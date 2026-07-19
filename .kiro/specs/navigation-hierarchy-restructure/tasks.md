zopen# Implementation Plan: Navigation Hierarchy Restructure

## Overview

This implementation plan restructures the dashboard navigation to create a clearer hierarchical relationship between Projects and their child items. The work is broken down into four main phases: top navigation simplification, sidebar restructure, project page implementation, and state management integration. Each task builds incrementally on previous work, with checkpoints to ensure stability.

## Tasks

- [ ] 1. Simplify Top Navigation Bar
  - Remove project selector dropdown and related controls from top navigation
  - Remove `#project-select`, `#project-select-search`, release, and cycle selector elements from `frontend/index.html`
  - Remove project selector CSS styles from `frontend/css/styles.css`
  - Remove project selector initialization and event handlers from `frontend/js/app.js`
  - Keep user controls and logout functionality intact
  - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [x] 2. Add Project Navigation Item to Sidebar
  - [x] 2.1 Add "Project" navigation item to sidebar in HTML
    - Insert new navigation item in `frontend/index.html` below "QA Dashboard"
    - Add appropriate icon and label markup
    - Set `data-view="project"` and `data-level="0"` attributes
    - _Requirements: 2.1, 2.2_
  
  - [x] 2.2 Implement navigation handler for Project page
    - Add view switching logic to show/hide project page view in `frontend/js/app.js`
    - Update `navigateTo()` method to handle 'project' view
    - Ensure active nav item styling updates correctly
    - _Requirements: 2.2_

- [ ] 3. Implement Hierarchical Navigation Structure
  - [x] 3.1 Restructure sidebar HTML with hierarchy levels
    - Mark global navigation items with `data-level="0"` in `frontend/index.html`
    - Mark project-specific items (Requirements, Scenarios, Test Cases, Test Automation, Execution Workspace, Reports) with `data-level="1"`
    - Add `nav-item-indented` class to all level 1 items
    - Set initial `display: none` on all indented items
    - _Requirements: 4.1, 4.2, 4.3, 5.1, 5.2, 5.3, 5.4, 5.5_
  
  - [ ] 3.2 Create CSS styles for hierarchical indentation
    - Add `.nav-item-indented` styles to `frontend/css/styles.css`
    - Implement 20px left margin indentation
    - Add font-size reduction (0.9rem) and opacity (0.85)
    - Create connecting line indicator using `::before` pseudo-element
    - Ensure hover and active states match standard nav items
    - _Requirements: 4.2, 4.4, 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [ ] 3.3 Implement sidebar visibility control logic
    - Create `updateSidebarHierarchy(hasProject)` method in `frontend/js/app.js`
    - Toggle visibility of all `data-level="1"` nav items based on project selection state
    - Call method when project state changes (select/deselect)
    - _Requirements: 4.1, 4.5, 4.6, 5.6_

- [ ] 4. Checkpoint - Verify Navigation Structure
  - Ensure sidebar renders correctly with proper indentation
  - Verify global nav items always visible
  - Verify project-specific items hidden by default
  - Test manual project state changes update sidebar correctly
  - Ask the user if questions arise

- [ ] 5. Create Project Page View
  - [ ] 5.1 Add Project Page HTML structure
    - Create new view panel `<div id="project-page-view">` in `frontend/index.html`
    - Add page header with title "Projects"
    - Add search input field with id `project-search`
    - Add project grid container with id `project-grid-container`
    - _Requirements: 2.3, 2.4, 8.1_
  
  - [ ] 5.2 Implement Project Page CSS styling
    - Create `.project-grid` CSS Grid layout (auto-fill, minmax(320px, 1fr)) in `frontend/css/styles.css`
    - Style `.project-card` with background, border, padding, hover effects
    - Style `.project-card-new` for "Create New Project" card with dashed border
    - Add `.project-card.selected` styling with accent border and background
    - Style `.project-description`, `.project-meta`, `.lob-tag`, `.last-accessed`
    - _Requirements: 8.1, 8.2, 8.3_
  
  - [ ] 5.3 Implement Project Page rendering logic
    - Create `renderProjectPage()` method in `frontend/js/app.js`
    - Fetch projects from API and build project card HTML
    - Render "Create New Project" card as first item
    - Display project name, description, line of business, last accessed date
    - Highlight currently selected project with `.selected` class
    - _Requirements: 2.3, 2.5, 8.2, 8.3_
  
  - [ ] 5.4 Implement project card click handler
    - Create `selectProjectFromCard(projectId)` method in `frontend/js/app.js`
    - Call `selectProject(projectId)` to update state
    - Navigate to dashboard view after selection
    - Update sidebar to show indented items
    - _Requirements: 8.4, 8.5_
  
  - [ ] 5.5 Implement project search functionality
    - Create `setupProjectSearch()` method in `frontend/js/app.js`
    - Add input event listener to `#project-search` field
    - Filter project cards based on search query (name, description, LOB)
    - Show/hide cards dynamically as user types
    - _Requirements: 2.4_

