"""
TestCase model.

References its parent Scenario by id, same pattern as Scenario -> Requirement.
Mutable, because `status` moves from PENDING to PASSED/FAILED/BLOCKED once
an Execution Agent exists - not today, but the field earns its place now
so that agent doesn't need a schema change to write to it.
"""

from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from backend.models.common import Priority


class TestCaseStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TestCase(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    scenario_id: UUID
    title: str = Field(min_length=1, max_length=200)
    preconditions: list[str] = Field(default_factory=list)
    steps: list[str] = Field(min_length=1)
    expected_result: str = Field(min_length=1)
    priority: Priority = Priority.MEDIUM
    status: TestCaseStatus = TestCaseStatus.PENDING
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))