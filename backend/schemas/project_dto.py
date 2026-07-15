from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str
    line_of_business: str = "general"
    framework: str = "playwright"
    jira_project_key: str | None = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: str
    line_of_business: str
    framework: str
    created_at: datetime
    requirements: list[UUID]
    jira_project_key: str | None = None

