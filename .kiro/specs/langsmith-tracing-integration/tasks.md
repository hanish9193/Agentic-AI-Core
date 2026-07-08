# Implementation Plan: LangSmith Tracing Integration

## Overview

This plan implements LangSmith tracing for the Enterprise AI Test Automation Platform using a Template Method Pattern + Context Manager architecture. The implementation is divided into 5 phases to minimize risk:

1. **Phase 1: Infrastructure** - Add configuration and isolated tracing module (no existing code modified)
2. **Phase 2: Instrumentation** - Convert BaseAgent to template method pattern with CRITICAL pytest verification
3. **Phase 3: LLM Integration** - Attach LangSmith callbacks to capture metrics
4. **Phase 4: Persistence** - Add trace repository and storage
5. **Phase 5: UI Integration** - Add dashboard trace links and API endpoints

**Key Design Principles:**
- Template Method Pattern for BaseAgent (run() → _run())
- Manual trace context wrapping for run_workflow()
- Isolated LangSmith SDK imports in langsmith_tracer.py only
- Graceful degradation when tracing is disabled
- Zero overhead in production when disabled

## Tasks

### Phase 1: Infrastructure Setup (No Existing Code Modified)

- [x] 1. Create LangSmith configuration infrastructure
  - [x] 1.1 Add LangSmithConfig model to settings.py
    - Create LangSmithConfig class with fields: tracing_enabled, endpoint, api_key, project_name
    - Set default values: endpoint="https://api.smith.langchain.com", project_name="Enterprise-AI-TestAutomation"
    - Add LangSmithConfig field to Settings class
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [x] 1.2 Add environment variable loading in Settings.from_yaml()
    - Add LANGSMITH_TRACING environment variable with boolean cast
    - Add LANGSMITH_ENDPOINT environment variable override
    - Add LANGSMITH_API_KEY environment variable loading
    - Add LANGSMITH_PROJECT environment variable override
    - Follow existing _override() pattern for consistency
    - _Requirements: 1.5, 1.6, 1.8, 1.9, 9.6, 9.7_
  
  - [x] 1.3 Add LangSmith configuration to .env.example
    - Document LANGSMITH_TRACING=false (default disabled)
    - Document LANGSMITH_ENDPOINT with default URL
    - Document LANGSMITH_API_KEY requirement
    - Document LANGSMITH_PROJECT with default name
    - Add security warning about not hardcoding API keys
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

- [ ] 2. Create isolated LangSmith tracer module
  - [x] 2.1 Create backend/services/langsmith_tracer.py
    - Create LangSmithTracer class with __init__ that reads settings
    - Implement graceful initialization with try/except for Client creation
    - Add configuration error handling (missing API key when enabled)
    - Set self.enabled flag based on successful initialization
    - Add logging for initialization status
    - Import LangSmith SDK (Client, trace, get_current_run_tree) ONLY in this file
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6, 13.5_
  
  - [-] 2.2 Implement create_trace_context() context manager
    - Accept name (str) and metadata (dict) parameters
    - Return no-op context when tracing disabled
    - Use LangSmith trace() context manager when enabled
    - Yield _TraceContext with trace_id and record_exception() method
    - Catch and log tracing errors without propagating
    - _Requirements: 2.4, 13.1, 13.2, 13.3, 13.4, 13.6_
  
  - [ ] 2.3 Implement extract_metadata() helper method
    - Extract execution_id from state.execution_results if available
    - Extract project_id from state.requirement.project_id if available
    - Extract requirement_id and requirement_title from state.requirement
    - Extract scenario_count from state.generated_scenarios
    - Extract testcase_count from state.generated_test_cases
    - Extract approved counts from state selection fields
    - Extract model_name and llm_provider from settings
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11_
  
  - [x] 2.4 Create _TraceContext and _NoOpTraceContext classes
    - Implement _TraceContext with trace_id property and record_exception() method
    - Implement _NoOpTraceContext with no-op trace_id and record_exception()
    - Store run_tree reference in _TraceContext for exception recording
    - _Requirements: 2.4, 11.9, 12.1_
  
  - [~] 2.5 Implement get_tracer() singleton function
    - Create global _tracer variable
    - Return existing instance or create new LangSmithTracer
    - Export get_tracer as public API
    - _Requirements: 2.1, 2.2, 2.3_

- [ ] 3. Create unit tests for infrastructure
  - [ ]* 3.1 Write unit tests for LangSmithConfig loading
    - Test default values when no environment variables set
    - Test environment variable overrides for each config field
    - Test boolean parsing for LANGSMITH_TRACING
    - Test integration with Settings.from_yaml()
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 9.6_
  
  - [ ]* 3.2 Write unit tests for LangSmithTracer initialization
    - Test initialization with tracing disabled
    - Test initialization with tracing enabled and valid API key
    - Test graceful failure with missing API key
    - Test graceful failure with invalid endpoint
    - Test no-op mode when disabled
    - _Requirements: 2.2, 2.3, 2.5, 2.6, 13.5_
  
  - [ ]* 3.3 Write unit tests for extract_metadata()
    - Test metadata extraction from complete WorkflowState
    - Test metadata extraction from partial WorkflowState (missing fields)
    - Test scenario and testcase count extraction
    - Test approved count extraction
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11_

