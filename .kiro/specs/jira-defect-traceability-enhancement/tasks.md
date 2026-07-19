# Implementation Plan: Jira Defect Traceability Enhancement

## Overview

This implementation plan breaks down the Jira defect traceability enhancement into discrete, executable coding tasks. The implementation focuses on five core areas: screenshot upload infrastructure, defect tracking services, report rendering, data model enhancements, and Jira service improvements. Each task builds incrementally, with early checkpoint validations to ensure correctness before moving to integration.

## Tasks

- [ ] 1. Set up core data models and infrastructure
  - [ ] 1.1 Create data model enhancements for step-level screenshot tracking
    - Add `StepScreenshot` dataclass to `backend/models/execution_result.py`
    - Add `step_screenshots` field to `ExecutionResult` model
    - Add JSON serialization/deserialization methods for `StepScreenshot`
    - _Requirements: 1.4, 6.1, 6.4_

  - [ ] 1.2 Create database migration for step screenshot tracking
    - Generate Alembic migration to add `step_screenshots_json` column to `ExecutionDB`
    - Add column as nullable JSON type
    - Test migration rollback and upgrade paths
    - _Requirements: 1.1_

  - [ ] 1.3 Enhance ExecutionReport model with defect trace support
    - Add `DefectTraceTable` dataclass to `backend/models/execution_report.py`
    - Add `defect_trace_tables` field to `ExecutionReport` model
    - Include `is_stale` flag for cache fallback scenarios
    - _Requirements: 2.1, 3.5_

  - [ ] 1.4 Create DefectInfo data model
    - Create `backend/models/defect_info.py` with `DefectInfo` dataclass
    - Include fields: `defect_id`, `summary`, `status`, `status_category`, `created_at`, `updated_at`, `url`
    - Add validation for Jira issue key format
    - _Requirements: 2.2, 2.3, 3.2, 3.3_

- [ ] 2. Implement screenshot upload service
  - [ ] 2.1 Create UploadQueueItem and UploadQueue
    - Create `backend/services/upload_queue.py`
    - Implement `UploadQueueItem` dataclass with retry metadata
    - Implement file-based JSON queue storage in `.upload_queue/` directory
    - Add methods: `enqueue`, `dequeue_ready`, `update_retry`, `remove`, `get_pending_count`
    - Implement exponential backoff calculation (5s, 10s, 20s)
    - _Requirements: 7.3, 7.4, 7.5_

  - [ ]* 2.2 Write unit tests for UploadQueue
    - Test enqueue/dequeue operations
    - Test exponential backoff scheduling
    - Test persistence across queue restarts
    - Test concurrent access scenarios
    - _Requirements: 7.3, 7.4_

  - [ ] 2.3 Implement ScreenshotUploader service
    - Create `backend/services/screenshot_uploader.py`
    - Implement `upload_step_screenshot` method with filename generation
    - Implement `_sanitize_filename` to remove invalid characters
    - Implement `_generate_filename` with format: `{testcase}_step{num}_{timestamp}.{ext}`
    - Implement `_add_upload_comment` with step context and report link
    - Add async upload using thread pool executor
    - Handle upload failures by queueing to `UploadQueue`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 6.2, 6.4, 9.1, 9.2, 9.3, 9.4_

  - [ ]* 2.4 Write unit tests for ScreenshotUploader
    - Test filename sanitization and generation
    - Test successful upload flow
    - Test failure handling and queue integration
    - Test comment creation with metadata
    - Mock JiraService and UploadQueue dependencies
    - _Requirements: 1.1, 6.1, 6.2_

  - [ ] 2.5 Implement UploadRetryWorker background service
    - Create `backend/services/upload_retry_worker.py`
    - Implement daemon thread with 10-second poll interval
    - Implement `_process_queue` to retry ready items
    - Add graceful shutdown handling
    - Add worker lifecycle management (start/stop methods)
    - _Requirements: 7.3, 7.4, 7.5_

  - [ ]* 2.6 Write integration tests for retry worker
    - Test queue processing and retry logic
    - Test graceful shutdown
    - Test concurrent upload handling
    - _Requirements: 7.5, 10.1, 10.2_

