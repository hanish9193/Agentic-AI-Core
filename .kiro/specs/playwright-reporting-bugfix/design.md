# Playwright Reporting Bugfix Design

## Architecture Principles

### Principle 1: Single Execution Pipeline

**Critical Rule**: There is exactly one execution pipeline in the entire platform. All execution flows through:

```
Dashboard / Next.js Workspace
         ↓
   Execution API
         ↓
  PlaywrightRunner (Python)
         ↓
Chromium + Playwright
         ↓
   Raw Execution Events
         ↓
   TimelineBuilder
         ↓
 Structured Timeline
         ↓
   ExecutionResult
         ↓
  Report / AI / Jira Agents
```

**Responsibilities**:
- **Dashboard**: UI for projects, requirements, scenarios, test cases, reports
- **Next.js Workspace**: UI + Monaco editor + browser viewer + execution trigger button
- **Execution API** (`backend/main.py`): Orchestration, authentication, parameter validation
- **PlaywrightRunner** (`backend/services/playwright_runner.py`): Browser launch, script execution, raw event capture
- **TimelineBuilder** (`backend/services/timeline_builder.py`): Raw events → Structured timeline transformation
- **Report Agent** (`backend/services/report_service.py`): Structured timeline → HTML/PDF rendering

**Key Point**: Both Dashboard and Next.js Workspace call the same PlaywrightRunner. This keeps all execution logic in Python, preventing business logic split between Python and TypeScript.

### Principle 2: Three-Layer Separation

**Critical Rule**: Execution, Timeline Construction, and Report Rendering are three independent layers:

```
Layer 1: Execution (PlaywrightRunner)
  - Launches browser
  - Executes Playwright script
  - Emits raw events: {"event": "goto", "timestamp": "...", "details": {...}}
  - Returns raw events array

Layer 2: Timeline Construction (TimelineBuilder)
  - Receives raw events + test case context
  - Attaches semantic step information
  - Attaches screenshots, videos, traces
  - Calculates durations and statuses
  - Produces complete TimelineEvent objects: {"step": 4, "title": "...", "action": "...", "expected": "...", "actual": "...", "status": "PASS", ...}

Layer 3: Report Rendering (Report Agent)
  - Receives structured timeline
  - Validates completeness
  - Renders HTML/PDF
  - Zero inference, zero parsing
```

**Key Point**: Playwright scripts focus **only** on browser automation. They emit minimal raw events. The TimelineBuilder enriches these events with all semantic context.

### Principle 3: Timeline as Single Source of Truth

**Critical Rule**: The structured timeline is the single source of truth for execution reconstruction.

**All consumers read from `ExecutionResult.timeline`**:
- Observer (real-time execution monitoring)
- Report Agent (HTML/PDF generation)
- AI Analysis (test quality assessment)
- Jira Agent (defect creation)

**Nobody parses**:
- Screenshot filenames
- Console text
- HTML reports
- Terminal output
- Log files

**Timeline is populated ONLY by TimelineBuilder**. No other component may write to `ExecutionResult.timeline`.

## Overview

This design addresses critical issues in the Playwright execution pipeline and reporting system where execution reports display generic placeholder text ("Execute test step", "Visual State Capture") instead of meaningful automation steps, screenshot filenames appear as failure messages, and the execution flow has incorrect artifact handling.

The bug manifests in the disconnect between test case step definitions and the timeline events captured during execution. The current architecture relies on implicit timeline inference from screenshot filenames and console logs, leading to generic step descriptions when this inference fails. The fix establishes an explicit timeline capture mechanism that preserves semantic context from test case steps throughout the execution pipeline.

**Fix Strategy**: Consolidate execution through the Next.js Playwright Workspace, inject test case step context into the execution engine, capture structured timeline events with semantic descriptions, persist timeline data to ExecutionResult, and enhance report mapping to accurately display step-by-step execution flow with correct screenshot attachments.

## Glossary

- **Bug_Condition (C)**: The condition where execution reports contain generic step descriptions or incorrect screenshot mappings - occurs when timeline events lack semantic context from original test case steps
- **Property (P)**: The desired behavior where reports display accurate step descriptions matching test case definitions with screenshots correctly attached to action steps
- **Preservation**: Existing execution mechanics, artifact generation, and non-reporting functionality that must remain unchanged
- **Raw Execution Event**: Minimal event emitted by Playwright wrapper containing: timestamp, event type (goto/click/fill), selector/URL, success/failure indicator, actual result. Does NOT contain semantic step information from test case.
- **Structured Timeline Event**: Complete event produced by TimelineBuilder by merging test case step (action, expected) with raw event (status, actual, timestamp) and artifacts (screenshots, video, trace)
- **ExecutionResult**: Database model in `backend/models/execution_result.py` containing execution metadata with complete structured timeline array
- **PlaywrightRunner**: Low-level Python execution service at `backend/services/playwright_runner.py` responsible for browser launch, script execution, artifact collection, and raw event capture
- **TimelineBuilder**: Merger service at `backend/services/timeline_builder.py` that combines test case steps + raw execution events + artifacts into structured timeline. **Does NOT generate or invent any text.**
- **Test Case Step**: Complete step definition in TestCase model containing: action (string), expected (string). This is the **single source of truth** for all semantic content.
- **Execution API**: FastAPI orchestration layer that validates requests, invokes PlaywrightRunner, calls TimelineBuilder, persists results, and triggers downstream consumers
- **Report Agent**: Pure timeline renderer at `backend/services/report_service.py` that transforms structured timeline into HTML/PDF reports with zero inference
- **Timeline Consumer**: Any component that reads structured timeline events (Report Agent, AI Analysis, Jira Agent, Observer). **Consumers never modify timeline.**

## Bug Details

### Bug Condition

The bug manifests when execution reports are generated from Playwright test runs. The `compile_reports()` function in `report_service.py` produces HTML reports with generic or incorrect step descriptions because timeline events lack semantic context from the original test case steps.

