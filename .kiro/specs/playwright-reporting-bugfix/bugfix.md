# Playwright Execution Pipeline & Reporting Architecture Bugfix

## Bug Condition Analysis

### Bug Condition C(X): Report Generation Produces Generic/Incorrect Step Descriptions

**Formal Definition:**
```
C(execution_result) = 
  ∃ step ∈ execution_result.report_steps WHERE
    (step.description = "Execute test step: '{generic_event}'" OR
     step.description = "Visual State Capture" OR
     step.screenshot_filename IN step.error_messages) AND
    step.description ≠ actual_automation_step(execution_result.test_case)
```

**Preservation Checking:**
The bug condition is preserved when:
1. Timeline events lack semantic context from the original test case steps
2. Screenshot filenames are mapped as execution steps instead of being attached to action steps
3. Generic event names from execution-engine.ts don't match test case step descriptions
4. LLM enrichment fails or is bypassed

**Fix Checking:**
The bug is fixed when:
1. Report steps accurately reflect test case step descriptions
2. Screenshots are correctly attached to their corresponding action steps
3. Timeline events include semantic context from test case design
4. Step-by-step execution flow matches test case definition

---

## Introduction

This document provides a comprehensive architecture audit of the Playwright execution pipeline and reporting system. The audit identifies critical issues where execution reports display generic placeholder text ("Execute test step", "Visual State Capture") instead of meaningful automation steps, screenshot filenames appear as failure messages, and the execution flow creates duplicate/incorrect artifact handling.

**Scope**: Complete flow from Dashboard execution trigger → FastAPI orchestration → Playwright Runner → Artifact collection → Report generation → HTML display

**Affected Components**:
- Frontend Dashboard (frontend/js/app.js, frontend/js/api.js)
- FastAPI Execution Endpoints (backend/main.py)
- Playwright Runner (backend/services/playwright_runner.py)
- Report Service (backend/services/report_service.py)
- Next.js Execution Engine (backend/playwrightt/lib/execution-engine.ts)
- Playwright Agent (backend/agents/playwright_agent.py)

---

## Glossary

| Term | Definition |
|------|------------|
| **Timeline Event** | Structured data logged during execution containing: timestamp, event name, type (info/success/warning/error), and optional details |
| **Execution Result** | Database model containing execution metadata, status, duration, error_message, screenshot_path, video_path, trace_path, and timeline array |
| **Artifact** | File generated during execution: screenshots (.png), videos (.webm), traces (.zip), console logs |
| **Report Step** | HTML report element displaying: step_name, action, expected, actual, status, screenshot |
| **Bug Condition C(X)** | Formal predicate that evaluates to TRUE when a bug is present in execution result X |
| **Playwright Runner** | Python wrapper (playwright_runner.py) that invokes `npx playwright test` via subprocess.Popen |
| **Execution Engine** | TypeScript module (execution-engine.ts) in Next.js workspace that wraps Playwright page methods |
| **Execution Queue** | TypeScript singleton (execution-queue.ts) that manages execution metadata and timeline events |

---

## Current Execution Architecture (AS-IS)

