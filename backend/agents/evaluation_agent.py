"""
EvaluationAgent - the QA layer for the AI's own output. Before this agent,
ScenarioAgent and TestCaseAgent's output was trusted unconditionally. This
agent scores it, catches duplicates, and decides what proceeds
automatically versus what needs a human to look at it versus what gets
rejected outright.

Two kinds of logic here, deliberately not mixed:
- Duplicate detection and coverage checking are DETERMINISTIC - no LLM
  call, same input always gives the same output. These are comparisons,
  not judgment calls, so they don't need a model.
- Relevance and completeness scoring genuinely need judgment ("does this
  test case actually relate to the requirement" isn't answerable by
  string comparison) - that's the one LLM call this agent makes.

Duplicate detection compares title + expected_result together, not title
alone. Title-only word-overlap can't distinguish "verify login with
correct password" from "...incorrect password" (near-identical text,
opposite meaning, Jaccard ~0.67) - adding expected_result text separates
them cleanly (~0.90 for real duplicates vs ~0.16 for that negation case),
since the two outcomes described actually differ. Calibrated against
real examples, not guessed.

LLM correlation is by test_case_number (a 1-based index assigned just for
this prompt), not by echoing text back like TestCaseAgent's scenario_name
approach. Index-based is stricter here: we can validate we got back
exactly {1..N} with no gaps or duplicates, rather than fuzzy-matching text.

Three possible outcomes per test case, not two:
- REJECTED - a duplicate, or relevance below relevance_rejection_threshold
  (this isn't a borderline case, it's just wrong)
- APPROVED - confidence >= workflow.evaluation_threshold
- NEEDS_REVIEW - everything else (plausible but not confident enough)
"""

from pydantic import BaseModel, Field

from backend.agents.base import BaseAgent
from backend.config.settings import get_settings
from backend.models.state import WorkflowState
from backend.models.test_case import EvaluationStatus, TestCase
from backend.services.llm import LLMService
from backend.utils.prompts import load_prompt


class _TestCaseEvaluation(BaseModel):
    test_case_number: int = Field(ge=1)
    relevance: float = Field(ge=0.0, le=1.0)
    completeness: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1)


class _EvaluationBatch(BaseModel):
    evaluations: list[_TestCaseEvaluation] = Field(min_length=1)


def _jaccard_similarity(a: str, b: str) -> float:
    words_a, words_b = set(a.lower().split()), set(b.lower().split())
    if not words_a and not words_b:
        return 1.0
    return len(words_a & words_b) / len(words_a | words_b)


def _test_case_text(tc: TestCase) -> str:
    return f"{tc.title} {tc.expected_result}"


def _mark_duplicates(test_cases: list[TestCase], threshold: float) -> int:
    """Mutates evaluation_status/evaluation_reason in place for any test
    case that's a near-duplicate of an earlier one in the list. Keeps the
    first occurrence, rejects later ones. Returns how many were rejected."""
    rejected = 0
    for i in range(len(test_cases)):
        if test_cases[i].evaluation_status == EvaluationStatus.REJECTED:
            continue
        for j in range(i + 1, len(test_cases)):
            if test_cases[j].evaluation_status == EvaluationStatus.REJECTED:
                continue
            similarity = _jaccard_similarity(_test_case_text(test_cases[i]), _test_case_text(test_cases[j]))
            if similarity >= threshold:
                test_cases[j].evaluation_status = EvaluationStatus.REJECTED
                test_cases[j].evaluation_reason = f"Duplicate of '{test_cases[i].title}' (similarity {similarity:.2f})"
                rejected += 1
    return rejected


def _coverage_message(state: WorkflowState) -> str:
    covered_ids = {tc.scenario_id for tc in state.generated_test_cases}
    missing = [s for s in state.generated_scenarios if s.id not in covered_ids]
    if missing:
        names = ", ".join(s.scenario_name for s in missing)
        return f"coverage gap - no test case for: {names}"
    return f"coverage complete - all {len(state.generated_scenarios)} scenarios have at least one test case"


def _format_test_cases_block(test_cases: list[TestCase]) -> str:
    lines = []
    for i, tc in enumerate(test_cases, start=1):
        lines.append(
            f"{i}. Title: {tc.title}\n"
            f"   Preconditions: {tc.preconditions}\n"
            f"   Steps: {tc.steps}\n"
            f"   Expected result: {tc.expected_result}"
        )
    return "\n".join(lines)


class EvaluationAgent(BaseAgent):
    name = "Evaluation Agent"

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()
        settings = get_settings()
        self.confidence_threshold = settings.workflow.evaluation_threshold
        self.duplicate_threshold = settings.evaluation.duplicate_similarity_threshold
        self.relevance_rejection_threshold = settings.evaluation.relevance_rejection_threshold

    def run(self, state: WorkflowState) -> WorkflowState:
        if state.requirement is None:
            raise ValueError(f"{self.name} requires state.requirement to be set")
        if not state.generated_test_cases:
            raise ValueError(f"{self.name} requires at least one generated test case")

        state.add_log(f"{self.name} started")
        state.add_log(f"{self.name}: {_coverage_message(state)}")

        duplicate_count = _mark_duplicates(state.generated_test_cases, self.duplicate_threshold)
        if duplicate_count:
            state.add_log(f"{self.name}: rejected {duplicate_count} duplicate test case(s)")

        candidates = [tc for tc in state.generated_test_cases if tc.evaluation_status != EvaluationStatus.REJECTED]
        if not candidates:
            state.add_log(f"{self.name} finished: 0 approved, 0 need review, {duplicate_count} rejected as duplicates")
            return state

        prompt = load_prompt(
            "evaluation_prompt.txt",
            title=state.requirement.title,
            description=state.requirement.description,
            test_cases=_format_test_cases_block(candidates),
        )

        batch = self.llm_service.structured_generate(
            user=prompt,
            response_model=_EvaluationBatch,
        )

        expected_numbers = set(range(1, len(candidates) + 1))
        returned_numbers = {e.test_case_number for e in batch.evaluations}
        if returned_numbers != expected_numbers:
            raise ValueError(
                f"{self.name}: LLM returned evaluations for {sorted(returned_numbers)}, "
                f"expected exactly {sorted(expected_numbers)}"
            )

        approved_count = 0
        review_count = 0
        irrelevant_count = 0
        for evaluation in batch.evaluations:
            test_case = candidates[evaluation.test_case_number - 1]
            confidence = (evaluation.relevance + evaluation.completeness) / 2
            test_case.confidence = confidence
            test_case.evaluation_reason = evaluation.reason

            if evaluation.relevance < self.relevance_rejection_threshold:
                test_case.evaluation_status = EvaluationStatus.REJECTED
                irrelevant_count += 1
            elif confidence >= self.confidence_threshold:
                test_case.evaluation_status = EvaluationStatus.APPROVED
                approved_count += 1
            else:
                test_case.evaluation_status = EvaluationStatus.NEEDS_REVIEW
                review_count += 1

        state.add_log(
            f"{self.name} finished: {approved_count} approved, {review_count} need review, "
            f"{duplicate_count + irrelevant_count} rejected ({duplicate_count} duplicates, {irrelevant_count} irrelevant)"
        )
        return state