**Formal Specification:**
```
FUNCTION isBugCondition(execution_result)
  INPUT: execution_result of type ExecutionResult
  OUTPUT: boolean
  
  // Extract timeline events
  raw_timeline := execution_result.timeline OR execution_result._raw_payload["timeline"] OR []
  
  // Get test case for comparison
  test_case := get_test_case(execution_result.test_case_id)
  
  // Map timeline to report steps
  mapped_steps := []
  FOR EACH event IN raw_timeline DO
    step := map_timeline_event_to_step(event, test_case)
    mapped_steps.append(step)
  END FOR
  
  // Bug condition: generic descriptions or incorrect mappings
  RETURN (
    // Condition 1: Generic action text
    EXISTS step IN mapped_steps WHERE 
      step.action MATCHES "Execute test step: '\w+'" OR
      step.action = "Capture screenshot to record browser visual state."
    
    OR
    
    // Condition 2: Screenshot filename appearing as step title
    EXISTS step IN mapped_steps WHERE
      step.step_name MATCHES ".*\.png$" AND
      step.status = "❌ Failed"
    
    OR
    
    // Condition 3: Timeline is empty or incomplete
    length(raw_timeline) = 0 OR
    length(raw_timeline) < length(test_case.steps)
    
    OR
    
    // Condition 4: Step descriptions don't match test case steps
    EXISTS i IN [0..min(length(mapped_steps), length(test_case.steps))] WHERE
      NOT contains(mapped_steps[i].action, test_case.steps[i])
  )
END FUNCTION
```

### Examples

**Example 1: Generic Step Description**
- **Test Case Step**: "Enter username 'testuser' into the login form"
- **Timeline Event**: `{"event": "fill", "type": "info", "time": 1.2, "details": ""}`
- **Mapped Report Step**: `{"action": "Execute test step: 'fill'.", "expected": "Verify behavior of 'fill'.", "actual": "Action executed without exceptions."}`
- **Bug**: Generic description instead of meaningful "Enter username 'testuser' into the login form"

**Example 2: Screenshot Filename as Failure Message**
- **Timeline Event**: `{"event": "screenshot", "type": "error", "time": 3.5, "details": "error-state.png"}`
- **Mapped Report Step**: `{"step_name": "Visual State Capture", "status": "❌ Failed", "expected": "Visual state captured in file 'error-state.png'."}`
- **Bug**: Screenshot event incorrectly classified as a failed step

**Example 3: Empty Timeline**
- **Test Case Steps**: ["Navigate to login page", "Enter credentials", "Click login button"]
- **Timeline Events**: `[]` (empty)
- **Mapped Report Steps**: No steps displayed in report
- **Bug**: Complete absence of execution detail in report

**Example 4: Mismatched Step Descriptions**
- **Test Case Step 1**: "Navigate to booking page"
- **Timeline Event**: `{"event": "step-01-goto.png", "type": "info"}`
- **Regex Match**: Extracts step number 1
- **Mapped Report Step**: `{"step_name": "Step 1: Navigate to booking page", "action": "Execute step 1: Navigate to booking page"}`
- **Bug**: This works correctly ONLY if screenshot filename follows exact format AND test case is available

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Playwright CLI subprocess execution mechanism must remain unchanged
- Artifact generation (screenshots, videos, traces) must continue to work exactly as before
- Screenshot-on-failure capturing must continue to function
- report.json parsing and status extraction must remain unchanged
- HTML report styling and structure must remain unchanged
- JUnit XML report generation must continue to work
- Execution timeout handling and process cleanup must remain unchanged
- Storage state persistence for authentication must continue to work
- Vault credential injection must continue to function
- Browser headless/headed configuration must remain unchanged

**Scope:**
All inputs that do NOT involve report step description generation should be completely unaffected by this fix. This includes:
- Playwright test execution mechanics
- Browser automation and interaction
- Artifact file generation and storage
- Process lifecycle management
- Configuration loading and validation
- Error handling and timeout logic

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

**Primary Issue - Dual Execution Paths Without Shared Timeline**:

The platform has TWO independent Playwright execution mechanisms that don't share timeline data:

1. **Path A (Dashboard → FastAPI → playwright_runner.py subprocess)**:
   - Dashboard calls `/api/v1/projects/{project_id}/testcases/{test_case_id}/execute`
   - `playwright_runner.py` launches `subprocess.Popen(['npx', 'playwright', 'test'])`
   - Executes in isolation, generates artifacts, returns basic status
   - **NO timeline capture** because subprocess stdout is not parsed for structured events
   - Screenshot filenames are the ONLY semantic link back to test steps

2. **Path B (Next.js Workspace → execution-engine.ts → Playwright API)**:
   - Next.js workspace calls internal `/api/execute`
   - `execution-engine.ts` uses Playwright Node.js API directly
   - Wraps methods, captures timeline events, stores in execution queue
   - **HAS timeline capture** but stores in-memory, not persisted to ExecutionResult.timeline
   - Timeline events sent via webhook but not saved to database

**The Fix**: Consolidate to a single execution service (PlaywrightRunner in Python) that both Dashboard and Next.js Workspace invoke, with structured timeline capture built-in.

**Secondary Issue - Timeline Not Structured**:

Current timeline events lack semantic structure:
```python
# Current (insufficient)
{"event": "goto", "type": "info", "time": 0.5, "details": ""}
```

This forces `report_service.py` to infer meaning from screenshot filenames, which fails when:
- Filenames don't follow expected pattern
- Test case context is not available
- Screenshot wrapper doesn't log timeline events

**The Fix**: Emit structured timeline events with complete semantic context:
```json
{
  "step": 1,
  "action": "Navigate to login page",
  "status": "PASS",
  "start_time": "2026-07-16T10:23:45.123Z",
  "end_time": "2026-07-16T10:23:45.965Z",
  "duration_ms": 842,
  "screenshot": "step-01.png",
  "page": "Login",
  "error": null
}
```

