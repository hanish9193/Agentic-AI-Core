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

# How each provider is told "respond with JSON". These are NOT
# interchangeable: OpenAI (and OpenAI-compatible providers like Groq) use
# response_format={"type": "json_object"}; Ollama's own JSON mode is a
# different parameter (format="json") per litellm's Ollama docs. Passing
# the wrong one for a provider doesn't error - it just gets ignored, and
# you silently lose JSON enforcement while still passing tests that don't
# actually hit that provider. Add a case here before using a new provider,
# don't assume the OpenAI-style kwarg works everywhere.
_JSON_MODE_KWARGS: dict[str, dict] = {
    "ollama": {"format": "json"},
}
_DEFAULT_JSON_MODE_KWARGS = {"response_format": {"type": "json_object"}}

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

    def _json_mode_kwargs(self) -> dict:
        return _JSON_MODE_KWARGS.get(self.config.provider, _DEFAULT_JSON_MODE_KWARGS)
    
    def _completion_kwargs(self) -> dict:
        kwargs = {
            "model": self._model_string(),
            "temperature": self.config.temperature,
        }

        if self.config.api_base:
            kwargs["api_base"] = self.config.api_base

        if self.config.api_key:
            kwargs["api_key"] = self.config.api_key

        return kwargs

    def generate(self, *, system: str, user: str, **kwargs) -> str:
        """Plain text completion. Returns the raw response content."""
        try:
            response = completion(
                model=self._model_string(),
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
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
                **self._json_mode_kwargs(),
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