### Complete Execution Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ DASHBOARD (frontend/js/app.js)                                              │
│ - User clicks "Run", "Run Selected", or "Run Selected Batch"                │
│ - Calls API.executeTestCase(projectId, testCaseId)                          │
│ - OR API.executeBatch(projectId, testCaseIds)                               │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASTAPI ENDPOINTS (backend/main.py)                                         │
│ POST /api/v1/projects/{project_id}/testcases/{test_case_id}/execute        │
│ POST /api/v1/projects/{project_id}/batches/execute                          │
│                                                                              │
│ → Loads test_case from repository                                           │
│ → Validates test_case.playwright_script exists                              │
│ → Calls playwright_runner.run(script, run_id, on_log, storage_state, ...)  │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PLAYWRIGHT RUNNER (backend/services/playwright_runner.py)                   │
│ → Creates run directory: backend/playwrightt/artifacts/{run_id}/            │
│ → Injects screenshot wrapper code into script                               │
│ → Writes test.spec.ts and playwright.config.ts                              │
│ → Executes: subprocess.Popen(['npx', 'playwright', 'test', ...])           │
│ → Captures stdout/stderr in real-time via threading.Queue                   │
│ → Waits for report.json generation                                          │
│ → Parses report.json for status, duration, error_message                    │
│ → Returns PlaywrightRunResult                                               │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PLAYWRIGHT CLI (subprocess - npx playwright test)                           │
│ → Launches Chromium browser                                                 │
│ → Executes test.spec.ts                                                     │
│ → Screenshot wrapper intercepts page.goto(), fill(), click(), selectOption()│
│ → Saves screenshots: step-01-goto.png, step-02-click.png, ...              │
│ → Generates report.json, video.webm, trace.zip                              │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ARTIFACTS COLLECTION (playwright_runner._parse_report)                      │
│ → Reads report.json                                                         │
│ → Extracts status, duration, error_message from test result                │
│ → Extracts attachments: screenshot, video, trace paths                      │
│ → Returns PlaywrightRunResult to FastAPI                                    │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ EXECUTION RESULT CREATION (backend/main.py)                                 │
│ → Creates ExecutionResult model instance                                    │
│ → Sets: status, duration_seconds, error_message                             │
│ → Sets: screenshot_path, video_path, trace_path                             │
│ → **MISSING**: Timeline events are NOT populated here                       │
│ → Saves to repository                                                       │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ REPORT SERVICE (backend/services/report_service.py)                         │
│ → compile_reports(project_id, execution_result)                             │
│ → Extracts raw_timeline from execution_result._raw_payload OR timeline attr│
│ → **BUG**: Timeline is often EMPTY or has generic events                    │
│ → Maps each timeline event → report step via map_timeline_event_to_step()   │
│ → **BUG**: Generic event names → generic step descriptions                  │
│ → Calls enrich_steps_with_llm() to enhance step descriptions                │
│ → Generates HTML report with steps                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ROOT CAUSE ANALYSIS

### Issue #1: Generic Step Descriptions ("Execute test step")

**Bug Condition:**
```
∀ step ∈ report_steps:
  IF step.action = "Execute test step: '{event_name}'"
  AND event_name IN ["goto", "click", "fill", "selectOption"]
  THEN bug_present = TRUE
```

**Root Cause:**
The `map_timeline_event_to_step()` function in `report_service.py` (lines 30-95) generates generic step descriptions because:

1. **Timeline events lack semantic context**: Events from `playwright_runner.py` only contain:
   ```python
   {
     "event": "goto",  # Generic action type
     "type": "info",
     "time": 0.5,
     "details": ""  # No test case step description
   }
   ```

2. **Test case steps are not linked**: The function attempts to match screenshot filenames to test case steps:
   ```python
   if test_case and step_num is not None and 1 <= step_num <= len(test_case.steps):
       step_desc = test_case.steps[step_num - 1]
       title = f"Step {step_num}: {step_desc}"
   ```
   But this only works if `screenshot_filename` follows format `step-01-xxx.png`. If the screenshot wrapper generates different filenames, the mapping fails.

3. **Fallback to generic text**: When mapping fails:
   ```python
   action_text = f"Execute test step: '{event_name}'."
   expected = f"Verify behavior of '{action_clean}'."
   actual = "Action executed without exceptions."
   ```

**Files Responsible:**
- `backend/services/report_service.py`: Lines 30-95 (map_timeline_event_to_step)
- `backend/services/playwright_runner.py`: Lines 200-280 (screenshot wrapper injection)

**Why This Happens:**
The screenshot wrapper in `playwright_runner.py` generates filenames based on:
```python
const sanitizeFilename = (str) => {
    return str.toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
  };
const filename = `step-${String(stepIndex).padStart(2, '0')}-${cleanDesc}.png`;
```

The `cleanDesc` comes from `lastTimelineMessage` (set by `console.log('[Timeline] ...')`), but this is OPTIONAL in the user's script. If the user's script doesn't call `addTimelineEvent()`, `lastTimelineMessage` is empty, resulting in filenames like `step-01-.png` which don't match the regex in `map_timeline_event_to_step()`.

---

### Issue #2: Screenshot Filenames Appearing as Failure Messages

**Bug Condition:**
```
∃ step ∈ report_steps:
  step.title = "{screenshot_filename}.png"
  AND step.status = "❌ Failed"
```

**Root Cause:**
In `map_timeline_event_to_step()` (lines 70-85), when a screenshot filename is detected but can't be matched to a test case step, the function creates a generic "Visual State Capture" step:

```python
if screenshot_filename:
    # ... matching logic ...
    else:
        title = "Visual State Capture"
        action_text = "Capture screenshot to record browser visual state."
        expected = f"Visual state captured in file '{screenshot_filename}'."
        actual = "Screenshot image saved on disk."
```

However, if `evt_type == "error"` or `"error" in event_name.lower()`, the status is set to "❌ Failed" regardless of whether it's a screenshot event:

```python
status = "✅ Passed" if (evt_type != "error" and "error" not in event_name.lower()) else "❌ Failed"
```

This creates a conflict: a screenshot event that happens to have "error" in its filename (e.g., `error-2024-01-01.png`) will be marked as failed even though it's just a visual capture.

**Files Responsible:**
- `backend/services/report_service.py`: Lines 30-95 (map_timeline_event_to_step)

---

### Issue #3: Timeline Events Are Empty or Incomplete

**Bug Condition:**
```
execution_result.timeline = [] OR len(execution_result.timeline) < expected_steps
```

**Root Cause:**
The `playwright_runner.py` does NOT populate the `timeline` field of the `ExecutionResult`. It only returns a `PlaywrightRunResult` with:
- status
- duration_seconds
- error_message
- screenshot_path (single failure screenshot)
- video_path
- trace_path

The timeline events are ONLY captured in the **Next.js Execution Engine** (`execution-engine.ts`), which:
1. Wraps Playwright methods (page.goto, locator.click, etc.)
2. Calls `executionQueue.addTimelineEvent(executionId, event, type, details)`
3. Stores timeline in the in-memory `executionQueue`
4. Sends timeline via webhook to FastAPI

**However**, the FastAPI endpoint that receives webhook events is:
```
POST /api/v1/projects/{project_id}/executions/webhook
```

This endpoint is DEFINED in `backend/main.py` but the grep search shows it's likely receiving the webhook data but NOT persisting it to the `ExecutionResult.timeline` field.

**Files Responsible:**
- `backend/main.py`: Missing webhook endpoint implementation or incomplete timeline persistence
- `backend/services/playwright_runner.py`: Doesn't capture timeline events (by design - it delegates to subprocess)

---

### Issue #4: Duplicate Execution Paths (FastAPI vs Next.js)

**Bug Condition:**
```
execution_initiated_from_dashboard AND execution_initiated_from_nextjs_workspace
```

**Root Cause:**
There are TWO independent execution paths:

**Path A: Dashboard → FastAPI → Playwright Runner (subprocess)**
```
frontend/js/app.js → API.executeTestCase()
  ↓
backend/main.py → POST /testcases/{id}/execute
  ↓
backend/services/playwright_runner.py → subprocess.Popen(['npx', 'playwright', 'test'])
  ↓
Playwright CLI executes test.spec.ts
```

**Path B: Next.js Workspace → Next.js Execution Engine → Playwright API**
```
backend/playwrightt/app/page.tsx → handleExecute()
  ↓
POST /api/execute (Next.js API route)
  ↓
backend/playwrightt/lib/execution-engine.ts → ExecutionEngine.run()
  ↓
Playwright API (chromium.launch, page.goto, etc.) - DIRECT API CALLS
```

**The Problem:**
- Path A uses **subprocess** to invoke Playwright CLI, which is isolated from the execution context
- Path B uses **Playwright Node.js API directly**, which allows wrapping methods and capturing timeline events
- Path A generates artifacts in `backend/playwrightt/artifacts/{run_id}/`
- Path B generates artifacts in `backend/playwrightt/public/artifacts/{execution_id}/`
- Reports generated from Path A executions have NO timeline context because `playwright_runner.py` can't introspect the subprocess

**Files Responsible:**
- `backend/main.py`: FastAPI execution endpoint (Path A)
- `backend/playwrightt/app/page.tsx`: Next.js workspace execution (Path B)
- `backend/playwrightt/lib/execution-engine.ts`: Direct Playwright API execution (Path B)

---

### Issue #5: Screenshot Wrapper Generates Incorrect Filenames

**Bug Condition:**
```
screenshot_filename = "step-{index}-.png"  # Missing description
OR
screenshot_filename NOT IN execution_result.artifacts.screenshots
```

**Root Cause:**
The screenshot wrapper injected by `playwright_runner.py` (lines 200-280) relies on `console.log('[Timeline] ...')` to populate `lastTimelineMessage`:

```typescript
const origConsoleLog = console.log;
console.log = function(...args) {
  origConsoleLog(...args);
  const msg = args.join(' ');
  if (msg.startsWith('[Timeline]')) {
    lastTimelineMessage = msg.replace('[Timeline]', '').trim();
  }
};

const takeStepScreenshot = async (actionName: string) => {
  stepIndex++;
  const cleanDesc = sanitizeFilename(lastTimelineMessage || actionName);
  const filename = `step-${String(stepIndex).padStart(2, '0')}-${cleanDesc}.png`;
  // ...
};
```

