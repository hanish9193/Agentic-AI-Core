"""
The only module allowed to import litellm. Agents call LLMService, never
litellm directly - that's what keeps ScenarioAgent's code identical
whether it's talking to OpenAI, Ollama, or Groq.

structured_generate() forwards **kwargs straight to litellm.completion(),
which is deliberate: it means tests can pass mock_response=... through
the real public method and exercise this exact code path, with no
monkeypatching and no real API key. See test_scenario_agent.py.
"""

from typing import TypeVar

from litellm import completion
from pydantic import BaseModel

from backend.config.settings import LLMConfig, get_settings

T = TypeVar("T", bound=BaseModel)

# Providers whose litellm model string needs a prefix beyond the bare model
# name. OpenAI needs none ("gpt-4o-mini" as-is); others route through a
# provider/ prefix. Extend this as you actually add providers - don't
# pre-populate ones you're not using yet.
_PROVIDER_PREFIXES: dict[str, str] = {
    "openai": "",
    "ollama": "ollama/",
    "groq": "groq/",
}

DEFAULT_STRUCTURED_SYSTEM_PROMPT = (
    "You respond with a single valid JSON object and nothing else - "
    "no markdown fences, no commentary before or after it."
)


class LLMServiceError(Exception):
    """Raised when a completion call fails or returns something that
    doesn't validate against the expected schema. Agents catch this, not
    litellm's own exception types - callers shouldn't need to know which
    provider SDK is underneath."""


class LLMService:
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or get_settings().llm

    def _model_string(self) -> str:
        prefix = _PROVIDER_PREFIXES.get(self.config.provider, "")
        return f"{prefix}{self.config.model}"

    def generate(self, *, system: str, user: str, **kwargs) -> str:
        """Plain text completion. Returns the raw response content."""
        try:
            response = completion(
                model=self._model_string(),
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=self.config.temperature,
                api_key=self.config.api_key,
                **kwargs,
            )
        except Exception as exc:
            raise LLMServiceError(f"LLM call failed ({self.config.provider}/{self.config.model}): {exc}") from exc

        return response.choices[0].message.content

    def structured_generate(
        self,
        *,
        user: str,
        response_model: type[T],
        system: str = DEFAULT_STRUCTURED_SYSTEM_PROMPT,
        **kwargs,
    ) -> T:
        """Completion constrained to JSON, validated into response_model.

        response_model must describe a JSON *object* at the top level -
        OpenAI's json_object mode rejects a bare top-level array. Wrap
        list output in a small model with one field, e.g. {"items": [...]}.
        """
        try:
            response = completion(
                model=self._model_string(),
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=self.config.temperature,
                api_key=self.config.api_key,
                response_format={"type": "json_object"},
                **kwargs,
            )
        except Exception as exc:
            raise LLMServiceError(f"LLM call failed ({self.config.provider}/{self.config.model}): {exc}") from exc

        content = response.choices[0].message.content
        try:
            return response_model.model_validate_json(content)
        except Exception as exc:
            raise LLMServiceError(
                f"LLM response did not match {response_model.__name__}: {exc}\nRaw content: {content}"
            ) from exc