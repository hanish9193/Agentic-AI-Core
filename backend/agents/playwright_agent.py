"""
PlaywrightAgent converts an approved test case's plain-language steps
into an executable Playwright script.

Reads state.approved_test_cases() only, never generated_test_cases
directly - a rejected or still-needs-review test case is invisible to
this agent by construction, not by a runtime check. That's the point the
original design made: this agent "doesn't even know" a rejected test
case existed.

Output is raw TypeScript, not JSON. Earlier agents used JSON output
because their content (names, scores, short text) is easy to escape
correctly inside a JSON string. Code isn't - quotes, backslashes,
template literals, and multi-line content inside a JSON-encoded string
are a well-known way for models to produce broken JSON. Asking for raw
text sidesteps that failure mode; the tradeoff is this agent does its
own light validation (strip stray code fences, sanity-check it looks
like a Playwright test) instead of getting Pydantic's schema validation
for free.

One call per test case, not one batched call for all of them. Batching
would need the model to produce several code blocks separated by some
delimiter - its own fragile parsing problem, and a mistake in one script
could bleed into another. One call per test case costs more time on a
slow local model, but each result is isolated and self-contained.
"""

from backend.agents.base import BaseAgent
from backend.models.state import WorkflowState
from backend.models.test_case import TestCase
from backend.config.settings import get_settings
from backend.services.llm import LLMService
from backend.utils.prompts import load_prompt

from uuid import UUID

_SYSTEM_PROMPT = (
    "You are a senior QA automation engineer who writes clean, idiomatic "
    "Playwright TypeScript tests. You output ONLY code - no explanation, "
    "no markdown code fences, nothing before or after it."
)


