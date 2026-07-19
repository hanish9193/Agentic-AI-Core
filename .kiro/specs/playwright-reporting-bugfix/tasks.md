# Implementation Plan

## Overview

This implementation follows the three-layer architecture:
1. **PlaywrightRunner** - Emits raw execution events with actual results
2. **TimelineBuilder** - Merges test case steps + raw events + artifacts (zero text generation)
3. **Report Agent** - Pure renderer (zero inference)

The bug manifests when execution reports display generic step descriptions instead of meaningful test case steps. The fix establishes explicit timeline capture with semantic context preservation throughout the execution pipeline.

---

## Phase 1: Bug Condition Exploration (BEFORE Fix)

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Generic Step Descriptions in Reports
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate timeline events lack semantic context
  - **Scoped PBT Approach**: Execute a concrete test case with known steps ["Navigate to login page", "Enter username", "Enter password", "Click login"] and verify report contains generic descriptions like "Execute test step: 'fill'"
  - Test implementation:
    - Create test case with structured steps: `[{"action": "Navigate to login page", "expected": "Login page displayed"}, {"action": "Enter username", "expected": "Username field contains value"}, ...]`
    - Execute via PlaywrightRunner on UNFIXED code
    - Parse generated HTML report
    - Assert that report contains generic text like "Execute test step:" or "Visual State Capture"
    - Assert that `ExecutionResult.timeline` is empty or incomplete
    - Assert that step descriptions DO NOT match test case step definitions
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found:
    - Which step descriptions are generic?
    - Is timeline empty in ExecutionResult?
    - Are screenshot filenames appearing as failure messages?
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 1.1, 2.1, 2.2_

---

## Phase 2: Preservation Property Tests (BEFORE Fix)

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Execution Mechanics Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-reporting functionality:
    - Execute test scripts with various configurations (headless/headed, with/without storage state, different timeouts)
    - Observe that pass/fail status determination works
    - Observe that artifacts (screenshots, videos, traces) are generated in correct locations
    - Observe that process cleanup (kill process tree, close pipes) works
    - Observe that playwright.config.ts settings are respected
    - Observe that vault credentials are injected correctly
    - Observe that storage state files are created
  - Write property-based tests capturing observed behavior patterns:
    - For all test scripts, execution status (pass/fail/error) is determined correctly
    - For all test scripts, artifacts are generated in `backend/playwrightt/artifacts/{run_id}/`
    - For all test scripts that timeout or crash, process cleanup works
    - For all test scripts with storage state, authentication persists
    - For all test scripts with credentials, TARGET_USERNAME and TARGET_PASSWORD are injected
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

---

## Phase 3: Implementation

