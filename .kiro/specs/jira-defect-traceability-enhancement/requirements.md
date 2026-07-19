# Requirements Document

## Introduction

This document specifies the requirements for enhancing Jira integration with automatic step screenshot upload functionality and comprehensive defect traceability reporting. The system will automatically attach failed step screenshots to Jira issues and display a complete defect trace table in execution reports, providing clear visibility of all defects linked to test case executions.

## Glossary

- **Jira_Integration_Service**: The system component responsible for communicating with Jira API and managing Jira-related operations
- **Screenshot_Uploader**: The system component that uploads screenshot files to Jira issues as attachments
- **Defect_Trace_Table**: A tabular display in execution reports showing linked Jira defects with S.No, Defect ID, Description, and Status columns
- **Test_Case**: A test case entity in the platform that may have a linked Jira test case ID
- **Execution_Report**: A report generated after test case execution showing results, steps, and defect information
- **Failed_Step**: A test execution step that did not complete successfully
- **Step_Screenshot**: A screenshot image captured during test step execution
- **Jira_Issue**: A defect or issue entity in Jira identified by an issue key (e.g., PROJ-123)
- **Jira_Test_Case_ID**: The Jira issue key associated with a Test_Case in the platform
- **Defect_ID**: The unique Jira issue key identifying a specific defect (same as Jira issue key)
- **Issue_Summary**: The title or summary field of a Jira_Issue
- **Issue_Status**: The current workflow status of a Jira_Issue (e.g., Open, In Progress, Resolved, Closed)

## Requirements

### Requirement 1: Automatic Screenshot Upload for Failed Steps

**User Story:** As a QA engineer, I want failed step screenshots automatically uploaded to linked Jira issues, so that defect reports contain immediate visual evidence of the failure.

#### Acceptance Criteria

1. WHEN a Failed_Step occurs during test execution AND the Test_Case has a linked Jira_Test_Case_ID, THE Screenshot_Uploader SHALL upload the Step_Screenshot to the associated Jira_Issue as an attachment
2. WHEN the Screenshot_Uploader uploads a Step_Screenshot, THE Jira_Integration_Service SHALL verify the upload completed successfully
3. IF a screenshot upload fails, THEN THE Jira_Integration_Service SHALL log the error with the Jira_Issue key and failure reason
4. WHEN uploading a Step_Screenshot, THE Screenshot_Uploader SHALL include the step name and timestamp in the attachment filename
5. THE Screenshot_Uploader SHALL upload screenshots within 5 seconds of step failure detection

### Requirement 2: Defect Trace Table Display

**User Story:** As a QA engineer, I want to see a Jira Defect Trace table in execution reports, so that I can quickly review all defects associated with a test case execution.

#### Acceptance Criteria

1. WHEN an Execution_Report is generated for a Test_Case with a linked Jira_Test_Case_ID, THE Execution_Report SHALL display a Defect_Trace_Table section
2. THE Defect_Trace_Table SHALL contain columns for S.No, Defect_ID, Defect Description, and Status
3. THE Defect_Trace_Table SHALL number each defect row sequentially starting from 1
4. WHEN the Defect_Trace_Table is displayed, THE Execution_Report SHALL render the Defect_ID as a clickable hyperlink to the Jira_Issue
5. WHEN a Defect_ID hyperlink is clicked, THE Execution_Report SHALL open the Jira_Issue in a new browser tab

### Requirement 3: Jira Defect Data Synchronization

**User Story:** As a QA engineer, I want defect information synchronized from Jira, so that execution reports display current defect details and statuses.

#### Acceptance Criteria

1. WHEN generating an Execution_Report for a Test_Case with a linked Jira_Test_Case_ID, THE Jira_Integration_Service SHALL fetch all related Jira_Issues from Jira
2. THE Jira_Integration_Service SHALL retrieve the Issue_Summary for each Jira_Issue
3. THE Jira_Integration_Service SHALL retrieve the Issue_Status for each Jira_Issue
4. THE Jira_Integration_Service SHALL complete all Jira data retrieval within 10 seconds
5. IF Jira data retrieval fails, THEN THE Jira_Integration_Service SHALL display cached defect information with a staleness indicator

### Requirement 4: Defect Creation and Linking

**User Story:** As a QA engineer, I want newly created defects from failed steps to appear in the defect trace, so that I have a complete history of all issues discovered during execution.

#### Acceptance Criteria

1. WHEN a new Jira_Issue is created from a Failed_Step, THE Jira_Integration_Service SHALL link the Jira_Issue to the Test_Case
2. WHEN a new Jira_Issue is linked to a Test_Case, THE Execution_Report SHALL include the new Jira_Issue in the Defect_Trace_Table
3. THE Jira_Integration_Service SHALL update the Defect_Trace_Table with newly created defects within 3 seconds of creation
4. WHEN multiple Failed_Steps occur in a single execution, THE Jira_Integration_Service SHALL create or link separate Jira_Issues for each unique failure

