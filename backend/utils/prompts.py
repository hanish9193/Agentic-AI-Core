"""
Loads a prompt template from backend/prompts/ and substitutes variables.

Uses string.Template ($var), not str.format(). Prompt files routinely need
to show a literal JSON example to the model - with .format() every { and }
in that example would need doubling ({{ }}), which makes the prompt file
painful to hand-edit. $var has no such conflict with JSON syntax.
"""

from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(filename: str, **variables: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    return Template(path.read_text()).substitute(**variables)