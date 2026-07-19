# Requirements Document

## Introduction

This feature restructures the dashboard navigation to create a clearer hierarchical relationship between Projects and their child items (Requirements, Scenarios, Test Cases, etc.). Currently, the Project selector is positioned in the top navigation bar, which places Projects at the same visual level as other navigation items. The new design moves Project selection to a dedicated page accessible from the sidebar, and displays project-specific items as visually indented children below the selected project to clarify the parent-child relationship.

## Glossary

- **Dashboard**: The main application interface containing sidebar navigation and content workspace
- **Sidebar**: The left vertical navigation panel containing navigation items
- **Top_Navigation_Bar**: The horizontal bar at the top of the application containing project selector and user controls
- **Project_Page**: A dedicated view for displaying and selecting projects
- **QA_Dashboard**: The main dashboard view showing metrics and analytics
- **Project_Selector**: The dropdown UI component for selecting active projects
- **Navigation_Item**: A clickable element in the sidebar that navigates to a specific view
- **Indented_Navigation_Item**: A navigation item visually offset to the right to indicate hierarchical relationship
- **Selected_Project**: The currently active project whose data is being displayed
- **Child_Navigation_Items**: Navigation items that belong to a specific project (Requirements, Scenarios, Test Cases, etc.)

## Requirements

### Requirement 1: Remove Project Selector from Top Navigation

**User Story:** As a user, I want the Project selector removed from the top navigation bar, so that I can access projects through a clearer hierarchical structure.

#### Acceptance Criteria

1. THE Dashboard SHALL NOT display the project selector dropdown in the top navigation bar
2. THE Top_Navigation_Bar SHALL continue to display user controls and action buttons
3. WHERE user controls and action buttons fail to display, THE Dashboard SHALL allow access to the dashboard
4. THE Top_Navigation_Bar SHALL NOT display Release selector or Cycle selector controls
5. WHEN a user views the top navigation bar, THE Dashboard SHALL show a simplified header without project-related selectors

### Requirement 2: Add Project Page to Sidebar Navigation

**User Story:** As a user, I want a dedicated "Project" page accessible from the sidebar below "QA Dashboard", so that I can select and manage projects from a centralized location.

#### Acceptance Criteria

1. THE Sidebar SHALL display a "Project" navigation item below the "QA Dashboard" item
2. WHEN a user clicks the "Project" navigation item, THE Dashboard SHALL navigate to the Project_Page view
3. THE Project_Page SHALL display a list of all available projects exclusively on the Project page
4. THE Project_Page SHALL provide a search interface for filtering projects exclusively on the Project page
5. THE Project_Page SHALL display project details including name, description, and line of business exclusively on the Project page
6. THE Project_Page SHALL provide a button to create new projects exclusively on the Project page

### Requirement 3: Update Login Flow to Navigate to Dashboard First

**User Story:** As a user, I want to see the Dashboard immediately after login, so that I can view overall system status before selecting a project.

#### Acceptance Criteria

1. WHEN a user successfully logs in, THE Dashboard SHALL display the QA_Dashboard view
2. THE QA_Dashboard SHALL display aggregate metrics across all projects or show an empty state
3. WHERE the dashboard cannot display aggregate metrics or an empty state due to system issues, THE Dashboard SHALL fallback to empty state
4. THE Dashboard SHALL NOT automatically select or display a specific project after login
5. WHERE no project is currently selected, THE Dashboard SHALL allow displaying the project selection prompt alone without requiring metrics or empty state content

### Requirement 4: Display Project-Specific Navigation Items with Indentation

**User Story:** As a user, I want to see Requirements and other project-specific items indented below the selected project in the sidebar, so that I can visually understand which items belong to the selected project.

#### Acceptance Criteria

1. WHEN a project is selected, THE Sidebar SHALL display Child_Navigation_Items below the "Project" item
2. THE Child_Navigation_Items SHALL be visually indented to the right by 16-24 pixels
3. THE Child_Navigation_Items SHALL include: Requirements, Scenarios, Test Cases, Test Automation, Execution Workspace, Reports
4. THE Child_Navigation_Items SHALL use at least one visual indicator from: smaller font size OR reduced opacity
5. WHEN no project is selected, THE Sidebar SHALL NOT display Child_Navigation_Items
6. WHEN a user selects a different project, THE Sidebar SHALL update the Child_Navigation_Items to reflect the new selection