### Requirement 5: Defect Relationship Discovery

**User Story:** As a QA engineer, I want to see all defects related to my test case, so that I understand the complete defect history without manual Jira searching.

#### Acceptance Criteria

1. WHEN a Test_Case has a linked Jira_Test_Case_ID, THE Jira_Integration_Service SHALL query Jira for all related defects using the Jira_Test_Case_ID
2. THE Jira_Integration_Service SHALL identify related defects by Jira issue links, parent-child relationships, or custom test case ID fields
3. THE Jira_Integration_Service SHALL include both open and closed Jira_Issues in the Defect_Trace_Table
4. THE Jira_Integration_Service SHALL sort defects in the Defect_Trace_Table by creation date with newest defects first

### Requirement 6: Screenshot File Management

**User Story:** As a system administrator, I want screenshot uploads to handle file naming and organization properly, so that Jira attachments are easily identifiable and don't conflict.

#### Acceptance Criteria

1. WHEN generating a screenshot filename, THE Screenshot_Uploader SHALL include the test case name, step number, and ISO 8601 timestamp
2. THE Screenshot_Uploader SHALL sanitize filenames to remove characters invalid in Jira attachments
3. THE Screenshot_Uploader SHALL support PNG, JPEG, and WebP image formats
4. WHEN uploading multiple screenshots to the same Jira_Issue, THE Screenshot_Uploader SHALL ensure each filename is unique

### Requirement 7: Error Handling and Resilience

**User Story:** As a QA engineer, I want the system to continue functioning when Jira is unavailable, so that test execution and reporting are not blocked by external service failures.

#### Acceptance Criteria

1. IF the Jira_Integration_Service cannot connect to Jira, THEN THE Execution_Report SHALL display a warning message indicating Jira is unreachable
2. WHEN Jira is unreachable, THE Execution_Report SHALL display cached defect information from the most recent successful synchronization
3. THE Jira_Integration_Service SHALL retry failed screenshot uploads up to 3 times with exponential backoff
4. IF screenshot upload fails after all retries, THEN THE Jira_Integration_Service SHALL queue the upload for later retry when Jira becomes available
5. WHEN Jira connectivity is restored, THE Jira_Integration_Service SHALL process all queued screenshot uploads within 60 seconds

### Requirement 8: Defect Trace Table Formatting

**User Story:** As a QA engineer, I want the defect trace table to be clearly formatted and readable, so that I can quickly scan defect information.

#### Acceptance Criteria

1. THE Defect_Trace_Table SHALL display Issue_Status values using color coding (green for Resolved/Closed, yellow for In Progress, red for Open)
2. THE Defect_Trace_Table SHALL truncate Defect Description text longer than 100 characters with an ellipsis
3. WHEN a truncated Defect Description is hovered, THE Execution_Report SHALL display the full Issue_Summary in a tooltip
4. THE Defect_Trace_Table SHALL display a message "No defects linked to this test case" when no related Jira_Issues exist
5. THE Defect_Trace_Table SHALL be collapsible with an expand/collapse toggle in the Execution_Report

### Requirement 9: Screenshot Attachment Metadata

**User Story:** As a QA engineer, I want screenshot attachments to include contextual metadata, so that I can understand what each screenshot represents without opening the execution report.

#### Acceptance Criteria

1. WHEN uploading a Step_Screenshot, THE Screenshot_Uploader SHALL add a comment to the Jira_Issue describing the failed step
2. THE Screenshot_Uploader comment SHALL include the step name, execution timestamp, and test case name
3. THE Screenshot_Uploader comment SHALL include a link back to the Execution_Report in the platform
4. WHEN multiple screenshots are uploaded for different steps, THE Screenshot_Uploader SHALL create separate comments for each upload

### Requirement 10: Performance and Scalability

**User Story:** As a system administrator, I want the Jira integration to handle high-volume test execution efficiently, so that the system remains responsive under load.

#### Acceptance Criteria

1. THE Jira_Integration_Service SHALL upload screenshots asynchronously without blocking test execution
2. THE Jira_Integration_Service SHALL support concurrent uploads of at least 10 screenshots simultaneously
3. WHEN generating reports for multiple test executions, THE Jira_Integration_Service SHALL batch fetch defect information in groups of 50 issues per API call
4. THE Jira_Integration_Service SHALL cache Jira_Issue details for 5 minutes to reduce API calls for frequently accessed defects
5. THE Screenshot_Uploader SHALL compress screenshots larger than 2MB before uploading to reduce bandwidth usage
