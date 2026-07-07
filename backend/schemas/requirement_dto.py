from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field
from backend.models.requirement import RequirementSource


class RequirementCreate(BaseModel):
    title: str
    description: str
    priority: str = "medium"
    business_domain: str = "general"


class RequirementResponse(BaseModel):
    id: UUID
    title: str
    description: str
    source: RequirementSource
    uploaded_at: datetime
    priority: str
    business_domain: str
    attachments: list[str]