def _strip_code_fences(text: str) -> str:
    """Models routinely wrap code in ```typescript ... ``` even when told
    not to. Strip it if present; leave the text alone if it isn't."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    lines = lines[1:]  # drop the opening ``` or ```typescript line
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _looks_like_valid_code(code: str, framework: str) -> bool:
    code_lower = code.lower()
    if framework == "selenium":
        return "import" in code and ("webdriver" in code_lower or "pytest" in code_lower or "selenium" in code_lower)
    elif framework == "cucumber":
        return "feature:" in code_lower or "scenario:" in code_lower or "@given" in code_lower or "given(" in code_lower
    else:
        return "test(" in code and "import" in code


def _format_preconditions(preconditions: list[str]) -> str:
    if not preconditions:
        return "None specified"
    return "\n".join(f"- {p}" for p in preconditions)


def _format_steps(steps: list[str]) -> str:
    return "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))


class PlaywrightAgent(BaseAgent):
    name = "Playwright Agent"

    def __init__(self, llm_service: LLMService | None = None, repo = None):
        self.llm_service = llm_service or LLMService()
        self.repo = repo

    def run(self, state: WorkflowState) -> WorkflowState:
        if state.requirement is None:
            raise ValueError(f"{self.name} requires state.requirement to be set")

        approved = state.approved_test_cases()
        if not approved:
            state.add_log(f"{self.name}: no approved test cases to convert")
            return state

        state.add_log(f"{self.name} started")

        # Resolve project framework via repository
        framework = "playwright"
        target_url = None
        target_username = None
        target_password = None

        if self.repo and state.requirement:
            req_id = state.requirement.id
            projects = self.repo.list_projects()
            target_proj = None
            for proj in projects:
                if req_id in proj.requirements:
                    target_proj = proj
                    framework = proj.framework or "playwright"
                    break
            
            if target_proj:
                target_url = target_proj.target_url
                target_username = target_proj.target_username
                if target_proj.target_password_enc:
                    from backend.utils.crypto import decrypt_value
                    target_password = decrypt_value(target_proj.target_password_enc)

        for test_case in approved:
            test_case.playwright_script = self._generate_script(test_case, framework, target_url, target_username, target_password)

        state.add_log(f"{self.name} finished: generated {len(approved)} {framework.capitalize()} script(s)")
        return state

    def _generate_script(self, test_case: TestCase, framework: str = "playwright", target_url: str | None = None, target_username: str | None = None, target_password: str | None = None) -> str:
        import os
        import json
        settings = get_settings()
        base_url = target_url or settings.playwright.base_url

        # Override framework if configured at test case level
        if getattr(test_case, "automation_framework", None):
            framework = test_case.automation_framework.lower()

        framework_context_str = "None specified"
        if "imported" in framework or "existing" in framework:
            # Locate and load the imported POM classes index
            # Look up project directory path from test case scenario requirement
            project_id_str = None
            if self.repo:
                scenario = self.repo.get_scenario(test_case.scenario_id)
                if scenario:
                    req_id = scenario.requirement_id
                    projects = self.repo.list_projects()
                    for proj in projects:
                        if req_id in proj.requirements:
                            project_id_str = str(proj.id)
                            break
            if project_id_str:
                pom_path = os.path.join("data", "projects", project_id_str, "pom_index.json")
                if os.path.exists(pom_path):
                    try:
                        with open(pom_path, "r", encoding="utf-8") as f:
                            pom_data = json.load(f)
                            framework_context_str = json.dumps(pom_data, indent=2)
                    except Exception:
                        pass

        if framework == "selenium":
            system_prompt = (
                "You are a senior QA automation engineer who writes clean, idiomatic Selenium WebDriver tests in Python using pytest. "
                "You output ONLY code - no explanation, no markdown code fences, nothing before or after it."
            )
            prompt = load_prompt(
                "playwright_prompt.txt",
                title=test_case.title,
                preconditions=_format_preconditions(test_case.preconditions),
                steps=_format_steps(test_case.steps),
                expected_result=test_case.expected_result,
                base_url=base_url,
                framework_context=framework_context_str
            )
            if target_username and target_password:
                prompt += (
                    f"\n\nAt the start of the test, after navigating to the base URL, you MUST log in. "
                    f"Load the credentials securely from environment variables at the top of the test code block: "
                    f"import os\n"
                    f"BASE_URL = os.environ.get('TARGET_URL', '{base_url}')\n"
                    f"USERNAME = os.environ.get('TARGET_USERNAME', 'default_username')\n"
                    f"PASSWORD = os.environ.get('TARGET_PASSWORD', 'default_password')\n"
                    f"Navigate to BASE_URL. Type USERNAME into the username field, PASSWORD into the password field, and click login before proceeding with rest of steps."
                )
            prompt += "\n\nWrite this test case using Selenium Python with pytest instead of Playwright."
        elif framework == "cucumber":
            system_prompt = (
                "You are a senior QA automation engineer who writes Cucumber BDD test specifications. "
                "You output a single Gherkin .feature specification followed by Python Behave/step definitions. "
                "You output ONLY the feature and step code - no explanation, no markdown code fences, nothing before or after it."
            )
            prompt = load_prompt(
                "playwright_prompt.txt",
                title=test_case.title,
                preconditions=_format_preconditions(test_case.preconditions),
                steps=_format_steps(test_case.steps),
                expected_result=test_case.expected_result,
                base_url=base_url,
                framework_context=framework_context_str
            )
            if target_username and target_password:
                prompt += (
                    f"\n\nAt the start of the test, after navigating to the base URL, you MUST log in. "
                    f"Retrieve the username and password from environment variables `TARGET_USERNAME` and `TARGET_PASSWORD` in your behave steps."
                )
            prompt += "\n\nWrite this test case using Gherkin feature syntax and Python step definitions instead of Playwright."
        else:
            system_prompt = _SYSTEM_PROMPT
            prompt = load_prompt(
                "playwright_prompt.txt",
                title=test_case.title,
                preconditions=_format_preconditions(test_case.preconditions),
                steps=_format_steps(test_case.steps),
                expected_result=test_case.expected_result,
                base_url=base_url,
                framework_context=framework_context_str
            )
            if target_username and target_password:
                prompt += (
                    f"\n\nAt the start of the test, after navigating to the base URL, you MUST log in. "
                    f"Load the credentials securely from environment variables at the top of the test code block: "
                    f"const BASE_URL = process.env.TARGET_URL || '{base_url}';\n"
                    f"const USERNAME = process.env.TARGET_USERNAME || 'default_username';\n"
                    f"const PASSWORD = process.env.TARGET_PASSWORD || 'default_password';\n"
                    f"Navigate to BASE_URL. Type USERNAME into the username field, PASSWORD into the password field, and click login before proceeding with rest of steps."
                )

        raw_output = self.llm_service.generate(system=system_prompt, user=prompt)
        code = _strip_code_fences(raw_output)

        if not _looks_like_valid_code(code, framework):
            if framework == "playwright":
                raise ValueError(
                    f"{self.name}: output for '{test_case.title}' doesn't look like a "
                    f"Playwright test (missing 'test(' or 'import') - got: {code[:200]!r}"
                )
            else:
                raise ValueError(
                    f"{self.name}: output for '{test_case.title}' doesn't look like a valid "
                    f"{framework.capitalize()} script - got: {code[:200]!r}"
                )

        return code