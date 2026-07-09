// Helper to escape HTML and prevent XSS
export function escapeHTML(str) {
  if (!str) return '';
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}

export function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export const Components = {
  Spinner(text = "Processing...") {
    return `
      <div class="loading-overlay">
        <div class="spinner"></div>
        <div class="loading-text">${escapeHTML(text)}</div>
      </div>
    `;
  },

  EmptyState(title, description, actionHtml = "") {
    return `
      <div class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 48px; height: 48px; color: var(--text-muted);">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 13h6m-3-3v6m-9 1V4a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
        </svg>
        <h3>${escapeHTML(title)}</h3>
        <p>${escapeHTML(description)}</p>
        ${actionHtml}
      </div>
    `;
  },

  MetricCard(label, value, footerText = "") {
    return `
      <div class="metric-card">
        <div class="metric-label">${escapeHTML(label)}</div>
        <div class="metric-value">${escapeHTML(String(value))}</div>
        ${footerText ? `<div class="metric-footer">${escapeHTML(footerText)}</div>` : ''}
      </div>
    `;
  },

  RecentActivityItem(activity) {
    return `
      <div class="activity-item">
        <div class="activity-dot"></div>
        <div class="activity-content">
          <div style="font-weight: 500;">${escapeHTML(activity.message)}</div>
          <div class="activity-time">${escapeHTML(activity.time)}</div>
        </div>
      </div>
    `;
  },

  // Requirements List Component
  RequirementsTable(requirements, handlers) {
    if (!requirements || requirements.length === 0) {
      return this.EmptyState("No Requirements", "Get started by importing requirements to this project.");
    }

    window._requirementActions = handlers;

    const rows = requirements.map(req => {
      const date = new Date(req.uploaded_at).toLocaleDateString();
      return `
        <tr>
          <td style="font-weight: 600; cursor: pointer;" onclick="window._requirementActions.onSelect('${req.id}')">${escapeHTML(req.title)}</td>
          <td style="color: var(--text-secondary); max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHTML(req.description)}</td>
          <td><span class="badge badge-${req.priority.toLowerCase()}">${escapeHTML(req.priority)}</span></td>
          <td><span style="font-family: monospace; font-size: 0.8rem; background-color: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px;">${escapeHTML(req.business_domain)}</span></td>
          <td style="color: var(--text-muted);">${escapeHTML(date)}</td>
          <td style="text-align: right;">
            <div class="cell-actions">
              <button class="btn-icon btn-icon-success" title="Draft Scenarios" onclick="window._requirementActions.onSelect('${req.id}')">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    return `
      <div class="table-container">
        <table class="custom-table">
          <thead>
            <tr>
              <th>Requirement Title</th>
              <th>Description</th>
              <th>Priority</th>
              <th>Business Domain</th>
              <th>Created Date</th>
              <th style="text-align: right; width: 60px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  },

  // Scenarios component with comments / notes list
  ScenariosTable(scenarios, handlers, notesMap = {}) {
    if (!scenarios || scenarios.length === 0) {
      return this.EmptyState("No Scenarios", "Select a requirement and generate scenarios to begin.");
    }

    window._scenarioActions = handlers;

    const rows = scenarios.map(sc => {
      const statusBadge = sc.approved 
        ? `<span class="badge badge-approved">Approved</span>`
        : `<span class="badge badge-pending">Review Pending</span>`;

      // Render notes for scenario
      const notes = notesMap[sc.id] || [];
      const notesHtml = notes.map(n => `
        <div style="font-size: 0.75rem; background-color: var(--bg-primary); padding: 4px 8px; border-radius: 4px; margin-top: 4px; border-left: 2px solid var(--accent-primary); color: var(--text-secondary);">
          💬 <strong>Note:</strong> ${escapeHTML(n)}
        </div>
      `).join('');

      return `
        <tr>
          <td><input type="checkbox" class="scenario-checkbox" data-id="${sc.id}" /></td>
          <td style="font-weight: 600; min-width: 150px;">
            <div class="scenario-name-text" id="name-txt-${sc.id}">${escapeHTML(sc.scenario_name)}</div>
            <input type="text" class="form-control" id="name-in-${sc.id}" value="${escapeHTML(sc.scenario_name)}" style="display: none; padding: 4px 8px; font-size: 0.85rem;" />
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 6px; font-weight: 400;">
              <div>Reviewer: <strong style="color: var(--text-secondary);">${sc.approved ? "Lead QA Engineer" : "AI ScenarioAgent"}</strong></div>
              <div style="margin-top: 2px;">Time: <span>${new Date(sc.generated_at).toLocaleString()}</span></div>
            </div>
          </td>
          <td style="color: var(--text-secondary); min-width: 250px;">
            <div class="scenario-desc-text" id="desc-txt-${sc.id}">${escapeHTML(sc.description)}</div>
            <textarea class="form-control" id="desc-in-${sc.id}" style="display: none; padding: 4px 8px; font-size: 0.85rem; width: 100%; min-height: 50px;">${escapeHTML(sc.description)}</textarea>
            
            <!-- Comment Section -->
            <div style="margin-top: 8px;">
              ${notesHtml}
              <div style="margin-top: 6px; display: flex; gap: 8px; align-items: center;">
                <input type="text" class="form-control" id="note-add-in-${sc.id}" placeholder="Attach a review note..." style="padding: 4px 8px; font-size: 0.75rem; flex-grow: 1;" />
                <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="if(document.getElementById('note-add-in-${sc.id}').value.trim()) { window._scenarioActions.onAddNote('${sc.id}', document.getElementById('note-add-in-${sc.id}').value); document.getElementById('note-add-in-${sc.id}').value=''; }">Add Note</button>
              </div>
            </div>
          </td>
          <td>
            <div class="scenario-priority-text" id="prio-txt-${sc.id}"><span class="badge badge-${sc.priority.toLowerCase()}">${escapeHTML(sc.priority)}</span></div>
            <select class="form-control" id="prio-in-${sc.id}" style="display: none; padding: 4px 8px; font-size: 0.85rem;">
              <option value="low" ${sc.priority === 'low' ? 'selected' : ''}>Low</option>
              <option value="medium" ${sc.priority === 'medium' ? 'selected' : ''}>Medium</option>
              <option value="high" ${sc.priority === 'high' ? 'selected' : ''}>High</option>
            </select>
          </td>
          <td>${statusBadge}</td>
          <td style="text-align: right;">
            <div class="cell-actions" id="actions-view-${sc.id}">
              <button class="btn-icon btn-icon-success" title="Approve" onclick="window._scenarioActions.onApprove('${sc.id}')">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>
              </button>
              <button class="btn-icon btn-icon-danger" title="Reject / Disapprove" onclick="window._scenarioActions.onReject('${sc.id}')">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
              <button class="btn-icon" title="Edit" onclick="document.getElementById('name-txt-${sc.id}').style.display='none'; document.getElementById('name-in-${sc.id}').style.display='block'; document.getElementById('desc-txt-${sc.id}').style.display='none'; document.getElementById('desc-in-${sc.id}').style.display='block'; document.getElementById('prio-txt-${sc.id}').style.display='none'; document.getElementById('prio-in-${sc.id}').style.display='block'; document.getElementById('actions-view-${sc.id}').style.display='none'; document.getElementById('actions-edit-${sc.id}').style.display='flex';">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
              </button>
              <button class="btn-icon" title="Duplicate" onclick="window._scenarioActions.onDuplicate('${sc.id}')">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" /></svg>
              </button>
              <button class="btn-icon btn-icon-danger" title="Delete" onclick="window._scenarioActions.onDelete('${sc.id}')">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              </button>
            </div>
            
            <div class="cell-actions" id="actions-edit-${sc.id}" style="display: none;">
              <button class="btn btn-primary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="window._scenarioActions.onSave('${sc.id}', document.getElementById('name-in-${sc.id}').value, document.getElementById('desc-in-${sc.id}').value, document.getElementById('prio-in-${sc.id}').value)">Save</button>
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="document.getElementById('name-txt-${sc.id}').style.display='block'; document.getElementById('name-in-${sc.id}').style.display='none'; document.getElementById('desc-txt-${sc.id}').style.display='block'; document.getElementById('desc-in-${sc.id}').style.display='none'; document.getElementById('prio-txt-${sc.id}').style.display='block'; document.getElementById('prio-in-${sc.id}').style.display='none'; document.getElementById('actions-view-${sc.id}').style.display='flex'; document.getElementById('actions-edit-${sc.id}').style.display='none';">Cancel</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    return `
      <div class="table-container">
        <table class="custom-table">
          <thead>
            <tr>
              <th style="width: 40px;"><input type="checkbox" id="bulk-sc-select-all" onclick="const checked = this.checked; document.querySelectorAll('.scenario-checkbox').forEach(cb => cb.checked = checked);" /></th>
              <th>Scenario Name</th>
              <th>Description & Review Comments</th>
              <th>Priority</th>
              <th>Status</th>
              <th style="text-align: right; width: 180px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  },

  // Test Cases component with comments / notes
  TestCasesTable(testCases, handlers, notesMap = {}) {
    if (!testCases || testCases.length === 0) {
      return this.EmptyState("No Test Cases", "Generate test cases from approved scenarios to begin.");
    }

    window._testCaseActions = handlers;

    const rows = testCases.map(tc => {
      let badgeClass = "badge-pending";
      if (tc.evaluation_status === 'approved') badgeClass = "badge-approved";
      if (tc.evaluation_status === 'rejected') badgeClass = "badge-rejected";
      if (tc.evaluation_status === 'needs_review') badgeClass = "badge-review";

      let runBadgeClass = "badge-pending";
      if (tc.status === 'passed') runBadgeClass = "badge-approved";
      if (tc.status === 'failed') runBadgeClass = "badge-rejected";
      if (tc.status === 'blocked') runBadgeClass = "badge-review";

      const confidencePct = Math.round(tc.confidence * 100);
      const hasScript = !!tc.playwright_script;

      // Render notes for testcase
      const notes = notesMap[tc.id] || [];
      const notesHtml = notes.map(n => `
        <div style="font-size: 0.75rem; background-color: var(--bg-primary); padding: 4px 8px; border-radius: 4px; margin-top: 4px; border-left: 2px solid var(--accent-primary); color: var(--text-secondary);">
          💬 <strong>Note:</strong> ${escapeHTML(n)}
        </div>
      `).join('');
      
      return `
        <tr id="tc-row-${tc.id}">
          <td><input type="checkbox" class="tc-checkbox" data-id="${tc.id}" /></td>
          <td style="font-weight: 600; min-width: 150px;">
            <div class="tc-title-text" id="tc-title-txt-${tc.id}">${escapeHTML(tc.title)}</div>
            <input type="text" class="form-control" id="tc-title-in-${tc.id}" value="${escapeHTML(tc.title)}" style="display: none; padding: 4px 8px; font-size: 0.85rem;" />
          </td>
          <td style="color: var(--text-secondary); min-width: 250px;">
            <div class="tc-steps-text" id="tc-steps-txt-${tc.id}">
              ${tc.steps.map((s, idx) => `<div>${idx + 1}. ${escapeHTML(s)}</div>`).join('')}
            </div>
            <textarea class="form-control" id="tc-steps-in-${tc.id}" style="display: none; padding: 4px 8px; font-size: 0.85rem; width: 100%; min-height: 80px;">${escapeHTML(tc.steps.join('\n'))}</textarea>
            
            <!-- Comment Section -->
            <div style="margin-top: 10px;">
              ${notesHtml}
              <div style="margin-top: 6px; display: flex; gap: 8px; align-items: center;">
                <input type="text" class="form-control" id="tc-note-add-in-${tc.id}" placeholder="Attach note..." style="padding: 4px 8px; font-size: 0.75rem; flex-grow: 1;" />
                <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="if(document.getElementById('tc-note-add-in-${tc.id}').value.trim()) { window._testCaseActions.onAddNote('${tc.id}', document.getElementById('tc-note-add-in-${tc.id}').value); document.getElementById('tc-note-add-in-${tc.id}').value=''; }">Add Note</button>
              </div>
            </div>
          </td>
          <td style="min-width: 180px;">
            <div class="tc-expected-text" id="tc-expected-txt-${tc.id}">${escapeHTML(tc.expected_result)}</div>
            <textarea class="form-control" id="tc-expected-in-${tc.id}" style="display: none; padding: 4px 8px; font-size: 0.85rem; width: 100%; min-height: 50px;">${escapeHTML(tc.expected_result)}</textarea>
          </td>
          <td>
            <div class="tc-status-text" id="tc-eval-status-txt-${tc.id}"><span class="badge ${badgeClass}">${escapeHTML(tc.evaluation_status)}</span></div>
            <select class="form-control" id="tc-eval-status-in-${tc.id}" style="display: none; padding: 4px 8px; font-size: 0.85rem;">
              <option value="pending" ${tc.evaluation_status === 'pending' ? 'selected' : ''}>Pending</option>
              <option value="approved" ${tc.evaluation_status === 'approved' ? 'selected' : ''}>Approved</option>
              <option value="needs_review" ${tc.evaluation_status === 'needs_review' ? 'selected' : ''}>Needs Review</option>
              <option value="rejected" ${tc.evaluation_status === 'rejected' ? 'selected' : ''}>Rejected</option>
            </select>
          </td>
          <td>
            <div><span class="badge ${runBadgeClass}">${escapeHTML(tc.status || 'pending')}</span></div>
          </td>
          <td>
            <div class="tc-conf-text" id="tc-conf-txt-${tc.id}">${confidencePct}%</div>
            <input type="number" step="0.01" min="0" max="1" class="form-control" id="tc-conf-in-${tc.id}" value="${tc.confidence}" style="display: none; padding: 4px 8px; font-size: 0.85rem; width: 70px;" />
          </td>
          <td style="min-width: 140px;">
            ${tc.evaluation_status === 'approved' ? `
              ${hasScript ? `
                <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="window._testCaseActions.onViewScript('${tc.id}')">Edit Script</button>
              ` : `
                <button class="btn btn-primary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="window._testCaseActions.onGenerateScript('${tc.id}', this)">Generate Script</button>
              `}
              <a href="javascript:void(0)" onclick="window._testCaseActions.onViewScript('${tc.id}')" style="display: block; font-size: 0.7rem; color: var(--accent-primary); margin-top: 4px; font-weight: 600; text-decoration: none;">→ Open in Playwright Workspace</a>
            ` : `
              <button class="btn btn-primary" style="padding: 4px 8px; font-size: 0.75rem;" disabled>Generate Script</button>
              <div style="font-size: 0.65rem; color: var(--text-muted); margin-top: 2px;">Approve test case first</div>
            `}
          </td>
          <td style="text-align: right;">
            <div class="cell-actions" id="tc-actions-view-${tc.id}">
              <button class="btn-icon btn-icon-success" title="Approve" onclick="window._testCaseActions.onApprove('${tc.id}')">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7" /></svg>
              </button>
              <button class="btn-icon btn-icon-danger" title="Reject" onclick="window._testCaseActions.onReject('${tc.id}')">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
              <button class="btn-icon" title="Edit" onclick="document.getElementById('tc-title-txt-${tc.id}').style.display='none'; document.getElementById('tc-title-in-${tc.id}').style.display='block'; document.getElementById('tc-steps-txt-${tc.id}').style.display='none'; document.getElementById('tc-steps-in-${tc.id}').style.display='block'; document.getElementById('tc-expected-txt-${tc.id}').style.display='none'; document.getElementById('tc-expected-in-${tc.id}').style.display='block'; document.getElementById('tc-eval-status-txt-${tc.id}').style.display='none'; document.getElementById('tc-eval-status-in-${tc.id}').style.display='block'; document.getElementById('tc-conf-txt-${tc.id}').style.display='none'; document.getElementById('tc-conf-in-${tc.id}').style.display='block'; document.getElementById('tc-actions-view-${tc.id}').style.display='none'; document.getElementById('tc-actions-edit-${tc.id}').style.display='flex';">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
              </button>
              <button class="btn-icon btn-icon-danger" title="Delete" onclick="window._testCaseActions.onDelete('${tc.id}')">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
              </button>
            </div>
            
            <div class="cell-actions" id="tc-actions-edit-${tc.id}" style="display: none;">
              <button class="btn btn-primary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="window._testCaseActions.onSave('${tc.id}', { title: document.getElementById('tc-title-in-${tc.id}').value, steps: document.getElementById('tc-steps-in-${tc.id}').value.split('\\n'), expected_result: document.getElementById('tc-expected-in-${tc.id}').value, evaluation_status: document.getElementById('tc-eval-status-in-${tc.id}').value, confidence: parseFloat(document.getElementById('tc-conf-in-${tc.id}').value) })">Save</button>
              <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="document.getElementById('tc-title-txt-${tc.id}').style.display='block'; document.getElementById('tc-title-in-${tc.id}').style.display='none'; document.getElementById('tc-steps-txt-${tc.id}').style.display='block'; document.getElementById('tc-steps-in-${tc.id}').style.display='none'; document.getElementById('tc-expected-txt-${tc.id}').style.display='block'; document.getElementById('tc-expected-in-${tc.id}').style.display='none'; document.getElementById('tc-eval-status-txt-${tc.id}').style.display='block'; document.getElementById('tc-eval-status-in-${tc.id}').style.display='none'; document.getElementById('tc-conf-txt-${tc.id}').style.display='block'; document.getElementById('tc-conf-in-${tc.id}').style.display='none'; document.getElementById('tc-actions-view-${tc.id}').style.display='flex'; document.getElementById('tc-actions-edit-${tc.id}').style.display='none';">Cancel</button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    return `
      <div class="table-container">
        <table class="custom-table">
          <thead>
            <tr>
              <th style="width: 40px;"><input type="checkbox" id="bulk-tc-select-all" onclick="const checked = this.checked; document.querySelectorAll('.tc-checkbox').forEach(cb => cb.checked = checked);" /></th>
              <th>Test Case Title</th>
              <th>Steps & Comments</th>
              <th>Expected Result</th>
              <th>Evaluation Status</th>
              <th>Run Status</th>
              <th>Confidence</th>
              <th>Script</th>
              <th style="text-align: right; width: 140px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  },

  // Documents Table component inside Knowledge Base
  DocumentsTable(documents, onDelete) {
    if (!documents || documents.length === 0) {
      return this.EmptyState("No Knowledge Documents", "Knowledge Base is currently empty. Upload files (PDF, DOCX, XLSX, CSV, TXT) to establish RAG database.");
    }

    window._deleteDocument = onDelete;

    const rows = documents.map(doc => {
      const date = new Date(doc.uploaded_at).toLocaleDateString();
      let statusBadge = `<span class="badge badge-review">${escapeHTML(doc.embedding_status)}</span>`;
      if (doc.embedding_status === 'completed') {
        statusBadge = `<span class="badge badge-approved">Indexed</span>`;
      } else if (doc.embedding_status === 'failed') {
        statusBadge = `<span class="badge badge-rejected">Failed</span>`;
      }

      return `
        <tr>
          <td style="font-weight: 600;">${escapeHTML(doc.original_filename)}</td>
          <td><span style="font-family: monospace; font-size: 0.8rem; background-color: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px;">${escapeHTML(doc.mime_type)}</span></td>
          <td>${formatBytes(doc.size)}</td>
          <td>${statusBadge}</td>
          <td>${escapeHTML(date)}</td>
          <td style="text-align: right;">
            <button class="btn-icon btn-icon-danger" title="Delete File" onclick="window._deleteDocument('${doc.id}')">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 16px; height: 16px;"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
            </button>
          </td>
        </tr>
      `;
    }).join('');

    return `
      <div class="table-container">
        <table class="custom-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Mime Type</th>
              <th>Size</th>
              <th>Embedding Status</th>
              <th>Uploaded Date</th>
              <th style="text-align: right; width: 60px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  },

  // Executions Table Component
  ExecutionsTable(executions) {
    if (!executions || executions.length === 0) {
      return this.EmptyState("No Execution Records", "Execution history is empty. Go to Test Cases, view script, and trigger runs to log executions.");
    }

    const rows = executions.map(ex => {
      const date = new Date(ex.executed_at).toLocaleString();
      let statusBadge = `<span class="badge badge-approved">Passed</span>`;
      if (ex.status === 'failed') statusBadge = `<span class="badge badge-rejected">Failed</span>`;
      if (ex.status === 'skipped') statusBadge = `<span class="badge badge-pending">Skipped</span>`;
      if (ex.status === 'error') statusBadge = `<span class="badge badge-review">Error</span>`;

      return `
        <tr>
          <td style="font-family: monospace; font-size: 0.8rem;">${escapeHTML(String(ex.test_case_id).substring(0, 8))}...</td>
          <td>${statusBadge}</td>
          <td>${escapeHTML(String(ex.duration_seconds))}s</td>
          <td style="color: var(--text-secondary); max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            ${escapeHTML(ex.error_message || 'Success')}
          </td>
          <td>
            ${ex.screenshot_path ? `
              <a href="/api/v1/projects/${ex.project_id || 'default'}/executions/${ex.id}/screenshot?path=${encodeURIComponent(ex.screenshot_path)}" target="_blank" style="color: var(--accent-primary); text-decoration: none; font-weight: 500;">Screenshot</a>
            ` : `<span style="color: var(--text-muted);">No Screenshot</span>`}
          </td>
          <td>
            ${ex.video_path ? `
              <a href="/api/v1/projects/${ex.project_id || 'default'}/executions/${ex.id}/video?path=${encodeURIComponent(ex.video_path)}" target="_blank" style="color: var(--accent-primary); text-decoration: none; font-weight: 500;">Video</a>
            ` : `<span style="color: var(--text-muted);">No Video</span>`}
          </td>
          <td style="color: var(--text-muted);">${escapeHTML(date)}</td>
          <td style="text-align: right;">
            <a href="#/execution/${ex.id}" class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;">View Workspace</a>
          </td>
        </tr>
      `;
    }).join('');

    return `
      <div class="table-container">
        <table class="custom-table">
          <thead>
            <tr>
              <th>TestCase ID</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Error details</th>
              <th>Screenshot</th>
              <th>Video</th>
              <th>Ran Date</th>
              <th style="text-align: right;">Workspace</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  },

  // LangSmith Traces Panel Component
  LangSmithTraces(traceData) {
    if (!traceData || !traceData.traces || traceData.traces.length === 0) {
      return this.EmptyState("No LangSmith Logs", "Generate scenarios or test cases using the LLM to populate tracking traces.");
    }

    const rows = traceData.traces.map(t => {
      return `
        <tr style="font-family: monospace; font-size: 0.8rem;">
          <td style="font-family: var(--font-family); font-weight: 600; font-size: 0.85rem;">${escapeHTML(t.agent)}</td>
          <td>${t.calls} calls</td>
          <td>${t.latency_sec}s</td>
          <td>${t.tokens}</td>
          <td style="color: var(--color-success); font-weight: 600;">$${t.cost}</td>
        </tr>
      `;
    }).join('');

    return `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px;">
        <div class="metric-card">
          <div class="metric-label">Model Target</div>
          <div class="metric-value" style="font-size: 1.25rem;">${escapeHTML(traceData.provider)} / ${escapeHTML(traceData.model)}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Estimated Token Cost</div>
          <div class="metric-value" style="color: var(--color-success);">$${traceData.estimated_cost_usd}</div>
          <div class="metric-footer">Total Tokens consumed: ${traceData.total_tokens}</div>
        </div>
      </div>
      
      <div class="table-container">
        <table class="custom-table">
          <thead>
            <tr>
              <th>Agent Component</th>
              <th>Calls Tracked</th>
              <th>Accumulated Latency</th>
              <th>Token Count</th>
              <th>Trace Cost (USD)</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  },

  // Playwright Workspace Table
  PlaywrightApprovedTable(testCases, handlers) {
    if (!testCases || testCases.length === 0) {
      return this.EmptyState("No Approved Test Cases", "No test cases have been approved for this requirement yet. Go to Test Case Approval first.");
    }

    window._playwrightActions = handlers;

    const rows = testCases.map(tc => {
      const hasScript = !!tc.playwright_script;
      const confidencePct = Math.round(tc.confidence * 100);

      return `
        <tr id="pw-row-${tc.id}">
          <td style="font-weight: 600; min-width: 150px;">${escapeHTML(tc.title)}</td>
          <td style="color: var(--text-secondary); min-width: 250px;">
            ${tc.steps.map((s, idx) => `<div>${idx + 1}. ${escapeHTML(s)}</div>`).join('')}
          </td>
          <td style="min-width: 180px;">${escapeHTML(tc.expected_result)}</td>
          <td>${confidencePct}%</td>
          <td>
            ${hasScript ? `
              <span class="badge badge-approved" style="font-weight: 500;">✓ Script Ready</span>
            ` : `
              <span class="badge badge-review" style="font-weight: 500;">No Script</span>
            `}
          </td>
          <td style="text-align: right; min-width: 240px;">
            <div class="cell-actions" style="justify-content: flex-end; gap: 8px;">
              ${hasScript ? `
                <button class="btn btn-secondary" style="padding: 6px 12px; font-size: 0.75rem;" onclick="window._playwrightActions.onViewScript('${tc.id}')">Open Monaco Editor</button>
                <button class="btn btn-primary" style="padding: 6px 12px; font-size: 0.75rem; background-color: var(--color-success); border-color: var(--color-success);" onclick="window._playwrightActions.onRunTest('${tc.id}', this)">Run Test</button>
              ` : `
                <button class="btn btn-primary" style="padding: 6px 12px; font-size: 0.75rem;" onclick="window._playwrightActions.onGenerateScript('${tc.id}', this)">Generate Script</button>
              `}
            </div>
          </td>
        </tr>
      `;
    }).join('');

    return `
      <div class="table-container">
        <table class="custom-table">
          <thead>
            <tr>
              <th>Approved Test Case</th>
              <th>Test Steps</th>
              <th>Expected Result</th>
              <th>Confidence</th>
              <th>Script Status</th>
              <th style="text-align: right; width: 240px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${rows}
          </tbody>
        </table>
      </div>
    `;
  },

  // Card list for VS-Code IDE style left-pane
  PlaywrightApprovedCardList(testCases, activeTestCaseId, handlers) {
    window._playwrightWorkspaceHandlers = handlers;

    if (!testCases || testCases.length === 0) {
      return `
        <div style="text-align: center; padding: 30px; color: var(--text-muted); font-size: 0.85rem;">
          No approved test cases found.
        </div>
      `;
    }

    return testCases.map(tc => {
      const isSelected = tc.id === activeTestCaseId;
      const hasScript = !!tc.playwright_script;
      return `
        <div class="testcase-card ${isSelected ? 'selected' : ''}" 
             style="background-color: ${isSelected ? 'var(--bg-tertiary)' : 'var(--bg-primary)'};
                    border: 1px solid ${isSelected ? 'var(--accent-primary)' : 'var(--border-color)'};
                    border-radius: var(--border-radius-md);
                    padding: 12px;
                    cursor: pointer;
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                    transition: all 0.2s;"
             onclick="window._playwrightWorkspaceHandlers.onSelectTestCase('${tc.id}')">
          <div style="font-weight: 600; font-size: 0.85rem; display: flex; justify-content: space-between; align-items: start; gap: 8px;">
            <span>${escapeHTML(tc.title)}</span>
            <span class="badge ${hasScript ? 'badge-approved' : 'badge-review'}" style="font-size: 0.65rem; flex-shrink: 0; padding: 2px 6px;">
              ${hasScript ? '✓ Script' : 'No Script'}
            </span>
          </div>
          <div style="font-size: 0.75rem; color: var(--text-secondary); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
            ${escapeHTML(tc.expected_result)}
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.7rem; color: var(--text-muted); margin-top: 4px;">
            <span>Confidence: ${Math.round(tc.confidence * 100)}%</span>
            ${!hasScript ? `
              <button class="btn btn-primary" style="padding: 2px 8px; font-size: 0.7rem;" 
                      onclick="event.stopPropagation(); window._playwrightWorkspaceHandlers.onGenerateScript('${tc.id}', this)">
                Generate Script
              </button>
            ` : `
              <span style="color: var(--color-success); font-weight: 600;">Ready to Run</span>
            `}
          </div>
        </div>
      `;
    }).join('');
  },

  // Bottom pane executions log grid
  PlaywrightExecutionsHistory(executions) {
    if (!executions || executions.length === 0) {
      return `
        <div style="text-align: center; padding: 20px; color: var(--text-muted); font-size: 0.8rem;">
          No executions recorded for this requirement yet.
        </div>
      `;
    }

    const rows = executions.map(ex => {
      const date = new Date(ex.executed_at).toLocaleString();
      const badgeClass = ex.status === 'passed' ? 'badge-approved' : 'badge-rejected';
      return `
        <tr style="font-family: monospace; font-size: 0.8rem; cursor: pointer;" onclick="window.location.hash = '#/execution/${ex.id}'">
          <td>${ex.id.slice(0, 8)}...</td>
          <td><span class="badge ${badgeClass}" style="padding: 2px 6px;">${escapeHTML(ex.status)}</span></td>
          <td>${ex.duration_seconds.toFixed(2)}s</td>
          <td style="font-family: var(--font-family); color: var(--text-secondary);">${escapeHTML(date)}</td>
          <td style="color: var(--text-muted); font-size: 0.75rem;">${escapeHTML(ex.error_message || 'None')}</td>
        </tr>
      `;
    }).join('');

    return `
      <table class="custom-table" style="font-size: 0.8rem; margin: 0;">
        <thead>
          <tr style="background-color: var(--bg-tertiary);">
            <th>Run ID</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Timestamp</th>
            <th>Errors</th>
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
    `;
  }
};