### Requirement 5: Maintain Sidebar Global Navigation Items

**User Story:** As a user, I want global navigation items (Knowledge Base, LangSmith, Settings) to remain at the standard indentation level, so that I can distinguish between global and project-specific functionality.

#### Acceptance Criteria

1. THE Sidebar SHALL display "QA Dashboard" without indentation
2. THE Sidebar SHALL display "Project" without indentation below "QA Dashboard"
3. THE Sidebar SHALL display "Knowledge Base (RAG)" without indentation
4. THE Sidebar SHALL display "LangSmith" without indentation
5. THE Sidebar SHALL display "Settings" without indentation at the bottom of the sidebar
6. THE Sidebar SHALL maintain consistent styling for global navigation items regardless of project selection

### Requirement 6: Project Selection State Management

**User Story:** As a developer, I want project selection state to be managed consistently across navigation changes, so that the application maintains the correct context.

#### Acceptance Criteria

1. WHEN a user selects a project from the Project_Page, THE Dashboard SHALL store the Selected_Project in application state
2. WHEN a user selects a project, THE Dashboard SHALL persist the selection to localStorage
3. WHEN a user refreshes the page, THE Dashboard SHALL restore the previously selected project from localStorage
4. WHEN a user navigates between views, THE Dashboard SHALL maintain the Selected_Project state globally across all navigation
5. WHEN a user explicitly deselects or exits a project, THE Dashboard SHALL clear the Selected_Project state and hide Child_Navigation_Items
6. THE Dashboard SHALL allow automatic clearing of project state in addition to explicit user actions

### Requirement 7: Visual Hierarchy Indicators

**User Story:** As a user, I want clear visual indicators of the navigation hierarchy, so that I can quickly understand the relationship between navigation items.

#### Acceptance Criteria

1. THE Indented_Navigation_Item SHALL display a connecting line or visual marker linking to its parent
2. THE Indented_Navigation_Item SHALL have a left margin of 16-24 pixels greater than standard navigation items
3. THE Indented_Navigation_Item SHALL have a font size 1-2 pixels smaller than standard navigation items
4. WHERE an Indented_Navigation_Item has 85% opacity, THE Dashboard SHALL require opacity to be combined with margin or font size differences
5. WHEN a user hovers over an Indented_Navigation_Item, THE Dashboard SHALL always apply the same hover effect as standard items regardless of potential styling conflicts

### Requirement 8: Project Page UI Design

**User Story:** As a user, I want the Project page to display projects in a clear, scannable format, so that I can quickly find and select the project I need.

#### Acceptance Criteria

1. THE Project_Page SHALL display projects in a card grid layout with 2-3 columns
2. THE Project_Page SHALL display for each project: name, description, line of business, and last accessed date
3. THE Project_Page SHALL highlight the currently selected project with a distinctive border or background color
4. WHEN a user clicks a project card, THE Dashboard SHALL set that project as the Selected_Project
5. WHEN a user clicks a project card, THE Dashboard SHALL navigate to the QA_Dashboard view for that project
6. THE Project_Page SHALL display a "+ Create New Project" card as the first item in the grid

### Requirement 9: Backward Compatibility and Migration

**User Story:** As a developer, I want existing functionality to continue working after the navigation restructure, so that users experience minimal disruption.

#### Acceptance Criteria

1. THE Dashboard SHALL continue to support all existing API endpoints without modification
2. THE Dashboard SHALL maintain existing keyboard shortcuts and accessibility features
3. THE Dashboard SHALL preserve existing permission and role-based access controls
4. THE Dashboard SHALL continue to display user profile widget and logout functionality
5. WHEN a user has a project selected in localStorage from the old design, THE Dashboard SHALL correctly load and select that project in the new navigation structure

### Requirement 10: Empty State Handling

**User Story:** As a user, I want clear guidance when no project is selected, so that I know what action to take next.

#### Acceptance Criteria

1. WHEN no project is selected, THE Dashboard SHALL display an empty state message in the QA_Dashboard view
2. THE Empty_State SHALL include a message: "No project selected. Please select a project to view dashboard metrics."
3. THE Empty_State SHALL include a prominent button: "Go to Projects"
4. WHEN a user clicks the "Go to Projects" button, THE Dashboard SHALL navigate to the Project_Page
5. WHEN no project is selected, THE Dashboard SHALL disable or hide Child_Navigation_Items in the sidebar
