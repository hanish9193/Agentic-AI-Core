from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from backend.models.common import Priority


class ScenarioUpdate(BaseModel):
    scenario_name: str | None = None
    description: str | None = None
    priority: Priority | None = None
    approved: bool | None = None


class ScenarioResponse(BaseModel):
    id: UUID
    requirement_id: UUID
    scenario_name: str
    description: str
    priority: Priority
    confidence: float
    approved: bool
    generated_at: datetime