**Tertiary Issue - Report Service Relies on Inference**:

The `map_timeline_event_to_step()` function attempts to:
- Extract step numbers from screenshot filenames using regex
- Match filenames to test case steps
- Generate generic fallback text when matching fails
- Parse HTML reports from disk as self-healing

**The Fix**: Report service becomes a pure transformer: Timeline → HTML. No inference, no fallbacks, no LLM enrichment required for correct step descriptions.

## Correctness Properties

Property 1: Bug Condition - Accurate Step Descriptions

_For any_ execution result where a test case with defined steps is executed, the generated report SHALL display step descriptions that accurately reflect the test case step definitions, with each report step's action field containing the semantic description from the corresponding test case step, and screenshots correctly attached to their associated action steps rather than appearing as separate "Visual State Capture" entries.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

Property 2: Preservation - Execution Mechanics Unchanged

_For any_ test script execution that does NOT involve report generation (i.e., all Playwright automation, artifact generation, and process management), the fixed code SHALL produce exactly the same behavior as the original code, preserving all existing execution mechanics including subprocess invocation, browser automation, screenshot capture, video recording, trace generation, timeout handling, credential injection, and storage state persistence.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

## Fix Implementation Summary

### Critical Architectural Changes

**1. Three-Layer Separation**
```
Layer 1: PlaywrightRunner
  - Emits raw events: {"timestamp": "...", "event_type": "goto", "target": "...", "success": true}
  
Layer 2: TimelineBuilder
  - Receives: raw events + test case context
  - Produces: structured timeline with semantic enrichment
  
Layer 3: Report Agent
  - Receives: structured timeline
  - Produces: HTML/PDF with zero inference
```

**2. Timeline Construction Flow**
```python
# Old (inference-based, timeline built in Playwright script)
playwright_result = playwright_runner.run(script)  # ❌ Script emits complete timeline
execution_result.timeline = playwright_result.timeline

# New (clean separation, timeline built by dedicated builder)
playwright_result = playwright_runner.run(script)  # ✅ Script emits raw events only
timeline = timeline_builder.build(playwright_result.raw_events, test_case)  # ✅ Builder enriches
execution_result.timeline = timeline
```

**3. Fail Fast on Incomplete Data**
```python
# TimelineBuilder validation
if len(raw_events) < len(test_case.steps):
    raise ValueError("Execution incomplete. Some test case steps did not execute.")

# Report Agent validation
if not execution_result.timeline:
    raise ValueError("Execution timeline incomplete. Report generation aborted.")
```

**4. Zero Inference Guarantee**
- **PlaywrightRunner**: Only captures raw browser automation facts
- **TimelineBuilder**: Only enriches with test case context (no guessing)
- **Report Agent**: Only renders (no inference, no parsing, no fallbacks)

### Execution Flow

```
Test Case
    ↓
PlaywrightRunner (emits raw events)
    ↓
Raw Events: [{"timestamp": "...", "event_type": "goto", ...}, ...]
    ↓
TimelineBuilder (enriches with test case context)
    ↓
Structured Timeline: [{"step": 1, "title": "...", "action": "...", ...}, ...]
    ↓
ExecutionResult.timeline (single source of truth)
    ↓
┌─────────────────────────┐
│ Report Agent (renderer) │ → HTML/PDF
│ Observer (real-time)    │ → WebSocket
│ AI Agent (analysis)     │ → Insights
│ Jira Agent (defects)    │ → Issues
└─────────────────────────┘
```

### Validation Criteria

Implementation is correct when:
1. ✅ Playwright scripts contain ZERO timeline construction logic (only browser automation)
2. ✅ PlaywrightRunner returns raw events array (no semantic enrichment)
3. ✅ TimelineBuilder produces complete structured timeline from raw events + test case
4. ✅ Generated HTML report contains zero generic text
5. ✅ Every report step matches a timeline event exactly (title, action, expected, actual)
6. ✅ Screenshots appear embedded under execution steps, not as separate entries
7. ✅ Report generation fails with clear error if timeline is missing or incomplete
8. ✅ `report_service.py` contains zero regex parsing, filename extraction, or inference logic

## Fix Implementation

### Architectural Change: TimelineBuilder as Enrichment Layer

**Principle**: Separate execution (PlaywrightRunner), timeline construction (TimelineBuilder), and rendering (Report Agent) into three independent layers.

### Test Case Step Schema (Source of Truth)

**Critical Rule**: Test Case is the **single source of truth** for all semantic content.

Every test case must contain structured steps with action and expected result:

```python
class TestCaseStep(BaseModel):
    action: str  # What action to perform (e.g., "Navigate to Login Page")
    expected: str  # What should happen (e.g., "Login page is displayed")

class TestCase(BaseModel):
    id: UUID
    name: str
    steps: list[TestCaseStep]  # Structured steps, not plain strings
    playwright_script: str
    # ... other fields ...
```

**Example Test Case**:
```json
{
  "id": "...",
  "name": "User Login Test",
  "steps": [
    {
      "action": "Navigate to Login Page",
      "expected": "Login page is displayed"
    },
    {
      "action": "Enter username 'testuser'",
      "expected": "Username field contains 'testuser'"
    },
    {
      "action": "Enter password",
      "expected": "Password field is masked"
    },
    {
      "action": "Click Login Button",
      "expected": "User is authenticated and redirected to dashboard"
    }
  ],
  "playwright_script": "..."
}
```

**Key Point**: ALL semantic content (action descriptions, expected results) comes from test case, NOT generated by TimelineBuilder.

### Raw Execution Event Schema (PlaywrightRunner Output)

**Critical Rule**: Playwright scripts emit **minimal** raw events with actual results only.