**Problem 1**: If the user's script doesn't call `addTimelineEvent()` or `console.log('[Timeline] ...')`, then `lastTimelineMessage` is empty, resulting in filenames like `step-01-goto.png` (using the generic `actionName`).

**Problem 2**: The `sanitizeFilename` function converts descriptions to lowercase and replaces non-alphanumeric characters with underscores, making them hard to match back to the original test case steps.

**Files Responsible:**
- `backend/services/playwright_runner.py`: Lines 200-280 (screenshot wrapper injection)

---

### Issue #6: LLM Enrichment Fails or Is Bypassed

**Bug Condition:**
```
mapped_steps.action = "Execute test step: '{event}'"
AFTER enrich_steps_with_llm(mapped_steps, test_case)
```

**Root Cause:**
The `enrich_steps_with_llm()` function in `report_service.py` (lines 97-155) attempts to enhance step descriptions using the LLMService, but:

1. **Error handling silently fails**: All exceptions are caught and logged, but the function returns the original `mapped_steps` unchanged:
   ```python
   except Exception as e:
       print(f"[LLM Report Enrichment Error]: {e}")
   return mapped_steps  # Returns original steps even if enrichment failed
   ```

2. **LLM service may not be configured**: If Ollama or the configured LLM is not running, the enrichment silently fails

3. **Input data is poor quality**: If `mapped_steps` already have generic descriptions, the LLM has limited context to improve them

**Files Responsible:**
- `backend/services/report_service.py`: Lines 97-155 (enrich_steps_with_llm)

---

### Issue #7: Timeline Self-Healing Mechanisms Are Unreliable

**Bug Condition:**
```
raw_timeline = []
AFTER self_healing_attempt_1() AND self_healing_attempt_2()
```

**Root Cause:**
The `compile_reports()` function includes "self-healing" logic to recover timeline data when it's missing (lines 170-200):

```python
if not raw_timeline:
    # 1. Try to fetch from local Next.js status API
    try:
        url = f"http://localhost:3000/api/status?id={execution_id_str}"
        with urllib.request.urlopen(url, timeout=1) as response:
            data = json.loads(response.read().decode('utf-8'))
            raw_timeline = data.get("timeline", [])
    except Exception:
        pass

if not raw_timeline:
    # 2. Try to parse from Next.js report.html file on disk
    next_report_path = Path("backend/playwrightt/public/artifacts") / execution_id_str / "report.html"
    # ... regex parsing ...
```

**Problems:**
1. **Cross-process dependency**: Relies on Next.js dev server running on localhost:3000
2. **Timeout issues**: 1-second timeout may not be sufficient
3. **File system race condition**: report.html may not exist yet when compile_reports() is called
4. **Fragile regex parsing**: HTML parsing with regex is error-prone

**Files Responsible:**
- `backend/services/report_service.py`: Lines 170-200 (self-healing logic)

---

## Correct Execution Architecture (TO-BE)

### Proposed Fix: Unified Timeline Capture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PLAYWRIGHT RUNNER (backend/services/playwright_runner.py)                   │
│ → Inject enhanced screenshot wrapper that:                                  │
│   1. Reads test_case.steps from metadata                                    │
│   2. Maps stepIndex → test_case.steps[stepIndex-1]                          │
│   3. Logs structured timeline events to stdout in JSON format               │
│ → Parse stdout for JSON timeline events                                     │
│ → Build timeline array in PlaywrightRunResult                               │
│ → Return timeline to FastAPI                                                │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ EXECUTION RESULT CREATION (backend/main.py)                                 │
│ → Set execution_result.timeline = playwright_result.timeline                │
│ → Save to repository with complete timeline data                            │
└────────────────────────────┬────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ REPORT SERVICE (backend/services/report_service.py)                         │
│ → Read execution_result.timeline (already populated)                        │
│ → Map timeline events to report steps with semantic context                 │
│ → Attach screenshots to correct steps                                       │
│ → Generate HTML report with accurate step descriptions                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Architectural Recommendations

### Recommendation #1: Structured Timeline Logging

**Current State**: Timeline events are implicit (inferred from screenshots and console logs)

**Proposed State**: Timeline events are explicit JSON structures logged to stdout

**Implementation**:
```typescript
// In screenshot wrapper (playwright_runner.py injection)
const logTimelineEvent = (step_index: number, step_description: string, action_type: string) => {
  const event = {
    type: 'TIMELINE_EVENT',
    timestamp: new Date().toISOString(),
    step_index: step_index,
    step_description: step_description,
    action_type: action_type
  };
  console.log(JSON.stringify(event));
};
```