- [~] 4. Checkpoint - Infrastructure verification
  - Ensure all tests pass, ask the user if questions arise.

### Phase 2: BaseAgent Instrumentation (HIGHEST RISK)

- [ ] 5. Convert BaseAgent to template method pattern
  - [~] 5.1 Refactor BaseAgent.run() from abstract to concrete template method
    - Remove @abstractmethod decorator from run()
    - Implement run() as concrete method that calls get_tracer()
    - Add short-circuit path when tracing disabled (direct _run() call)
    - Create trace context with agent name and extracted metadata
    - Call self._run(state) within trace context
    - Handle exceptions with trace_ctx.record_exception() and re-raise
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.8, 11.1, 11.9_
  
  - [~] 5.2 Add abstract _run() method to BaseAgent
    - Create new @abstractmethod _run(state: WorkflowState) -> WorkflowState
    - Add docstring explaining child agents implement _run() not run()
    - _Requirements: 11.2, 11.3_

- [~] 6. **CRITICAL: Run full pytest suite after BaseAgent conversion**
  - **This is the highest-risk change - every agent inherits from BaseAgent**
  - Run `pytest` to verify ALL existing tests pass
  - If ANY test fails, STOP and fix before proceeding
  - Verify no regressions from BaseAgent template method pattern
  - This task BLOCKS all subsequent instrumentation work
  - _Requirements: 7.1, 7.2, 7.3, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_

- [ ] 7. Rename all child agent run() methods to _run()
  - [~] 7.1 Rename ScenarioAgent.run() to _run()
    - Change method signature from `def run(` to `def _run(`
    - No logic changes, only method name
    - Verify agent still works with BaseAgent.run() calling it
    - _Requirements: 3.1, 7.2, 11.2_
  
  - [~] 7.2 Rename TestCaseAgent.run() to _run()
    - Change method signature from `def run(` to `def _run(`
    - No logic changes, only method name
    - _Requirements: 3.2, 7.3, 11.2_
  
  - [~] 7.3 Rename EvaluationAgent.run() to _run()
    - Change method signature from `def run(` to `def _run(`
    - No logic changes, only method name
    - _Requirements: 3.3, 7.4, 11.2_
  
  - [~] 7.4 Rename PlaywrightAgent.run() to _run()
    - Change method signature from `def run(` to `def _run(`
    - No logic changes, only method name
    - _Requirements: 3.4, 7.5, 11.2_
  
  - [~] 7.5 Rename ExecutionAgent.run() to _run()
    - Change method signature from `def run(` to `def _run(`
    - No logic changes, only method name
    - _Requirements: 3.5, 7.6, 11.2_
  
  - [~] 7.6 Rename ReportAgent.run() to _run()
    - Change method signature from `def run(` to `def _run(`
    - No logic changes, only method name
    - _Requirements: 3.6, 7.7, 11.2_
  
  - [~] 7.7 Rename HumanApprovalAgent.run() to _run()
    - Change method signature from `def run(` to `def _run(`
    - No logic changes, only method name
    - _Requirements: 7.1, 11.2_

- [ ] 8. Instrument run_workflow() with manual trace context
  - [~] 8.1 Add trace context wrapping to run_workflow()
    - Import get_tracer at top of function
    - Add short-circuit path when tracing disabled (existing behavior)
    - Extract metadata with tracer.extract_metadata(initial_state)
    - Add workflow_name="run_workflow" to metadata
    - Wrap graph_instance.invoke() with create_trace_context()
    - Handle exceptions with trace_ctx.record_exception()
    - Do NOT modify graph.invoke() or build_graph()
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 11.1, 11.8_

- [ ] 9. Write integration tests for agent tracing
  - [ ]* 9.1 Write integration test for BaseAgent template method pattern
    - Create test agent subclass implementing _run()
    - Verify run() calls _run() correctly
    - Verify tracing context created when enabled
    - Verify no-op when disabled
    - _Requirements: 3.8, 11.9, 12.4_
  
  - [ ]* 9.2 Write integration test for run_workflow() tracing
    - Create mock graph with mock agents
    - Verify trace context created for workflow
    - Verify graph.invoke() called correctly
    - Verify graceful error handling
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 13.1, 13.6_

- [~] 10. Checkpoint - Agent instrumentation verification
  - Ensure all tests pass, ask the user if questions arise.

### Phase 3: LLM Integration