- [ ] 6. Implement Empty State Component
  - [ ] 6.1 Add Empty State HTML to Dashboard
    - Add `<div id="dashboard-empty-state">` inside `#dashboard-view` in `frontend/index.html`
    - Include icon SVG, heading "No project selected", message text
    - Add "Go to Projects" button with onclick handler
    - Set initial `display: none`
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [ ] 6.2 Create Empty State CSS styling
    - Add `.empty-state` styles to `frontend/css/styles.css`
    - Center content with flexbox, add padding and spacing
    - Style `.empty-state-icon` with appropriate size and color
    - Style empty state heading and message text
    - _Requirements: 10.1_
  
  - [ ] 6.3 Implement empty state display logic
    - Create `updateDashboardEmptyState()` method in `frontend/js/app.js`
    - Show empty state when `currentProject` is null
    - Hide empty state and show dashboard content when project selected
    - Call method after project state changes and on page load
    - _Requirements: 10.1, 10.4, 10.5_

- [ ] 7. Checkpoint - Verify Project Selection Flow
  - Test navigating to Project page
  - Verify project cards render correctly
  - Test selecting project and navigating to dashboard
  - Verify empty state shows when no project selected
  - Verify indented nav items appear after project selection
  - Ask the user if questions arise

- [ ] 8. Implement Project State Management
  - [ ] 8.1 Create Project State Manager module
    - Create `ProjectStateManager` class or object in `frontend/js/app.js`
    - Implement `getCurrentProject()` method
    - Implement `setCurrentProject(projectId)` method with localStorage persistence
    - Implement `clearProjectSelection()` method
    - _Requirements: 6.1, 6.2, 6.5_
  
  - [ ] 8.2 Integrate state management with project selection
    - Update `selectProject()` method to use `setCurrentProject()`
    - Store selected project ID in `localStorage.active_project_id`
    - Update `currentProject` in application state
    - Emit custom event `project:selected` with project details
    - _Requirements: 6.1, 6.2, 6.4_
  
  - [ ] 8.3 Implement localStorage persistence on page refresh
    - Create `restoreProjectFromStorage()` method in `frontend/js/app.js`
    - Call during application initialization
    - Check for `active_project_id` in localStorage
    - Fetch project details from API if ID exists
    - Update UI (sidebar, empty state) based on restored project
    - _Requirements: 6.3, 9.5_
  
  - [ ] 8.4 Handle localStorage errors and invalid project IDs
    - Wrap localStorage access in try-catch blocks
    - Handle missing or deleted projects (clear localStorage if not found)
    - Show non-intrusive notification for "Previously selected project not found"
    - Fall back to session-only state if localStorage unavailable
    - Log warnings to console for debugging
    - _Requirements: 6.3, 9.5_

- [ ] 9. Update Login Flow
  - [ ] 9.1 Modify login success handler
    - Update login redirect logic in `frontend/js/app.js` to navigate to `dashboard` view
    - Remove any auto-project-selection logic from login flow
    - Ensure dashboard loads without preselecting a project
    - _Requirements: 3.1, 3.4_
  
  - [ ] 9.2 Initialize dashboard with empty state on login
    - Show empty state in dashboard if no project in localStorage
    - Display aggregate metrics or empty state in QA Dashboard
    - Ensure "Go to Projects" button navigates correctly
    - _Requirements: 3.2, 3.3, 3.5_

