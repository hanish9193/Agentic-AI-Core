"""
Configuration loader.

Precedence: .env overrides default_config.yaml.
YAML holds the *shape* of config (agents enabled, workflow mode, thresholds).
.env holds secrets and anything that changes per machine/environment.

Usage:
    from backend.config.settings import get_settings
    settings = get_settings()
    settings.llm.model
    settings.agents.scenario
"""

from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path(__file__).parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "default_config.yaml"

load_dotenv()


class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    api_key: str | None = None
    api_base: str | None = None  # required for ollama (e.g. http://localhost:11434); leave unset for cloud providers


class WorkflowConfig(BaseModel):
    mode: str = "sequential"
    human_review_enabled: bool = True
    evaluation_threshold: float = 0.75


class AgentsConfig(BaseModel):
    requirement: bool = True
    scenario: bool = True
    testcase: bool = True
    evaluation: bool = True
    human_approval: bool = True
    playwright: bool = False
    execution: bool = False
    report: bool = False


class BrowserConfig(BaseModel):
    type: str = "chromium"
    headless: bool = True


class RAGConfig(BaseModel):
    enabled: bool = False
    vector_db_provider: str = "chroma"
    vector_db_path: str = "./data/vector_store"


class GenerationConfig(BaseModel):
    scenario_count: int = 3


class EvaluationConfig(BaseModel):
    # Word-overlap (Jaccard) on title+expected_result combined, not title
    # alone - title-only similarity can't distinguish "correct password"
    # from "incorrect password" (near-identical text, opposite meaning).
    # Calibrated against real examples, not guessed - see evaluation_agent.py.
    duplicate_similarity_threshold: float = 0.75
    # Below this relevance score, a test case is rejected outright rather
    # than sent for human review - e.g. a "Forgot Password" test case
    # generated for a "Profile Picture Upload" requirement isn't a
    # borderline call, it's just wrong.
    relevance_rejection_threshold: float = 0.3


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"

    llm: LLMConfig = LLMConfig()
    workflow: WorkflowConfig = WorkflowConfig()
    agents: AgentsConfig = AgentsConfig()
    browser: BrowserConfig = BrowserConfig()
    rag: RAGConfig = RAGConfig()
    generation: GenerationConfig = GenerationConfig()
    evaluation: EvaluationConfig = EvaluationConfig()

    @classmethod
    def from_yaml(cls, path: Path = DEFAULT_CONFIG_PATH) -> "Settings":
        raw = yaml.safe_load(path.read_text()) if path.exists() else {}

        # Merge local overrides from override.yaml if exists
        override_path = CONFIG_DIR / "override.yaml"
        if override_path.exists():
            try:
                overrides = yaml.safe_load(override_path.read_text())
                if isinstance(overrides, dict):
                    for key, val in overrides.items():
                        if isinstance(val, dict) and key in raw and isinstance(raw[key], dict):
                            raw[key].update(val)
                        else:
                            raw[key] = val
            except Exception:
                pass

        # .env values win if set; LLM_API_KEY has no YAML equivalent on purpose.
        raw.setdefault("llm", {})["api_key"] = _env("LLM_API_KEY")
        raw.setdefault("llm", {})["api_base"] = _env("LLM_API_BASE")
        _override(raw, "llm", "provider", "LLM_PROVIDER")
        _override(raw, "llm", "model", "LLM_MODEL")
        _override(raw, "workflow", "evaluation_threshold", "EVALUATION_THRESHOLD", cast=float)
        _override(raw, "workflow", "human_review_enabled", "HUMAN_REVIEW_ENABLED", cast=_bool)

        return cls(**raw)



def _env(key: str) -> str | None:
    import os
    return os.getenv(key)


def _override(raw: dict, section: str, field: str, env_key: str, cast=str) -> None:
    value = _env(env_key)
    if value is not None:
        raw.setdefault(section, {})[field] = cast(value)


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache
def get_settings() -> Settings:
    return Settings.from_yaml()