- [ ] 3. Checkpoint - Verify screenshot upload infrastructure
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement defect tracking services
  - [ ] 4.1 Create DefectCache service
    - Create `backend/services/defect_cache.py`
    - Implement `CacheEntry` dataclass with TTL tracking
    - Implement in-memory cache with 5-minute default TTL
    - Add methods: `get`, `set`, `invalidate`, `clear`
    - Implement lazy expiration checking on access
    - Add thread-safe locks for concurrent access
    - _Requirements: 3.5, 10.4_

  - [ ]* 4.2 Write unit tests for DefectCache
    - Test TTL expiration logic
    - Test cache hit/miss scenarios
    - Test concurrent access thread safety
    - Test cache invalidation
    - _Requirements: 10.4_

  - [ ] 4.3 Implement DefectFetcher service
    - Create `backend/services/defect_fetcher.py`
    - Implement `fetch_defects` for single test case with JQL query construction
    - Implement `fetch_defects_batch` with batching (50 test cases per call)
    - Implement `_parse_defect_info` to convert Jira API response to `DefectInfo`
    - Add concurrent batch execution using thread pool (max 3 concurrent)
    - Build JQL query to discover defects via issue links, parent-child, custom fields, and labels
    - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.2, 5.4, 10.3_

  - [ ]* 4.4 Write unit tests for DefectFetcher
    - Test JQL query construction for different relationship types
    - Test batch fetching logic
    - Test defect parsing from Jira API responses
    - Mock JiraService API calls
    - _Requirements: 5.1, 5.2_

  - [ ] 4.5 Implement DefectTrackerService orchestrator
    - Create `backend/services/defect_tracker_service.py`
    - Implement `get_defects_for_test_case` with cache-first lookup
    - Implement `get_defects_batch` for multiple test cases
    - Add `force_refresh` parameter to bypass cache
    - Integrate `DefectCache` and `DefectFetcher`
    - Sort defects by creation date (newest first)
    - Handle Jira connection errors with cached fallback
    - _Requirements: 3.1, 3.4, 3.5, 5.3, 5.4, 7.1, 7.2_

  - [ ]* 4.6 Write integration tests for DefectTrackerService
    - Test cache integration flow
    - Test force refresh behavior
    - Test batch fetching
    - Test error handling with cache fallback
    - Mock DefectCache and DefectFetcher
    - _Requirements: 3.5, 7.1, 7.2_

- [ ] 5. Checkpoint - Verify defect tracking services
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement defect trace rendering
  - [ ] 6.1 Create DefectTraceRenderer service
    - Create `backend/services/defect_trace_renderer.py`
    - Implement `render_defect_trace_table` to generate HTML table
    - Implement `_get_status_color` for status category color mapping
    - Implement `_truncate_description` for text truncation with ellipsis
    - Generate HTML with expand/collapse toggle button
    - Add clickable defect ID links opening in new tab
    - Add tooltips for truncated descriptions
    - Display "No defects linked to this test case" for empty results
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 6.2 Write unit tests for DefectTraceRenderer
    - Test HTML table generation with sample defects
    - Test status color mapping
    - Test description truncation
    - Test empty state rendering
    - Validate HTML structure and attributes
    - _Requirements: 2.1, 8.1, 8.2, 8.3_

  - [ ] 6.3 Add CSS styles for defect trace table
    - Add styles to report CSS file (location TBD based on existing report structure)
    - Define `.defect-trace-section`, `.defect-trace-table`, `.status-badge` classes
    - Add color coding: `.status-done` (green), `.status-in_progress` (yellow), `.status-to_do` (red)
    - Add hover effects and tooltip styles
    - Add responsive table layout
    - _Requirements: 8.1, 8.5_

- [ ] 7. Enhance JiraService with new capabilities
  - [ ] 7.1 Implement image compression in JiraService
    - Add `upload_attachment_with_compression` method to `backend/services/jira_service.py`
    - Use Pillow (PIL) for image compression
    - Set compression threshold at 2MB
    - Target 85% quality for JPEG, optimized PNG
    - Preserve aspect ratio and skip WebP files
    - _Requirements: 6.3, 10.5_

  - [ ]* 7.2 Write unit tests for compression logic
    - Test compression for images >2MB
    - Test preservation of images <2MB
    - Test different image formats (PNG, JPEG, WebP)
    - Verify quality and aspect ratio
    - _Requirements: 6.3, 10.5_

  - [ ] 7.3 Implement batch JQL search in JiraService
    - Add `batch_search_issues` method to `backend/services/jira_service.py`
    - Support concurrent JQL queries with configurable max concurrent (default 3)
    - Use thread pool executor for parallel execution
    - Return dictionary mapping query index to results
    - Add 10-second timeout per query
    - _Requirements: 10.3_

  - [ ]* 7.4 Write unit tests for batch search
    - Test concurrent query execution
    - Test timeout handling
    - Test result mapping
    - Mock Jira API calls
    - _Requirements: 10.3_

- [ ] 8. Integrate screenshot upload into execution flow
  - [ ] 8.1 Update ExecutionAgent to track step screenshots
    - Modify `backend/agents/execution_agent.py` to capture step-level screenshots
    - Populate `step_screenshots` list in `ExecutionResult`
    - Store screenshot paths with step number and name
    - Update database persistence to save `step_screenshots_json`
    - _Requirements: 1.1, 1.4_

  - [ ] 8.2 Integrate ScreenshotUploader into JiraSyncAgent
    - Modify `backend/agents/jira_sync_agent.py` to trigger uploads on failed steps
    - Call `ScreenshotUploader.upload_step_screenshot` for each failed step with screenshot
    - Pass test case name, step details, and execution timestamp
    - Generate report URL for comment links
    - _Requirements: 1.1, 1.5, 9.3_

  - [ ] 8.3 Integrate ScreenshotUploader into DefectManagementAgent
    - Modify `backend/agents/defect_management_agent.py` to upload screenshots when creating new defects
    - Upload screenshots immediately after defect creation
    - Link screenshot to newly created Jira issue
    - _Requirements: 4.1, 4.2_

  - [ ]* 8.4 Write integration tests for screenshot upload flow
    - Test end-to-end flow from failed step to Jira upload
    - Test screenshot tracking in ExecutionResult
    - Test upload triggering in agents
    - Mock ScreenshotUploader and verify calls
    - _Requirements: 1.1, 1.5_