- [ ] 11. Implement LangChain callback integration
  - [~] 11.1 Implement attach_langchain_callback() in LangSmithTracer
    - Accept llm parameter (LangChain LLM instance)
    - Return llm unchanged if tracing disabled
    - Import LangSmithCallbackHandler with try/except for version compatibility
    - Create callback with project_name and client parameters
    - Initialize llm.callbacks list if not exists or None
    - Append callback to llm.callbacks list
    - Add graceful fallback with warning if callback unavailable
    - Log successful callback attachment
    - _Requirements: 6.1, 6.2, 13.5_
  
  - [~] 11.2 Integrate callback into ScenarioAgent LLM initialization
    - Import get_tracer in ScenarioAgent.__init__
    - Call tracer.attach_langchain_callback(self.llm) after LLM creation
    - No changes to LLM usage logic
    - _Requirements: 3.1, 6.1, 6.6, 11.2_
  
  - [~] 11.3 Integrate callback into TestCaseAgent LLM initialization
    - Import get_tracer in TestCaseAgent.__init__
    - Call tracer.attach_langchain_callback(self.llm) after LLM creation
    - _Requirements: 3.2, 6.1, 6.6, 11.2_
  
  - [~] 11.4 Integrate callback into EvaluationAgent LLM initialization
    - Import get_tracer in EvaluationAgent.__init__
    - Call tracer.attach_langchain_callback(self.llm) after LLM creation
    - _Requirements: 3.3, 6.1, 6.6, 11.2_
  
  - [~] 11.5 Integrate callback into PlaywrightAgent LLM initialization
    - Import get_tracer in PlaywrightAgent.__init__
    - Call tracer.attach_langchain_callback(self.llm) after LLM creation
    - _Requirements: 3.4, 6.1, 6.6, 11.2_
  
  - [~] 11.6 Integrate callback into ExecutionAgent if it uses LLM
    - Check if ExecutionAgent has LLM instance
    - If yes, call tracer.attach_langchain_callback(self.llm)
    - If no, skip this task
    - _Requirements: 3.5, 6.1, 6.6, 11.2_

- [ ] 12. Write unit tests for LangChain callback integration
  - [ ]* 12.1 Write unit test for attach_langchain_callback()
    - Test callback attachment to LLM with tracing enabled
    - Test no-op when tracing disabled
    - Test graceful fallback when callback unavailable
    - Test callback list initialization
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [~] 13. Checkpoint - LLM integration verification
  - Ensure all tests pass, ask the user if questions arise.

### Phase 4: Persistence Layer

- [ ] 14. Create trace repository and storage
  - [~] 14.1 Create TraceRecord dataclass in backend/repository/trace_repository.py
    - Define fields: trace_id, execution_id, project_id, requirement_id
    - Add workflow_name, status, duration_ms fields
    - Add started_at, finished_at, langsmith_project fields
    - Implement generate_trace_url() method with LangSmith URL format
    - Add docstring explaining minimal storage (no LangSmith data duplication)
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.9, 10.1, 10.2, 10.3, 10.4, 10.5_
  
  - [~] 14.2 Implement TraceRepository class
    - Set store_path to backend/database/trace_store.json
    - Implement _ensure_store() to create empty store if not exists
    - Implement save_trace() to append trace to JSON array
    - Implement get_trace_by_execution_id() for single trace lookup
    - Implement get_traces_by_requirement_id() for requirement traces
    - Implement get_traces_by_project_id() for project traces
    - Use file locking for concurrent write safety
    - _Requirements: 7.8, 11.4, 11.5_
  
  - [~] 14.3 Create backend/database/trace_store.json
    - Initialize file with {"traces": []} structure
    - Add to .gitignore if not already present
    - _Requirements: 7.8_