```python
class RawExecutionEvent(BaseModel):
    timestamp: str  # ISO 8601 timestamp
    event_type: Literal["goto", "click", "fill", "select", "screenshot", "error"]
    target: str  # URL for goto, selector for click/fill/select, filename for screenshot
    success: bool  # True if action succeeded
    actual: str  # What actually happened (e.g., "Navigated to https://example.com/login", "Clicked button[type='submit']")
    error_message: str | None  # Error details if success=False
    details: dict | None  # Additional context (page title, value filled, etc.)
```

**Example - Raw goto event**:
```json
{
  "timestamp": "2026-07-16T10:23:45.123Z",
  "event_type": "goto",
  "target": "https://example.com/login",
  "success": true,
  "actual": "Navigated to https://example.com/login",
  "error_message": null,
  "details": {"page_title": "Login - My Application"}
}
```

**Example - Raw click event**:
```json
{
  "timestamp": "2026-07-16T10:23:46.005Z",
  "event_type": "click",
  "target": "button[type='submit']",
  "success": true,
  "actual": "Clicked button[type='submit']",
  "error_message": null,
  "details": {}
}
```

**Key Point**: Raw events contain actual execution results but NO semantic descriptions from test case (no "Navigate to Login Page", no "Login page is displayed").

### Structured Timeline Event Schema (TimelineBuilder Output)

**Critical Rule**: TimelineBuilder **merges** test case step + raw event + artifacts. **Zero text generation.**

```python
class TimelineEvent(BaseModel):
    step: int  # 1-based step index
    title: str  # "Step {step}: {test_case.steps[step-1].action}"
    action: str  # FROM TEST CASE: test_case.steps[step-1].action
    expected: str  # FROM TEST CASE: test_case.steps[step-1].expected
    actual: str  # FROM RAW EVENT: raw_event.actual
    status: Literal["PASS", "FAIL", "SKIP", "ERROR"]  # FROM RAW EVENT: derived from raw_event.success
    start_time: str  # FROM RAW EVENT: previous event timestamp
    end_time: str  # FROM RAW EVENT: raw_event.timestamp
    duration_ms: int  # CALCULATED: end_time - start_time
    screenshot: str | None  # FROM ARTIFACTS: matched by step index
    video: str | None  # FROM ARTIFACTS: video file for execution
    trace: str | None  # FROM ARTIFACTS: trace file for execution
    page: str | None  # FROM RAW EVENT: raw_event.details.page_title
    dataset_row: int | None  # FROM TEST CASE: if data-driven
    error: str | None  # FROM RAW EVENT: raw_event.error_message
    details: dict | None  # FROM RAW EVENT: raw_event.details
```

**Example - Structured timeline event** (test case step 1 + raw goto event + artifacts):
```json
{
  "step": 1,
  "title": "Step 1: Navigate to Login Page",
  "action": "Navigate to Login Page",
  "expected": "Login page is displayed",
  "actual": "Navigated to https://example.com/login",
  "status": "PASS",
  "start_time": "2026-07-16T10:23:45.000Z",
  "end_time": "2026-07-16T10:23:45.965Z",
  "duration_ms": 965,
  "screenshot": "step-01.png",
  "video": "execution-video.webm",
  "trace": "execution-trace.zip",
  "page": "Login - My Application",
  "dataset_row": null,
  "error": null,
  "details": {
    "url": "https://example.com/login",
    "page_title": "Login - My Application"
  }
}
```

**TimelineBuilder Merge Algorithm**:
```python
# NO text generation - pure merging
timeline_event = {
    "step": step_index,
    "title": f"Step {step_index}: {test_case.steps[step_index - 1].action}",
    "action": test_case.steps[step_index - 1].action,  # FROM TEST CASE
    "expected": test_case.steps[step_index - 1].expected,  # FROM TEST CASE
    "actual": raw_event.actual,  # FROM RAW EVENT
    "status": "PASS" if raw_event.success else "ERROR",  # FROM RAW EVENT
    "duration_ms": calculate_duration(prev_timestamp, raw_event.timestamp),
    "screenshot": find_screenshot(step_index, artifacts_dir),  # FROM ARTIFACTS
    "video": find_video(artifacts_dir),  # FROM ARTIFACTS
    "trace": find_trace(artifacts_dir),  # FROM ARTIFACTS
    # ... other fields merged from raw event ...
}
```

**Key Point**: TimelineBuilder is a **pure merger**. Zero templates, zero heuristics, zero text generation.

### Report Agent Responsibility

The Report Agent is a **pure renderer**:

```python
# Report Agent - Pure Timeline Renderer
for event in execution_result.timeline:
    render_step(event)  # No mapping, no parsing, no inference
```

The Report Agent must:
- ✅ Validate timeline completeness
- ✅ Attach screenshots under correct steps
- ✅ Generate HTML from structured events
- ✅ Generate PDF from structured events

The Report Agent must **NEVER**:
- ❌ Parse terminal output
- ❌ Parse screenshot filenames
- ❌ Guess actions from event names
- ❌ Infer failures from filenames
- ❌ Generate fake descriptions
- ❌ Repair missing data
- ❌ Use fallback text

**If timeline is incomplete, report generation must fail**:
```python
if not execution_result.timeline:
    raise ValueError("Execution timeline incomplete. Report generation aborted.")
```

### Changes Required

**File 1**: `backend/services/playwright_runner.py`

**Function**: `run()` method (lines 97-353)

**Specific Changes**:

1. **Inject Minimal Raw Event Emitter**: Playwright scripts emit only raw browser automation facts with actual results:
   ```python
   def run(self, script: str, run_id: str, test_case=None, **kwargs) -> PlaywrightRunResult:
       # Inject minimal event emitter - NO semantic enrichment
       event_emitter = """
       // Emit minimal raw execution events with actual results
       function emitRawEvent(event_type, target, success, actual, error_message = null, details = null) {
           const event = {
               timestamp: new Date().toISOString(),
               event_type: event_type,
               target: target,
               success: success,
               actual: actual,  // What actually happened
               error_message: error_message,
               details: details
           };
           console.log('RAW_EVENT:' + JSON.stringify(event));
       }
       """
       
       # Inject lightweight wrapper - focus on browser automation only
       wrapper = self._generate_minimal_wrapper()
       
       spec_content = event_emitter + wrapper + "\n" + script
       # ... write to test.spec.ts ...
   ```