- [ ] 3. Implement three-layer architecture fix

  - [ ] 3.1 Update TestCase model to have structured steps
    - **File**: `backend/models/test_case.py`
    - **Change**: Modify `TestCase.steps` from `list[str]` to `list[TestCaseStep]`
    - **Details**:
      - Create `TestCaseStep` model with fields: `action: str`, `expected: str`
      - Update TestCase model: `steps: list[TestCaseStep]`
      - Add validation to ensure steps are structured before execution
      - Update all test case creation/loading code to use structured steps
    - **Validation**: Ensure existing test cases can be migrated/loaded with structured steps
    - _Bug_Condition: isBugCondition(execution_result) where execution_result.timeline lacks semantic context from test case steps_
    - _Expected_Behavior: TestCase.steps provides semantic context for timeline construction_
    - _Preservation: TestCase model structure compatible with existing test case repositories_
    - _Requirements: 2.1, 2.3_

  - [ ] 3.2 Update PlaywrightRunner to emit raw execution events
    - **File**: `backend/services/playwright_runner.py`
    - **Change**: Inject minimal event emitter that logs raw execution events with actual results to stdout
    - **Details**:
      - Create `_generate_minimal_wrapper()` method that injects TypeScript wrapper code
      - Wrapper wraps `page.goto()`, `page.click()`, `page.fill()`, `page.selectOption()`
      - Each wrapped method emits raw event via `console.log('RAW_EVENT:' + JSON.stringify(event))`
      - Raw event structure: `{"timestamp": "...", "event_type": "goto|click|fill|select", "target": "...", "success": true|false, "actual": "...", "error_message": null|"...", "details": {...}}`
      - Example goto event: `{"timestamp": "2026-07-16T10:23:45.123Z", "event_type": "goto", "target": "https://example.com/login", "success": true, "actual": "Navigated to https://example.com/login", "error_message": null, "details": {"page_title": "Login"}}`
      - Example click event: `{"timestamp": "2026-07-16T10:23:46.005Z", "event_type": "click", "target": "button[type='submit']", "success": true, "actual": "Clicked button[type='submit']", "error_message": null, "details": {}}`
      - Parse stdout lines for `RAW_EVENT:` prefix and extract JSON
      - Store parsed events in `raw_events` array
      - Return `raw_events` in `PlaywrightRunResult`
    - **Validation**: Execute test case and verify `PlaywrightRunResult.raw_events` contains structured events with actual results
    - _Bug_Condition: Timeline events lack actual execution results_
    - _Expected_Behavior: Raw events capture actual results for each browser action_
    - _Preservation: Subprocess execution mechanism unchanged, artifacts generation unchanged_
    - _Requirements: 2.1, 2.2, 3.1_

  - [ ] 3.3 Create TimelineBuilder service as pure merger
    - **File**: `backend/services/timeline_builder.py` (NEW FILE)
    - **Change**: Create `TimelineBuilder` class with `build()` method
    - **Details**:
      - Method signature: `build(raw_events: list[dict], test_case, run_id: str, artifacts_dir: Path) -> list[dict]`
      - Validate test case has structured steps with action and expected fields
      - Validate raw events count >= test case steps count (fail if incomplete execution)
      - Filter out screenshot events from raw_events (they're attachments, not execution steps)
      - For each test case step (1-indexed):
        - Get test case step: `test_case.steps[step_index - 1]`
        - Get corresponding raw event: `execution_events[step_index - 1]`
        - Calculate duration: `end_time - start_time`
        - Determine status: `"PASS" if raw_event["success"] else "ERROR"`
        - Find screenshot: `_find_screenshot_for_step(step_index, artifacts_dir)`
        - Build timeline event by MERGING (no text generation):
          - `"step": step_index`
          - `"title": f"Step {step_index}: {test_case_step.action}"` (template for title only)
          - `"action": test_case_step.action` (FROM TEST CASE)
          - `"expected": test_case_step.expected` (FROM TEST CASE)
          - `"actual": raw_event["actual"]` (FROM RAW EVENT)
          - `"status": "PASS"|"ERROR"` (FROM RAW EVENT)
          - `"start_time": start_time.isoformat()` (CALCULATED)
          - `"end_time": raw_event["timestamp"]` (FROM RAW EVENT)
          - `"duration_ms": duration_ms` (CALCULATED)
          - `"screenshot": screenshot_filename` (FROM ARTIFACTS)
          - `"video": video_path` (FROM ARTIFACTS)
          - `"trace": trace_path` (FROM ARTIFACTS)
          - `"page": raw_event.details.page_title` (FROM RAW EVENT)
          - `"error": raw_event.error_message` (FROM RAW EVENT)
          - `"details": {...}` (FROM RAW EVENT)
      - Attach video and trace paths to all events
      - Return structured timeline array
    - Helper methods:
      - `_find_screenshot_for_step(step_index, artifacts_dir)`: Find screenshot by chronological order
      - `_find_artifact(artifacts_dir, pattern)`: Find video/trace files
    - **Critical**: TimelineBuilder is a PURE MERGER. Zero text generation, zero inference, zero heuristics.
    - **Validation**: Unit test TimelineBuilder with mock raw events and test case, verify output has correct structure
    - _Bug_Condition: Timeline events lack semantic context from test case steps_
    - _Expected_Behavior: Structured timeline events with action from test case, actual from raw event, artifacts attached_
    - _Preservation: No changes to execution mechanics, only timeline construction_
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ] 3.4 Update Execution API to invoke PlaywrightRunner then TimelineBuilder
    - **File**: `backend/main.py`
    - **Change**: Modify `/api/v1/projects/{project_id}/testcases/{test_case_id}/execute` endpoint
    - **Details**:
      - Step 1: Execute test via PlaywrightRunner (get raw events)
        - `playwright_result = playwright_runner.run(...)`
      - Step 2: Build structured timeline from raw events
        - `timeline_builder = TimelineBuilder()`
        - `timeline = timeline_builder.build(playwright_result.raw_events, test_case, run_id, artifacts_dir)`
      - Step 3: Persist execution result with structured timeline
        - Create `ExecutionResult` with all fields including `timeline=timeline`
        - `repo.save_execution_result(result)`
      - Add error handling: if TimelineBuilder raises ValueError (incomplete execution), return 500 with error message
    - **Validation**: Execute test case via API, fetch ExecutionResult from DB, verify timeline is populated with structured events
    - _Bug_Condition: Timeline not persisted to ExecutionResult.timeline field_
    - _Expected_Behavior: ExecutionResult.timeline contains complete structured timeline from TimelineBuilder_
    - _Preservation: API contract unchanged, execution mechanics unchanged_
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 3.5 Update ExecutionResult.timeline field structure
    - **File**: `backend/models/execution_result.py`
    - **Change**: Ensure timeline field uses structured schema
    - **Details**:
      - Update field definition: `timeline: list[dict] = Field(default_factory=list)`
      - Add docstring: "Structured timeline events from TimelineBuilder. Each event contains: step, title, action, expected, actual, status, duration_ms, screenshot, video, trace, page, error, details."
      - Ensure database migration if needed (timeline field type change)
    - **Validation**: Create ExecutionResult with structured timeline, save to DB, load from DB, verify structure preserved
    - _Bug_Condition: Timeline field structure not enforced_
    - _Expected_Behavior: ExecutionResult.timeline stores structured timeline events_
    - _Preservation: ExecutionResult model compatible with existing execution results_
    - _Requirements: 2.1, 2.3_

  - [ ] 3.6 Refactor report_service.py to be pure timeline renderer
    - **File**: `backend/services/report_service.py`
    - **Change**: Remove all inference logic, make `compile_reports()` a pure renderer
    - **Details**:
      - Modify `compile_reports()`:
        - Validate timeline exists: `if not execution_result.timeline: raise ValueError("Execution timeline incomplete. Report generation aborted.")`
        - Validate timeline event structure: Check all required fields present (step, title, action, expected, actual, status, duration_ms)
        - Call `generate_html_report_from_timeline(timeline, execution_result, test_case, project_id)`
      - Create `generate_html_report_from_timeline()`:
        - Pure loop renderer: for each event in timeline, extract fields and render HTML
        - No mapping, no inference, no parsing
        - Status display: `{"PASS": "✅ Passed", "FAIL": "❌ Failed", "ERROR": "❌ Error", "SKIP": "⏭️ Skipped"}[status]`
        - Embed screenshots under steps: `<img src="/api/v1/projects/{project_id}/executions/{execution_result.id}/artifacts/{screenshot}" />`
        - Render step card with: step number, title, status, duration, action, expected, actual, error (if present), screenshot (if present)
      - Remove functions entirely:
        - `map_timeline_event_to_step()` - No longer needed
        - `extract_step_number_from_filename()` - No longer needed
        - `parse_screenshot_filename()` - No longer needed
        - `self_heal_timeline_from_localhost()` - No longer needed
        - `parse_html_report_for_timeline()` - No longer needed
        - `generate_generic_fallback_step()` - No longer needed
        - `enrich_steps_with_llm()` - No longer needed for correct steps (can keep as optional AI analysis consumer)
      - Optional: Keep `generate_ai_observations()` as separate consumer that reads from timeline (not required for correct steps)
    - **Critical**: Report Agent is PURE RENDERER. Zero inference, zero parsing, zero fallbacks. If timeline is incomplete, fail with clear error.
    - **Validation**: Execute test case, generate report, verify HTML contains step descriptions matching test case steps exactly
    - _Bug_Condition: Report service relies on inference and fallback text generation_
    - _Expected_Behavior: Report service is pure renderer, timeline is single source of truth_
    - _Preservation: HTML report styling unchanged, report structure unchanged_
    - _Requirements: 2.1, 2.2, 2.4_

  - [ ] 3.7 Update Next.js Workspace to delegate to FastAPI execution API
    - **File**: `backend/playwrightt/app/api/execute/route.ts`
    - **Change**: Modify POST handler to call FastAPI execution API
    - **Details**:
      - Extract test_case_id and project_id from request body
      - Call FastAPI: `fetch('http://localhost:8000/api/v1/projects/{project_id}/testcases/{test_case_id}/execute', {method: 'POST'})`
      - Parse response as ExecutionResult
      - Store in local execution queue for real-time monitoring: `executionQueue.set(executionResult.id, {status: executionResult.status, timeline: executionResult.timeline})`
      - Return ExecutionResult as JSON
    - **Validation**: Click "Run" in Next.js workspace, verify execution invokes FastAPI endpoint, verify timeline is populated
    - _Bug_Condition: Duplicate execution paths (FastAPI subprocess vs Next.js API)_
    - _Expected_Behavior: Single execution pipeline, Next.js workspace delegates to FastAPI_
    - _Preservation: Next.js workspace UI unchanged, execution trigger button works_
    - _Requirements: 2.1, 2.2_

  - [ ] 3.8 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Accurate Step Descriptions in Reports
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1:
      - Execute test case with structured steps
      - Parse generated HTML report
      - Assert that report contains accurate step descriptions matching test case steps
      - Assert that `ExecutionResult.timeline` is populated with structured events
      - Assert that step descriptions match test case step definitions
      - Assert no generic text like "Execute test step:" or "Visual State Capture"
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ] 3.9 Verify preservation tests still pass
    - **Property 2: Preservation** - Execution Mechanics Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2:
      - Execute test scripts with various configurations
      - Verify pass/fail status determination unchanged
      - Verify artifacts generated in same locations
      - Verify process cleanup works
      - Verify playwright.config.ts settings respected
      - Verify credentials injected correctly
      - Verify storage state persists
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