- [ ] 15. Integrate repository persistence into tracer
  - [~] 15.1 Implement persist_trace() in LangSmithTracer
    - Accept trace_id, workflow_name, metadata, status parameters
    - Return early if tracing disabled
    - Import TraceRepository
    - Call repo.save_trace() with extracted metadata
    - Add try/except with error logging (don't propagate)
    - _Requirements: 10.1, 10.2, 13.5, 13.7_
  
  - [~] 15.2 Add persist_trace() call to run_workflow() success path
    - Call tracer.persist_trace() after successful graph.invoke()
    - Pass trace_ctx.trace_id, workflow_name, metadata, status="success"
    - _Requirements: 4.8, 10.1_
  
  - [~] 15.3 Add persist_trace() call to run_workflow() error path
    - Call tracer.persist_trace() in exception handler
    - Pass trace_ctx.trace_id, workflow_name, metadata, status="error"
    - _Requirements: 3.11, 4.8, 10.1_

- [ ] 16. Write unit tests for trace repository
  - [ ]* 16.1 Write unit tests for TraceRepository persistence
    - Test save_trace() creates trace_store.json if missing
    - Test save_trace() appends to existing traces
    - Test get_trace_by_execution_id() returns correct trace
    - Test get_traces_by_requirement_id() returns all matching traces
    - Test concurrent write safety
    - _Requirements: 7.8, 11.4, 11.5_
  
  - [ ]* 16.2 Write unit tests for TraceRecord.generate_trace_url()
    - Test URL generation with valid trace_id and project name
    - Test URL format matches LangSmith documentation
    - _Requirements: 10.1, 10.2_

- [~] 17. Checkpoint - Persistence layer verification
  - Ensure all tests pass, ask the user if questions arise.

### Phase 5: UI Integration

- [ ] 18. Create trace API endpoints (if REST API exists)
  - [~] 18.1 Add GET /api/executions/{execution_id}/trace endpoint
    - Accept execution_id path parameter
    - Call TraceRepository.get_trace_by_execution_id()
    - Return trace metadata with generated trace_url
    - Return 404 if trace not found
    - _Requirements: 5.9, 10.1_
  
  - [~] 18.2 Add GET /api/requirements/{requirement_id}/traces endpoint
    - Accept requirement_id path parameter
    - Call TraceRepository.get_traces_by_requirement_id()
    - Return list of trace metadata with generated trace_urls
    - _Requirements: 5.3, 10.1_
  
  - [~] 18.3 Add GET /api/projects/{project_id}/traces endpoint
    - Accept project_id path parameter
    - Call TraceRepository.get_traces_by_project_id()
    - Return list of trace metadata with generated trace_urls
    - _Requirements: 5.1, 10.1_

- [ ] 19. Update execution dashboard UI (if dashboard exists)
  - [~] 19.1 Add "Open in LangSmith" button to execution page
    - Fetch trace metadata from /api/executions/{execution_id}/trace
    - Display button with trace_url as link target
    - Show button only if trace exists
    - Open LangSmith URL in new tab when clicked
    - _Requirements: 10.1_
  
  - [~] 19.2 Display trace status and duration on execution page
    - Show trace status (success/error) as badge
    - Show trace duration_ms formatted as seconds
    - Show trace started_at and finished_at timestamps
    - _Requirements: 10.3, 10.4_

- [ ] 20. Write integration tests for UI integration
  - [ ]* 20.1 Write integration test for trace API endpoints
    - Test GET /api/executions/{execution_id}/trace returns trace
    - Test GET /api/requirements/{requirement_id}/traces returns traces
    - Test 404 responses for missing traces
    - _Requirements: 5.9, 10.1_

- [~] 21. Final checkpoint - Complete integration verification
  - Run full pytest suite to verify no regressions
  - Verify tracing works end-to-end with real LangSmith project
  - Verify graceful degradation when tracing disabled
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional test tasks and can be skipped for faster MVP
- Phase 2 includes CRITICAL pytest checkpoint after BaseAgent conversion - this is the highest-risk change
- All tracing is non-breaking - existing workflows continue if tracing fails
- LangSmith SDK imports ONLY in backend/services/langsmith_tracer.py
- Template Method Pattern: BaseAgent.run() is concrete, child agents implement _run()
- Manual trace context wrapping in run_workflow() - never decorate graph.invoke()
- Trace repository stores ONLY correlation IDs and timestamps - no LangSmith data duplication
- UI integration tasks (Phase 5) may be skipped if REST API or dashboard don't exist yet

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1", "1.3"]
    },
    {
      "id": 1,
      "tasks": ["1.2", "2.1"]
    },
    {
      "id": 2,
      "tasks": ["2.2", "2.3", "2.4"]
    },
    {
      "id": 3,
      "tasks": ["2.5", "3.1", "3.2", "3.3"]
    },
    {
      "id": 4,
      "tasks": ["5.1"]
    },
    {
      "id": 5,
      "tasks": ["5.2"]
    },
    {
      "id": 6,
      "tasks": ["7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7"]
    },
    {
      "id": 7,
      "tasks": ["8.1", "9.1"]
    },
    {
      "id": 8,
      "tasks": ["9.2", "11.1"]
    },
    {
      "id": 9,
      "tasks": ["11.2", "11.3", "11.4", "11.5", "11.6"]
    },
    {
      "id": 10,
      "tasks": ["12.1", "14.1", "14.3"]
    },
    {
      "id": 11,
      "tasks": ["14.2"]
    },
    {
      "id": 12,
      "tasks": ["15.1"]
    },
    {
      "id": 13,
      "tasks": ["15.2", "15.3", "16.1", "16.2"]
    },
    {
      "id": 14,
      "tasks": ["18.1", "18.2", "18.3"]
    },
    {
      "id": 15,
      "tasks": ["19.1", "19.2", "20.1"]
    }
  ]
}
```