2. **Minimal Wrapper - Pure Browser Automation**: Generate wrapper with actual results:
   ```python
   def _generate_minimal_wrapper(self) -> str:
       return """
       // Wrap page.goto - emit raw event with actual result
       const originalGoto = page.goto.bind(page);
       page.goto = async (url, options) => {
           try {
               const result = await originalGoto(url, options);
               const pageTitle = await page.title();
               
               // Emit raw event with actual result
               emitRawEvent(
                   'goto',
                   url,
                   true,
                   `Navigated to ${url}`,  // Actual result
                   null,
                   { page_title: pageTitle }
               );
               
               // Take screenshot
               await page.screenshot({ path: `screenshot-${Date.now()}.png` });
               
               return result;
           } catch (error) {
               emitRawEvent(
                   'goto',
                   url,
                   false,
                   `Failed to navigate to ${url}`,  // Actual result
                   error.message,
                   null
               );
               throw error;
           }
       };
       
       // Wrap page.click - emit raw event with actual result
       const originalClick = page.click.bind(page);
       page.click = async (selector, options) => {
           try {
               const result = await originalClick(selector, options);
               
               emitRawEvent(
                   'click',
                   selector,
                   true,
                   `Clicked ${selector}`,  // Actual result
                   null,
                   null
               );
               
               await page.screenshot({ path: `screenshot-${Date.now()}.png` });
               return result;
           } catch (error) {
               emitRawEvent(
                   'click',
                   selector,
                   false,
                   `Failed to click ${selector}`,  // Actual result
                   error.message,
                   null
               );
               throw error;
           }
       };
       
       // Wrap page.fill - emit raw event with actual result
       const originalFill = page.fill.bind(page);
       page.fill = async (selector, value, options) => {
           try {
               const result = await originalFill(selector, value, options);
               
               emitRawEvent(
                   'fill',
                   selector,
                   true,
                   `Filled ${selector} with value`,  // Actual result
                   null,
                   { value_length: value.length }
               );
               
               await page.screenshot({ path: `screenshot-${Date.now()}.png` });
               return result;
           } catch (error) {
               emitRawEvent(
                   'fill',
                   selector,
                   false,
                   `Failed to fill ${selector}`,  // Actual result
                   error.message,
                   { value_length: value.length }
               );
               throw error;
           }
       };
       
       // Similar wrapping for selectOption, etc.
       """
   ```
       
       // Similar wrapping for selectOption, etc. - all emit raw events only
       """
   ```

3. **Parse Raw Events from stdout**: In the output capturing loop:
   ```python
   raw_events = []
   for line_str in stdout_lines:
       if line_str.startswith('RAW_EVENT:'):
           try:
               event_json = line_str[len('RAW_EVENT:'):]
               event = json.loads(event_json)
               raw_events.append(event)
           except json.JSONDecodeError as e:
               print(f"[PlaywrightRunner] Failed to parse raw event: {e}")
   ```

4. **Return Raw Events in PlaywrightRunResult**:
   ```python
   return PlaywrightRunResult(
       status=status,
       duration_seconds=test_result.get("duration", 0) / 1000.0,
       error_message=error_message,
       screenshot_path=attachments.get("screenshot"),
       video_path=attachments.get("video"),
       trace_path=attachments.get("trace"),
       raw_events=raw_events  # Raw events - NO semantic enrichment
   )
   ```

**File 2**: `backend/services/timeline_builder.py` (NEW FILE)

**Function**: `TimelineBuilder.build()` method

**Specific Changes**:

1. **Create TimelineBuilder as Pure Merger**: NO text generation, only merging:
   ```python
   class TimelineBuilder:
       """
       Merges test case steps + raw execution events + artifacts into structured timeline.
       NO text generation. NO inference. Pure data merging only.
       """
       
       def build(
           self, 
           raw_events: list[dict], 
           test_case,
           run_id: str,
           artifacts_dir: Path
       ) -> list[dict]:
           """
           Build structured timeline by merging:
             - Test case steps (action, expected) 
             - Raw events (actual, status, timestamp)
             - Artifacts (screenshots, video, trace)
           
           Args:
               raw_events: Raw events from PlaywrightRunner
               test_case: TestCase model with structured steps
               run_id: Execution ID for artifact paths
               artifacts_dir: Directory containing screenshots, videos, traces
           
           Returns:
               Structured timeline events - pure merge, zero text generation
           """
           if not test_case or not test_case.steps:
               raise ValueError("TestCase with structured steps is required for timeline construction")
           
           if len(raw_events) < len(test_case.steps):
               raise ValueError(
                   f"Execution incomplete: {len(raw_events)} events but {len(test_case.steps)} steps expected. "
                   f"Some test case steps did not execute."
               )
           
           timeline = []
           start_time = None
           
           # Filter out screenshot events - they're attachments, not execution steps
           execution_events = [e for e in raw_events if e["event_type"] != "screenshot"]
           
           for step_index in range(1, len(test_case.steps) + 1):
               # Get test case step (source of semantic content)
               test_case_step = test_case.steps[step_index - 1]
               
               # Get corresponding raw event (source of execution facts)
               if step_index > len(execution_events):
                   raise ValueError(f"Missing raw event for step {step_index}")
               raw_event = execution_events[step_index - 1]
               
               # Calculate duration
               end_time = datetime.fromisoformat(raw_event["timestamp"].replace('Z', '+00:00'))
               if start_time:
                   duration_ms = int((end_time - start_time).total_seconds() * 1000)
               else:
                   duration_ms = 0
               
               # Determine status from raw event
               status = "PASS" if raw_event["success"] else "ERROR"
               
               # Find artifacts
               screenshot = self._find_screenshot_for_step(step_index, artifacts_dir)
               
               # Build timeline event by MERGING - no text generation
               timeline_event = {
                   "step": step_index,
                   "title": f"Step {step_index}: {test_case_step.action}",  # Template ONLY for title
                   "action": test_case_step.action,  # FROM TEST CASE
                   "expected": test_case_step.expected,  # FROM TEST CASE
                   "actual": raw_event["actual"],  # FROM RAW EVENT
                   "status": status,  # FROM RAW EVENT
                   "start_time": start_time.isoformat() if start_time else raw_event["timestamp"],
                   "end_time": raw_event["timestamp"],  # FROM RAW EVENT
                   "duration_ms": duration_ms,  # CALCULATED
                   "screenshot": screenshot,  # FROM ARTIFACTS
                   "video": None,  # Populated after loop
                   "trace": None,  # Populated after loop
                   "page": raw_event.get("details", {}).get("page_title"),  # FROM RAW EVENT
                   "dataset_row": None,  # Future: from test case if data-driven
                   "error": raw_event.get("error_message"),  # FROM RAW EVENT
                   "details": {
                       "event_type": raw_event["event_type"],
                       "target": raw_event["target"],
                       **raw_event.get("details", {})
                   }
               }
               
               timeline.append(timeline_event)
               start_time = end_time
           
           # Attach video and trace paths to all events
           video_path = self._find_artifact(artifacts_dir, "*.webm")
           trace_path = self._find_artifact(artifacts_dir, "*.zip")
           
           for event in timeline:
               event["video"] = video_path
               event["trace"] = trace_path
           
           return timeline
       
       def _find_screenshot_for_step(self, step_index: int, artifacts_dir: Path) -> str | None:
           """Find screenshot file for given step index"""
           # Look for screenshots in chronological order
           screenshots = sorted(artifacts_dir.glob("screenshot-*.png"))
           if step_index <= len(screenshots):
               return screenshots[step_index - 1].name
           return None
       
       def _find_artifact(self, artifacts_dir: Path, pattern: str) -> str | None:
           """Find artifact file matching pattern"""
           artifacts = list(artifacts_dir.glob(pattern))
           return artifacts[0].name if artifacts else None
   ```

2. **Validation**: Ensure test case has structured steps:
   ```python
   # In Execution API, before calling TimelineBuilder
   if not isinstance(test_case.steps[0], dict) or "action" not in test_case.steps[0]:
       raise ValueError(
           "TestCase.steps must be structured with 'action' and 'expected' fields. "
           f"Got: {test_case.steps[0]}"
       )
   ```

**File 3**: `backend/main.py`

**Function**: `/api/v1/projects/{project_id}/testcases/{test_case_id}/execute` endpoint

**Specific Changes**:

1. **Invoke PlaywrightRunner then TimelineBuilder**: Two-step process:
   ```python
   @app.post("/api/v1/projects/{project_id}/testcases/{test_case_id}/execute")
   async def execute_test_case(project_id: UUID, test_case_id: UUID):
       test_case = repo.get_test_case(test_case_id)
       
       # Step 1: Execute test (get raw events)
       playwright_result = playwright_runner.run(
           script=test_case.playwright_script,
           run_id=str(uuid4()),
           test_case=test_case,  # Pass for artifact naming only
           storage_state=storage_state_path,
           # ... other params ...
       )
       
       # Step 2: Build structured timeline from raw events
       timeline_builder = TimelineBuilder()
       timeline = timeline_builder.build(
           raw_events=playwright_result.raw_events,
           test_case=test_case,
           run_id=playwright_result.run_id,
           artifacts_dir=Path(f"backend/playwrightt/artifacts/{playwright_result.run_id}")
       )
       
       # Step 3: Persist execution result with structured timeline
       result = ExecutionResult(
           id=uuid4(),
           test_case_id=test_case_id,
           status=ExecutionStatus[playwright_result.status],
           duration_seconds=playwright_result.duration_seconds,
           error_message=playwright_result.error_message,
           screenshot_path=playwright_result.screenshot_path,
           video_path=playwright_result.video_path,
           trace_path=playwright_result.trace_path,
           timeline=timeline,  # Structured timeline from TimelineBuilder
           executed_at=datetime.now(timezone.utc)
       )
       
       repo.save_execution_result(result)
       return result
   ```

**File 4**: `backend/playwrightt/app/api/execute/route.ts` (Next.js Workspace API)

**Function**: POST handler for execution

**Specific Changes**:

1. **Delegate to FastAPI Execution API**: Next.js workspace invokes the same execution + timeline building service:
   ```typescript
   export async function POST(request: Request) {
     const { test_case_id, project_id } = await request.json();
     
     // Call FastAPI execution API (which invokes PlaywrightRunner + TimelineBuilder)
     const response = await fetch(
       `http://localhost:8000/api/v1/projects/${project_id}/testcases/${test_case_id}/execute`,
       {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' }
       }
     );
     
     const executionResult = await response.json();
     
     // Store in local execution queue for real-time monitoring
     executionQueue.set(executionResult.id, {
       status: executionResult.status,
       timeline: executionResult.timeline
     });
     
     return NextResponse.json(executionResult);
   }
   ```

**Specific Changes**:

1. **Pure Timeline Renderer - No Inference**: Report Agent simply renders timeline events:
   ```python
   def compile_reports(self, project_id: UUID, execution_result: ExecutionResult, test_case=None):
       """
       Pure timeline renderer. No inference, no parsing, no reconstruction.
       Timeline is the single source of truth.
       """
       # Validate timeline exists and is complete
       timeline = execution_result.timeline
       
       if not timeline:
           raise ValueError(
               f"Execution timeline incomplete for execution {execution_result.id}. "
               "Report generation aborted. PlaywrightRunner must emit structured timeline events."
           )
       
       # Validate timeline event structure
       for i, event in enumerate(timeline):
           required_fields = ["step", "title", "action", "expected", "actual", "status", "duration_ms"]
           missing_fields = [f for f in required_fields if f not in event]
           if missing_fields:
               raise ValueError(
                   f"Timeline event {i} missing required fields: {missing_fields}. "
                   f"Report generation aborted."
               )
       
       # Pure rendering - simply loop and render each event
       html_report = self.generate_html_report_from_timeline(timeline, execution_result, test_case, project_id)
       
       # Optional: Add AI analysis section (NOT required for correct steps)
       if self.ai_analysis_enabled():
           ai_observations = self.generate_ai_observations(timeline, test_case)
           html_report = self.append_ai_section(html_report, ai_observations)
       
       return html_report
   ```

2. **Generate HTML Report from Timeline** - Pure loop rendering:
   ```python
   def generate_html_report_from_timeline(
       self, 
       timeline: list[dict], 
       execution_result: ExecutionResult, 
       test_case, 
       project_id: UUID
   ) -> str:
       """
       Pure renderer: Timeline events → HTML
       No mapping, no inference, no parsing.
       """
       html_steps = []
       
       # Simply loop and render each timeline event
       for event in timeline:
           # Extract fields directly - all required fields guaranteed to exist
           step_num = event["step"]
           title = event["title"]
           action = event["action"]
           expected = event["expected"]
           actual = event["actual"]
           status = event["status"]
           duration_ms = event["duration_ms"]
           screenshot = event.get("screenshot")
           error = event.get("error")
           
           # Map status to display icon
           status_display = {
               "PASS": "✅ Passed",
               "FAIL": "❌ Failed",
               "ERROR": "❌ Error",
               "SKIP": "⏭️ Skipped"
           }[status]
           
           # Build screenshot URL (embed under step, not separate entry)
           screenshot_html = ""
           if screenshot:
               screenshot_url = f"/api/v1/projects/{project_id}/executions/{execution_result.id}/artifacts/{screenshot}"
               screenshot_html = f'<img src="{screenshot_url}" alt="Screenshot for {title}" class="step-screenshot" />'
           
           # Render step HTML
           step_html = f"""
           <div class="step-card {status.lower()}">
               <div class="step-header">
                   <span class="step-number">{step_num}</span>
                   <span class="step-title">{title}</span>
                   <span class="step-status">{status_display}</span>
                   <span class="step-duration">{duration_ms}ms</span>
               </div>
               <div class="step-body">
                   <div class="step-field">
                       <strong>Action:</strong> {action}
                   </div>
                   <div class="step-field">
                       <strong>Expected:</strong> {expected}
                   </div>
                   <div class="step-field">
                       <strong>Actual:</strong> {actual}
                   </div>
                   {f'<div class="step-error"><strong>Error:</strong> {error}</div>' if error else ''}
                   {screenshot_html}
               </div>
           </div>
           """
           html_steps.append(step_html)
       
       # Assemble full report
       return self._build_html_template(html_steps, execution_result, test_case)
   ```

3. **Remove ALL Inference Functions**: Delete these functions entirely:
   - `map_timeline_event_to_step()` - No longer needed
   - `extract_step_number_from_filename()` - No longer needed
   - `parse_screenshot_filename()` - No longer needed
   - `self_heal_timeline_from_localhost()` - No longer needed
   - `parse_html_report_for_timeline()` - No longer needed
   - `generate_generic_fallback_step()` - No longer needed
   - `enrich_steps_with_llm()` - No longer needed for correct steps

4. **AI Analysis as Optional Consumer** - Reads from timeline, not from report:
   ```python
   def generate_ai_observations(self, timeline: list[dict], test_case) -> str:
       """
       Optional AI analysis - reads from structured timeline.
       Not required for correct step descriptions.
       """
       try:
           prompt = f"""
           Analyze this test execution:
           Test Case: {test_case.name}
           Timeline: {json.dumps(timeline, indent=2)}
           
           Provide:
           1. Test coverage assessment
           2. Performance analysis (step durations)
           3. Potential risks or edge cases
           4. Suggestions for improvement
           """
           return self.llm_service.generate(prompt)
       except Exception as e:
           print(f"[AI Observations] Optional AI analysis failed: {e}")
           return None
   ```

**File 6**: `backend/models/execution_result.py`

**Model**: `ExecutionResult`

**Specific Changes**:

1. **Ensure Timeline Field Uses Structured Schema**:
   ```python
   class ExecutionResult(BaseModel):
       id: UUID = Field(default_factory=uuid4)
       test_case_id: UUID
       status: ExecutionStatus
       duration_seconds: float
       error_message: str | None = None
       screenshot_path: str | None = None
       video_path: str | None = None
       trace_path: str | None = None
       timeline: list[dict] = Field(default_factory=list)  # Structured timeline events
       executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
   ```

## Testing Strategy

### Validation Approach

The testing strategy follows a three-phase approach: first, demonstrate the bug on unfixed code using exploratory tests; second, implement the fix and verify correct behavior with fix checking tests; third, ensure existing functionality is preserved with preservation checking tests.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm the root cause analysis by showing that timeline events lack semantic context and report step descriptions are generic.

**Test Plan**: Execute existing test cases using the unfixed code and capture the generated HTML reports. Parse the reports to extract step descriptions and compare them against the original test case step definitions. Verify that generic descriptions like "Execute test step: 'fill'" appear in the output.

**Test Cases**:
1. **Simple Login Test**: Execute a test case with steps ["Navigate to login page", "Enter username", "Enter password", "Click login button"] and verify that the report shows generic descriptions instead of these semantic steps (will fail on unfixed code)

2. **Timeline Extraction Test**: Execute a test case and examine `ExecutionResult.timeline` in the database to confirm it is empty or incomplete (will fail on unfixed code - timeline will be empty)

3. **Screenshot Filename Parsing Test**: Execute a test case where the screenshot wrapper generates a filename without proper semantic context (e.g., `step-01-.png`) and verify that the report mapping fails to extract meaningful descriptions (will fail on unfixed code)

4. **Webhook Timeline Test**: Monitor the webhook endpoint to confirm that timeline events are sent but not persisted to the ExecutionResult model (will fail on unfixed code)

**Expected Counterexamples**:
- Report HTML contains steps like `<div class="detail-row">Execute test step: 'goto'.</div>`
- ExecutionResult.timeline field is empty: `[]`
- Screenshot filenames lack semantic descriptions: `step-01-goto.png` instead of `step-01-navigate_to_login_page.png`
- Possible causes: missing test case context in screenshot wrapper, timeline not persisted to database, report mapping relying on fragile inference

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior: accurate step descriptions that match test case definitions.

**Pseudocode:**
```
FOR ALL execution_result WHERE isBugCondition(execution_result) DO
  // Re-run report compilation with fixed code
  reports := compile_reports_fixed(execution_result)
  
  // Verify timeline is populated
  ASSERT execution_result.timeline.length > 0
  
  // Verify step descriptions match test case
  test_case := get_test_case(execution_result.test_case_id)
  mapped_steps := reports.mapped_steps
  
  FOR i IN [0..length(test_case.steps)] DO
    ASSERT contains(mapped_steps[i].action, test_case.steps[i])
    ASSERT NOT mapped_steps[i].action.startsWith("Execute test step:")
  END FOR
  
  // Verify no screenshot events as separate steps
  FOR step IN mapped_steps DO
    ASSERT step.step_name != "Visual State Capture"
    ASSERT NOT step.step_name.endsWith(".png")
  END FOR
END FOR
```

**Test Cases**:
1. **Accurate Step Description Test**: Execute a test case with known steps and verify that the generated report's step descriptions exactly match the test case step definitions

2. **Timeline Persistence Test**: Execute a test case and verify that `ExecutionResult.timeline` contains structured events with `step_index`, `step_description`, `action_type`, and `screenshot_filename` fields

3. **Screenshot Attachment Test**: Execute a test case and verify that screenshots are attached to action steps via `screenshot_name` and `screenshot_url` fields, not as separate "Visual State Capture" steps

4. **Multi-Step Test**: Execute a test case with 5+ steps and verify that all steps appear in the report with correct descriptions and sequential step indices

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (i.e., all non-reporting functionality), the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL test_script WHERE NOT affects_report_generation(test_script) DO
  // Execute with original code
  result_original := playwright_runner_original.run(test_script)
  
  // Execute with fixed code
  result_fixed := playwright_runner_fixed.run(test_script)
  
  // Verify execution mechanics unchanged
  ASSERT result_original.status = result_fixed.status
  ASSERT result_original.duration_seconds ≈ result_fixed.duration_seconds  // Within tolerance
  ASSERT result_original.error_message = result_fixed.error_message
  
  // Verify artifacts generated
  ASSERT exists(result_original.screenshot_path) = exists(result_fixed.screenshot_path)
  ASSERT exists(result_original.video_path) = exists(result_fixed.video_path)
  ASSERT exists(result_original.trace_path) = exists(result_fixed.trace_path)
  
  // Verify screenshot files on disk unchanged
  IF exists(result_original.screenshot_path) THEN
    ASSERT file_exists(result_fixed.screenshot_path)
  END IF
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss (e.g., special characters in test case steps, empty steps, very long steps)
- It provides strong guarantees that behavior is unchanged for all non-reporting aspects

**Test Plan**: Observe behavior on UNFIXED code first for Playwright execution mechanics, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Execution Status Preservation**: Execute 100 random test scripts and verify that pass/fail status determination is identical between unfixed and fixed code

2. **Artifact Generation Preservation**: Execute test scripts with various configurations (headless/headed, with/without storage state, different timeouts) and verify that screenshot, video, and trace files are generated in the same locations with the same content

3. **Process Management Preservation**: Execute test scripts that timeout or crash and verify that process cleanup (kill process tree, close pipes) works identically

4. **Configuration Preservation**: Execute test scripts with various playwright.config.ts settings and verify that browser launch, timeout, and reporter configurations are respected identically

5. **Credential Injection Preservation**: Execute test scripts that require vault credentials and verify that TARGET_USERNAME and TARGET_PASSWORD environment variables are injected identically

6. **Storage State Preservation**: Execute test scripts that save authentication state and verify that the storageState file is created with identical content

### Unit Tests

- Test `map_timeline_event_to_step()` with structured timeline events containing step_index and step_description fields
- Test `map_timeline_event_to_step()` with legacy timeline events lacking structured fields (fallback behavior)
- Test screenshot attachment logic when event has screenshot_filename but no step_description
- Test timeline JSON parsing from stdout with valid and invalid JSON
- Test TEST_CASE_STEPS injection with various step arrays (empty, single step, 10+ steps, steps with special characters)
- Test report HTML generation with accurate vs generic step descriptions

### Property-Based Tests

- Generate random test case step arrays (0-20 steps, various string lengths and characters) and verify that injected TEST_CASE_STEPS constant is valid TypeScript
- Generate random timeline event structures and verify that map_timeline_event_to_step() never crashes and always returns valid step dictionaries
- Generate random execution results with various timeline lengths and verify that compile_reports() produces HTML with correct number of steps
- Generate random screenshot filenames and verify that sanitizeFilename() produces valid filesystem names

### Integration Tests

- End-to-end test: Create a test case with known steps, execute via FastAPI endpoint, retrieve ExecutionResult from database, verify timeline is populated, generate report, verify step descriptions match test case
- Batch execution test: Execute 5 test cases in a batch and verify that each execution result has a correctly populated timeline
- Error handling test: Execute a test case that fails mid-execution and verify that the timeline contains all steps up to the failure point with correct descriptions
- Screenshot attachment test: Execute a test case with 5 steps, verify that the generated report has 5 step cards with screenshots attached (not 10 steps with separate screenshot entries)