- [ ] 10. Implement Navigation Guards and Error Handling
  - [ ] 10.1 Add navigation guards for project-specific views
    - Create `requiresProject()` guard function in `frontend/js/app.js`
    - Intercept navigation to Requirements, Scenarios, Test Cases, etc.
    - Show modal/toast "Please select a project first" if no project selected
    - Redirect to Project page, then back to requested view after selection
    - _Requirements: 4.5_
  
  - [ ] 10.2 Handle view panel not found errors
    - Add error handling in `navigateTo()` method
    - Log error with view ID if panel doesn't exist
    - Fall back to dashboard view
    - Show error notification to user
    - _Requirements: 6.4_
  
  - [ ] 10.3 Implement state consistency validation
    - Add defensive checks to always derive UI from `currentProject` state
    - Force sidebar refresh if state and UI out of sync
    - Log inconsistency warnings to console
    - _Requirements: 6.4_

- [ ] 11. Preserve Backward Compatibility
  - [ ] 11.1 Verify existing API endpoints unchanged
    - Test project fetch, create, update, delete endpoints
    - Ensure Requirements, Scenarios, Test Cases APIs unaffected
    - Verify no breaking changes to backend contracts
    - _Requirements: 9.1_
  
  - [ ] 11.2 Maintain keyboard shortcuts and accessibility
    - Test keyboard navigation through all nav items
    - Verify focus indicators visible on interactive elements
    - Test screen reader announcements for hierarchy
    - Ensure ARIA attributes present for navigation structure
    - _Requirements: 9.2_
  
  - [ ] 11.3 Preserve user controls and permissions
    - Verify user profile widget displays correctly
    - Test logout functionality unchanged
    - Verify role-based access controls still enforced
    - _Requirements: 9.3, 9.4_

- [ ] 12. Final Integration and Testing
  - [ ]* 12.1 Write unit tests for state management
    - Test `setCurrentProject()` updates memory and localStorage
    - Test `clearProjectSelection()` removes localStorage key
    - Test `restoreProjectFromStorage()` handles invalid data
    - Test event emission on project state changes
  
  - [ ]* 12.2 Write integration tests for user flows
    - Test login redirects to dashboard with empty state
    - Test project selection updates sidebar and shows indented items
    - Test page refresh restores project selection
    - Test navigation between all views with project selected
  
  - [ ]* 12.3 Perform visual regression testing
    - Capture baseline screenshots of new UI components
    - Verify sidebar indentation renders correctly
    - Verify project page grid layout (2-3 columns)
    - Verify empty state appearance
    - Verify selected project highlight styling

- [ ] 13. Final Checkpoint - Complete System Verification
  - Test complete login-to-project-selection-to-navigation flow
  - Verify all navigation items work correctly with project selected
  - Verify empty state, project page, and sidebar all function together
  - Test localStorage persistence across browser refresh
  - Test all error scenarios and fallback behaviors
  - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional testing tasks that can be skipped for faster MVP delivery
- Each implementation task references specific requirements for traceability
- Checkpoints ensure incremental validation and early detection of issues
- The feature uses vanilla JavaScript with no framework dependencies
- LocalStorage is used for persistence; graceful degradation if unavailable
- All existing functionality (API endpoints, keyboard shortcuts, permissions) must remain unchanged
- Visual hierarchy uses indentation (20px), font size reduction, and connecting lines
- Empty state provides clear guidance to users when no project is selected
- State management follows single source of truth principle (always derive UI from `currentProject`)

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1", "2.1"] },
    { "id": 1, "tasks": ["2.2", "3.1"] },
    { "id": 2, "tasks": ["3.2", "3.3", "5.1"] },
    { "id": 3, "tasks": ["5.2", "6.1"] },
    { "id": 4, "tasks": ["5.3", "6.2"] },
    { "id": 5, "tasks": ["5.4", "5.5", "6.3", "8.1"] },
    { "id": 6, "tasks": ["8.2", "8.3"] },
    { "id": 7, "tasks": ["8.4", "9.1"] },
    { "id": 8, "tasks": ["9.2", "10.1"] },
    { "id": 9, "tasks": ["10.2", "10.3", "11.1"] },
    { "id": 10, "tasks": ["11.2", "11.3"] },
    { "id": 11, "tasks": ["12.1", "12.2", "12.3"] }
  ]
}
```