**Benefit**: Playwright runner can parse JSON events from stdout and build a structured timeline

---

### Recommendation #2: Test Case Context Injection

**Current State**: Screenshot wrapper has no knowledge of test case steps

**Proposed State**: Test case steps are injected as a constant in test.spec.ts

**Implementation**:
```python
# In playwright_runner.py
test_case_steps = test_case.steps if test_case else []
context_injection = f"const TEST_CASE_STEPS = {json.dumps(test_case_steps)};\n"
spec_content = context_injection + screenshot_wrapper + "\n" + script
```

**Benefit**: Screenshot wrapper can reference TEST_CASE_STEPS[stepIndex-1] for accurate descriptions

---

### Recommendation #3: Eliminate Duplicate Execution Paths

**Current State**: Two independent execution paths (FastAPI subprocess vs Next.js API)

**Proposed State**: Single execution path with optional UI wrapper

**Options**:
- **Option A**: FastAPI always uses `playwright_runner.py` (subprocess), Next.js workspace is a viewer only
- **Option B**: Next.js workspace executes via Playwright API, FastAPI delegates to Next.js via HTTP
- **Option C**: Playwright runner refactored to use Playwright API directly (no subprocess)

**Recommendation**: Option A (maintain subprocess isolation, enhance timeline capture)

---

### Recommendation #4: Screenshot Attachment Strategy

**Current State**: Screenshots are mapped as separate steps

**Proposed State**: Screenshots are attached to action steps via step_index

**Implementation**:
```python
# In map_timeline_event_to_step()
if screenshot_filename:
    step_num = extract_step_number(screenshot_filename)
    if step_num and step_num <= len(mapped_steps):
        # Attach to existing step instead of creating new step
        mapped_steps[step_num - 1]["screenshot_name"] = screenshot_filename
        mapped_steps[step_num - 1]["screenshot_url"] = screenshot_url
        return None  # Don't create a new step
```

**Benefit**: Reports show screenshots inline with actions, not as separate "Visual State Capture" steps

---

### Recommendation #5: Webhook Integration Completion

**Current State**: Webhooks are sent but timeline may not be persisted

**Proposed State**: Webhook endpoint persists timeline events to ExecutionResult

**Implementation**:
```python
@app.post("/api/v1/projects/{project_id}/executions/webhook")
def execution_webhook(project_id: UUID, payload: dict):
    execution_id = payload.get("execution_id")
    event_type = payload.get("event")
    
    if event_type == "updated" and "timeline_event" in payload:
        # Append timeline event to execution_result
        execution = repo.get_execution_result(execution_id)
        if execution:
            if not hasattr(execution, 'timeline'):
                execution.timeline = []
            execution.timeline.append(payload["timeline_event"])
            repo.save_execution_result(execution)
```

**Benefit**: Timeline data is preserved even if Next.js process restarts

---

## Summary of Issues

| Issue | Bug Condition | Root Cause | Files Responsible |
|-------|---------------|------------|-------------------|
| Generic step descriptions | `step.action = "Execute test step: '{event}'"` | Timeline events lack semantic context from test case | `report_service.py`, `playwright_runner.py` |
| Screenshot filenames as failures | `step.title = "{filename}.png" AND step.status = "Failed"` | Screenshot events incorrectly classified as errors | `report_service.py` (map_timeline_event_to_step) |
| Empty timeline | `execution_result.timeline = []` | Playwright runner doesn't capture timeline, webhook doesn't persist | `playwright_runner.py`, `main.py` |
| Duplicate execution paths | Two independent execution flows | Dashboard uses subprocess, Next.js uses Playwright API | `main.py`, `execution-engine.ts` |
| Incorrect screenshot filenames | `filename = "step-01-.png"` (missing description) | Screenshot wrapper relies on optional console.log | `playwright_runner.py` (screenshot wrapper) |
| LLM enrichment fails | Steps remain generic after enrichment | Silent error handling, poor input data | `report_service.py` (enrich_steps_with_llm) |
| Unreliable self-healing | Timeline remains empty after recovery attempts | Cross-process dependencies, fragile parsing | `report_service.py` (compile_reports) |

---

## Next Steps

This bugfix requirements document establishes the bug conditions and root causes. The next phase is to create a **technical design document** that specifies:

1. Enhanced screenshot wrapper implementation with structured logging
2. Timeline capture and persistence architecture
3. Report step mapping algorithm improvements
4. Execution path consolidation strategy
5. Screenshot attachment mechanism
6. Detailed implementation tasks

