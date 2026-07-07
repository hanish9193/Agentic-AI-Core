from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str
    created_at: datetime
    requirements: list[UUID]