- [ ] 9. Integrate defect tracking into report generation
  - [ ] 9.1 Update ReportAgent to fetch defect traces
    - Modify `backend/agents/report_agent.py` to call `DefectTrackerService.get_defects_batch`
    - Fetch defects for all test cases in execution report
    - Populate `defect_trace_tables` in `ExecutionReport`
    - Handle Jira connection errors with stale cache fallback
    - _Requirements: 2.1, 3.1, 3.4, 7.1, 7.2_

  - [ ] 9.2 Integrate DefectTraceRenderer into report generation
    - Call `DefectTraceRenderer.render_defect_trace_table` for each test case
    - Embed rendered HTML into execution report template
    - Pass Jira base URL from configuration
    - Display staleness warning when using cached data
    - _Requirements: 2.1, 2.4, 2.5, 7.1_

  - [ ] 9.3 Update report templates to include defect trace section
    - Modify HTML report templates to include defect trace table section
    - Position defect trace table below test case execution results
    - Add JavaScript for expand/collapse toggle functionality
    - Ensure responsive layout for different screen sizes
    - _Requirements: 2.1, 8.5_

  - [ ]* 9.4 Write integration tests for report generation with defect traces
    - Test report generation with defect traces
    - Test empty defect scenario
    - Test stale cache indicator
    - Verify HTML rendering correctness
    - _Requirements: 2.1, 7.1, 7.2_

- [ ] 10. Initialize services and configure application startup
  - [ ] 10.1 Initialize services in application startup
    - Modify `backend/main.py` to instantiate all new services
    - Create service instances: `UploadQueue`, `ScreenshotUploader`, `UploadRetryWorker`
    - Create service instances: `DefectCache`, `DefectFetcher`, `DefectTrackerService`, `DefectTraceRenderer`
    - Wire dependencies using dependency injection
    - Start `UploadRetryWorker` daemon thread
    - _Requirements: 1.5, 7.5_

  - [ ] 10.2 Add graceful shutdown handling
    - Register shutdown handler for `UploadRetryWorker`
    - Ensure pending uploads are persisted on shutdown
    - Add cleanup logic for temporary files
    - _Requirements: 7.5_

  - [ ] 10.3 Add configuration settings for new services
    - Add settings to `backend/config/settings.py` or config file
    - Configure: upload queue directory, retry settings, cache TTL, batch sizes
    - Configure: compression threshold, concurrent upload limit
    - Add Jira base URL configuration for link generation
    - _Requirements: 6.2, 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 11. Error handling and monitoring
  - [ ] 11.1 Add comprehensive error logging
    - Add structured logging for all upload failures with context
    - Add logging for defect fetch failures with JQL queries
    - Add logging for cache hits/misses
    - Add logging for retry attempts and exhaustion
    - _Requirements: 1.3, 7.3, 7.4_

  - [ ] 11.2 Implement admin notifications for critical failures
    - Add notification logic for retry exhaustion (after 3 retries)
    - Log critical errors with full context for admin review
    - Consider integration with existing notification system (email/Slack if available)
    - _Requirements: 7.4_

- [ ] 12. Final checkpoint - End-to-end validation
  - Ensure all tests pass, ask the user if questions arise.
  - Test complete flow: failed step → screenshot upload → defect creation → report generation with trace table
  - Verify retry mechanism handles transient failures
  - Verify cache reduces API calls as expected
  - Verify report rendering displays defect traces correctly

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Screenshot upload happens asynchronously and doesn't block test execution
- Defect trace fetching uses caching to optimize performance
- All new services use dependency injection for testability
- File-based queue ensures screenshot uploads survive application restarts
- The implementation builds incrementally with checkpoints to validate correctness
- Priority: Focus on screenshot upload (tasks 1-3) and defect tracking (tasks 4-5) before integration (tasks 8-9)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.4"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "4.1"] },
    { "id": 3, "tasks": ["2.4", "2.5", "4.2", "4.3"] },
    { "id": 4, "tasks": ["2.6", "4.4", "4.5", "6.1", "7.1"] },
    { "id": 5, "tasks": ["4.6", "6.2", "6.3", "7.2", "7.3"] },
    { "id": 6, "tasks": ["7.4", "8.1"] },
    { "id": 7, "tasks": ["8.2", "8.3"] },
    { "id": 8, "tasks": ["8.4", "9.1"] },
    { "id": 9, "tasks": ["9.2", "9.3"] },
    { "id": 10, "tasks": ["9.4", "10.1"] },
    { "id": 11, "tasks": ["10.2", "10.3", "11.1"] },
    { "id": 12, "tasks": ["11.2"] }
  ]
}
```
