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

from datetime import datetime, timezone
from uuid import UUID, uuid4
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from backend.models.common import Priority


class Scenario(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    requirement_id: UUID
    scenario_name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    priority: Priority = Priority.MEDIUM
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    approved: bool = False
    rejected: bool = False
    generated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
    )
    reviewer: str | None = None
    approved_at: datetime | None = None
    jira_issue_key: str | None = None
    jira_issue_url: str | None = None
    jira_sync_status: str | None = None
    jira_last_synced_at: datetime | None = None
    path_type: str = "happy_path"
    tags: list[str] = Field(default_factory=list)