---

## Phase 4: Checkpoint

- [ ] 4. Checkpoint - Ensure all tests pass and validate architecture
  - Run all tests (exploration test from task 1, preservation tests from task 2)
  - Verify exploration test now passes (bug is fixed)
  - Verify preservation tests still pass (no regressions)
  - Validate three-layer architecture:
    - PlaywrightRunner emits raw events only (no semantic enrichment)
    - TimelineBuilder produces structured timeline (pure merger, zero text generation)
    - Report Agent renders timeline (pure renderer, zero inference)
  - Validate timeline is single source of truth:
    - All consumers read from `ExecutionResult.timeline`
    - No component parses screenshot filenames, console text, or HTML reports
    - Timeline populated ONLY by TimelineBuilder
  - Execute end-to-end integration test:
    - Create test case with structured steps
    - Execute via FastAPI endpoint
    - Retrieve ExecutionResult from database
    - Verify timeline populated with structured events
    - Generate HTML report
    - Verify report displays accurate step descriptions matching test case steps
    - Verify screenshots embedded under steps (not as separate entries)
  - Ask user if questions arise
  - _Requirements: All requirements (1.1, 2.1, 2.2, 2.3, 2.4, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7)_

---

## Requirements Traceability

- **1.1**: Bug Condition - Generic step descriptions in reports (validated by task 1, fixed by tasks 3.1-3.7, verified by task 3.8)
- **2.1**: Timeline Construction - Raw events from PlaywrightRunner (implemented in task 3.2)
- **2.2**: Timeline Enrichment - TimelineBuilder merges test case + raw events (implemented in task 3.3)
- **2.3**: Timeline Persistence - ExecutionResult.timeline populated (implemented in tasks 3.4, 3.5)
- **2.4**: Report Rendering - Pure timeline renderer (implemented in task 3.6)
- **3.1**: Preservation - Subprocess execution unchanged (validated by task 2, verified by task 3.9)
- **3.2**: Preservation - Artifact generation unchanged (validated by task 2, verified by task 3.9)
- **3.3**: Preservation - Process cleanup unchanged (validated by task 2, verified by task 3.9)
- **3.4**: Preservation - Configuration loading unchanged (validated by task 2, verified by task 3.9)
- **3.5**: Preservation - Credential injection unchanged (validated by task 2, verified by task 3.9)
- **3.6**: Preservation - Storage state unchanged (validated by task 2, verified by task 3.9)
- **3.7**: Preservation - Browser configuration unchanged (validated by task 2, verified by task 3.9)

---

## Notes

- **Three-Layer Architecture**: PlaywrightRunner (raw events) → TimelineBuilder (enrichment) → Report Agent (rendering)
- **Zero Inference Guarantee**: PlaywrightRunner captures facts, TimelineBuilder merges data, Report Agent renders. No guessing at any layer.
- **Timeline as Single Source of Truth**: All consumers read from `ExecutionResult.timeline`. No parsing of filenames, console output, or HTML reports.
- **Fail Fast**: If timeline is incomplete, report generation fails with clear error. No fallbacks, no self-healing.
- **Test Case is Source of Truth**: All semantic content (action, expected) comes from TestCase.steps. TimelineBuilder only merges, never generates text.
