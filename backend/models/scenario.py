"""
Scenario model.

Unlike Requirement, a Scenario is mutable — specifically its `approved`
field, which flips from False to True (or gets rejected) during human
review. Everything else about it should be treated as generated-once,
but we don't freeze the whole model just for one field's sake.

It references its parent Requirement by id, not by embedding the object.
Scenario shouldn't need to know anything about Requirement's fields —
just which one it came from.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ScenarioPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Scenario(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    requirement_id: UUID
    scenario_name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    priority: ScenarioPriority = ScenarioPriority.MEDIUM
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    approved: bool = False
    generated_at: datetime = Field(default_factory=datetime.utcnow)