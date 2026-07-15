"""
ExecutionReport - a plain-data summary of everything the pipeline
produced. No LLM, no judgment calls here or in the agent that builds
this - purely arithmetic over what's already in WorkflowState by the
time this runs.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class TestCaseReportEntry(BaseModel):
    """One line in the report's failed/blocked lists - deliberately lean,
    not the full TestCase object. A report is a summary; embedding the
    full playwright_script text (often 20+ lines) in every entry would
    turn a summary back into a dump."""

    title: str
    status: str
    duration_seconds: float | None = None
    reason: str | None = None


class ExecutionReport(BaseModel):
    requirement_title: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    scenario_count: int = 0
    test_case_count: int = 0

    approved_count: int = 0
    needs_review_count: int = 0
    rejected_count: int = 0

    executed_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    blocked_count: int = 0
    pass_rate: float = 0.0  # passed_count / executed_count, or 0.0 if nothing executed

    total_execution_seconds: float = 0.0

    failed_tests: list[TestCaseReportEntry] = Field(default_factory=list)
    blocked_tests: list[TestCaseReportEntry] = Field(default_factory=list)
    
    # Jira reporting statistics
    jira_stories_synced: list[str] = Field(default_factory=list)
    jira_bugs_raised: list[str] = Field(default_factory=list)
    jira_retests_required: int = 0