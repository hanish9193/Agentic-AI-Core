import { API } from './api.js';
import { Components, escapeHTML } from './components.js';

class App {
  constructor() {
    this.projects = [];
    this.currentProject = null;
    this.requirements = [];
    this.scenarios = [];
    this.testCases = [];
    this.documents = [];
    this.executions = [];
    this.settings = null;
    this.logs = [];

    this.selectedRequirementId = null;
    this.activeExecutionStream = null;
  }

  async init() {
    this.setupEventListeners();
    await this.loadSettings();
    await this.loadProjects();

    const savedProjectId = localStorage.getItem('active_project_id');
    if (savedProjectId && this.projects.some(p => p.id === savedProjectId)) {
      await this.selectProject(savedProjectId);
    } else {
      this.showProjectStartScreen();
    }
  }

  setupEventListeners() {
    // Nav items
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const view = e.currentTarget.getAttribute('data-view');
        if (view) this.navigateTo(view);
      });
    });

    // Project Dropdown
    document.getElementById('project-select').addEventListener('change', async (e) => {
      const val = e.target.value;
      if (val === '__create_new__') {
        this.openModal('create-project-modal');
        e.target.value = this.currentProject ? this.currentProject.id : '';
      } else if (val) {
        await this.selectProject(val);
      }
    });

    // Create Project Form
    document.getElementById('create-project-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('new-proj-name').value.trim();
      const desc = document.getElementById('new-proj-desc').value.trim();
      if (!name) return;

      try {
        const proj = await API.createProject(name, desc);
        this.addLog(`Project '${name}' created`);
        await this.loadProjects();
        this.closeModal('create-project-modal');
        await this.selectProject(proj.id);
      } catch (err) {
        alert(`Failed to create project: ${err.message}`);
      }
    });

    // Create Requirement Form
    document.getElementById('create-requirement-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!this.currentProject) return;

      const title = document.getElementById('req-title').value.trim();
      const desc = document.getElementById('req-desc').value.trim();
      const priority = document.getElementById('req-priority').value;
      const domain = document.getElementById('req-domain').value.trim();

      if (!title || !desc) return;

      try {
        await API.createRequirement(this.currentProject.id, title, desc, priority, domain);
        this.addLog(`Requirement '${title}' added`);
        this.closeModal('create-requirement-modal');
        await this.refreshProjectData();
        this.navigateTo('requirements');
      } catch (err) {
        alert(`Failed to add requirement: ${err.message}`);
      }
    });

    // Settings Form
    document.getElementById('settings-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = {
        llm: {
          provider: document.getElementById('settings-llm-provider').value,
          model: document.getElementById('settings-llm-model').value,
          temperature: parseFloat(document.getElementById('settings-llm-temp').value) || 0.2,
          api_key: document.getElementById('settings-llm-key').value || null,
          api_base: document.getElementById('settings-llm-base').value || null
        },
        workflow: {
          mode: document.getElementById('settings-wf-mode').value,
          human_review_enabled: document.getElementById('settings-wf-review').value === 'true',
          evaluation_threshold: parseFloat(document.getElementById('settings-wf-eval-threshold').value) || 0.75
        },
        browser: {
          type: document.getElementById('settings-browser-type').value,
          headless: document.getElementById('settings-browser-headless').value === 'true'
        },
        generation: {
          scenario_count: parseInt(document.getElementById('settings-gen-count').value) || 3
        },
        evaluation: {
          duplicate_similarity_threshold: parseFloat(document.getElementById('settings-eval-dup').value) || 0.75,
          relevance_rejection_threshold: parseFloat(document.getElementById('settings-eval-rej').value) || 0.3
        }
      };

      try {
        const res = await API.updateSettings(payload);
        this.settings = res.settings;
        this.addLog("Settings updated successfully");
        alert("Configuration updated successfully");
      } catch (err) {
        alert(`Failed to update settings: ${err.message}`);
      }
    });
  }

  addLog(message) {
    const timestamp = new Date().toLocaleTimeString();
    this.logs.unshift({ time: timestamp, message });
    this.renderActivityLogs();
  }

  showProjectStartScreen() {
    this.currentProject = null;
    localStorage.removeItem('active_project_id');
    document.getElementById('sidebar-container').style.display = 'none';
    document.getElementById('project-select-wrapper').style.display = 'none';
    
    const container = document.getElementById('workspace-container');
    const options = this.projects.map(p => `<option value="${p.id}">${escapeHTML(p.name)}</option>`).join('');

    container.innerHTML = `
      <div class="project-start-container">
        <div class="project-start-card">
          <h2>AI Test Automation Platform</h2>
          <p>Create a new workspace or open an existing project to begin orchestrating testing agents.</p>
          
          <div class="project-actions-block">
            ${this.projects.length > 0 ? `
              <div class="form-group">
                <label for="start-project-dropdown">Open Existing Project</label>
                <select id="start-project-dropdown" class="form-control">
                  <option value="" disabled selected>▼ Select Project</option>
                  ${options}
                </select>
              </div>
              <div class="divider">or</div>
            ` : ''}
            
            <button class="btn btn-primary w-100" id="btn-start-create">Create New Project</button>
          </div>
        </div>
      </div>
    `;

    document.getElementById('btn-start-create').addEventListener('click', () => {
      this.openModal('create-project-modal');
    });

    if (this.projects.length > 0) {
      document.getElementById('start-project-dropdown').addEventListener('change', async (e) => {
        const val = e.target.value;
        if (val) {
          await this.selectProject(val);
        }
      });
    }
  }

  async loadSettings() {
    try {
      this.settings = await API.getSettings();
      this.populateSettingsForm();
    } catch (err) {
      this.addLog(`Error loading settings: ${err.message}`);
    }
  }

  populateSettingsForm() {
    if (!this.settings) return;
    document.getElementById('settings-llm-provider').value = this.settings.llm.provider || 'openai';
    document.getElementById('settings-llm-model').value = this.settings.llm.model || '';
    document.getElementById('settings-llm-temp').value = this.settings.llm.temperature || 0.2;
    document.getElementById('settings-llm-key').value = this.settings.llm.api_key || '';
    document.getElementById('settings-llm-base').value = this.settings.llm.api_base || '';

    document.getElementById('settings-wf-mode').value = this.settings.workflow.mode || 'sequential';
    document.getElementById('settings-wf-review').value = String(this.settings.workflow.human_review_enabled);
    document.getElementById('settings-wf-eval-threshold').value = this.settings.workflow.evaluation_threshold || 0.75;

    document.getElementById('settings-browser-type').value = this.settings.browser.type || 'chromium';
    document.getElementById('settings-browser-headless').value = String(this.settings.browser.headless);

    document.getElementById('settings-gen-count').value = this.settings.generation.scenario_count || 3;
    document.getElementById('settings-eval-dup').value = this.settings.evaluation.duplicate_similarity_threshold || 0.75;
    document.getElementById('settings-eval-rej').value = this.settings.evaluation.relevance_rejection_threshold || 0.3;
  }

  async loadProjects() {
    try {
      this.projects = await API.getProjects();
      this.populateProjectDropdown();
    } catch (err) {
      this.addLog(`Error loading projects: ${err.message}`);
    }
  }

  populateProjectDropdown() {
    const dropdown = document.getElementById('project-select');
    dropdown.innerHTML = `
      <option value="" disabled selected>▼ Select Project</option>
      ${this.projects.map(p => `<option value="${p.id}">${escapeHTML(p.name)}</option>`).join('')}
      <option value="__create_new__" style="color: var(--accent-primary); font-weight: 600;">+ Create New Project</option>
    `;
    if (this.currentProject) {
      dropdown.value = this.currentProject.id;
    }
  }

  async selectProject(projectId) {
    try {
      this.currentProject = await API.getProject(projectId);
      localStorage.setItem('active_project_id', projectId);
      
      document.getElementById('sidebar-container').style.display = 'flex';
      document.getElementById('project-select-wrapper').style.display = 'flex';
      document.getElementById('project-select').value = projectId;

      this.addLog(`Project '${this.currentProject.name}' selected`);
      await this.refreshProjectData();
      this.navigateTo('dashboard');
    } catch (err) {
      alert(`Error loading project details: ${err.message}`);
      this.showProjectStartScreen();
    }
  }

  async refreshProjectData() {
    if (!this.currentProject) return;
    try {
      this.requirements = await API.getRequirements(this.currentProject.id);
      this.scenarios = await API.getScenarios(this.currentProject.id);
      this.testCases = await API.getTestCases(this.currentProject.id);
      this.documents = await API.getDocuments(this.currentProject.id);
      this.executions = await API.getExecutionResults(this.currentProject.id);
      
      this.renderDashboardMetrics();
      this.renderRequirements();
      this.renderScenarios();
      this.renderTestCases();
      this.renderDocuments();
      this.renderExecutions();
      this.renderReports();
      this.renderLangSmithTraces();
    } catch (err) {
      this.addLog(`Error refreshing data: ${err.message}`);
    }
  }

  navigateTo(viewName) {
    if (!this.currentProject && viewName !== 'settings') {
      this.showProjectStartScreen();
      return;
    }

    document.querySelectorAll('.view-panel').forEach(panel => {
      panel.classList.remove('active');
    });

    const activePanel = document.getElementById(`${viewName}-view`);
    if (activePanel) {
      activePanel.classList.add('active');
    }

    document.querySelectorAll('.nav-item').forEach(item => {
      if (item.getAttribute('data-view') === viewName) {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    if (document.getElementById('workspace-container').children.length === 1 && document.getElementById('workspace-container').firstElementChild.classList.contains('project-start-container')) {
      location.reload();
    }
  }

  // Dashboard Metrics
  renderDashboardMetrics() {
    const totalReqs = this.requirements.length;
    const totalScenarios = this.scenarios.length;
    const totalTestCases = this.testCases.length;
    const pendingApproval = this.testCases.filter(tc => tc.evaluation_status === 'needs_review').length;
    
    // Average Confidence
    let totalConfidence = 0;
    let counts = 0;
    this.scenarios.forEach(s => {
      totalConfidence += s.confidence;
      counts++;
    });
    this.testCases.forEach(tc => {
      totalConfidence += tc.confidence;
      counts++;
    });
    const avgConfidence = counts > 0 ? `${Math.round((totalConfidence / counts) * 100)}%` : '0%';

    // Pass Ratio
    const runTotal = this.executions.length;
    const passed = this.executions.filter(ex => ex.status === 'passed').length;
    const passRatio = runTotal > 0 ? `${Math.round((passed / runTotal) * 100)}%` : '0%';

    const grid = document.getElementById('dashboard-metrics-grid');
    grid.innerHTML = `
      ${Components.MetricCard("Requirements", totalReqs)}
      ${Components.MetricCard("Generated Scenarios", totalScenarios)}
      ${Components.MetricCard("Generated Test Cases", totalTestCases)}
      ${Components.MetricCard("Pending Approvals", pendingApproval, `${pendingApproval} require human review`)}
      ${Components.MetricCard("Avg Confidence", avgConfidence)}
      ${Components.MetricCard("Automation Pass %", passRatio, `Total executed runs: ${runTotal}`)}
    `;
  }

  renderActivityLogs() {
    const container = document.getElementById('recent-activity-list');
    if (!container) return;
    
    if (this.logs.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); font-size: 0.85rem;">No recent activity logs.</div>`;
      return;
    }
    
    container.innerHTML = this.logs.slice(0, 10).map(log => Components.RecentActivityItem(log)).join('');
  }

  // Requirements Table
  renderRequirements() {
    const container = document.getElementById('requirements-list-container');
    
    const tableHtml = Components.RequirementsTable(this.requirements, {
      onSelect: (reqId) => {
        this.selectedRequirementId = reqId;
        this.renderScenariosRequirementDropdown();
        this.renderTestCasesRequirementDropdown();
        this.navigateTo('scenarios');
      },
      onDelete: async (reqId) => {
        alert("Requirements cannot be deleted to preserve immutability and scenario generation tracking rules.");
      }
    });

    container.innerHTML = tableHtml;
    
    const createBtn = document.getElementById('btn-create-requirement');
    if (createBtn) {
      createBtn.onclick = () => this.openModal('create-requirement-modal');
    }
  }

  // Scenarios Table
  renderScenariosRequirementDropdown() {
    const select = document.getElementById('scenario-req-select');
    if (!select) return;

    select.innerHTML = `
      <option value="" disabled ${!this.selectedRequirementId ? 'selected' : ''}>▼ Choose Requirement</option>
      ${this.requirements.map(r => `<option value="${r.id}" ${r.id === this.selectedRequirementId ? 'selected' : ''}>${escapeHTML(r.title)}</option>`).join('')}
    `;

    select.onchange = (e) => {
      this.selectedRequirementId = e.target.value;
      this.renderScenarios();
      this.renderTestCasesRequirementDropdown();
    };
  }

  async renderScenarios() {
    this.renderScenariosRequirementDropdown();
    const container = document.getElementById('scenarios-list-container');
    
    if (!this.selectedRequirementId) {
      container.innerHTML = Components.EmptyState("Select Requirement", "Choose a requirement from the dropdown list to view or generate scenarios.");
      document.getElementById('scenarios-actions-toolbar').style.display = 'none';
      return;
    }

    document.getElementById('scenarios-actions-toolbar').style.display = 'flex';
    const requirementScenarios = this.scenarios.filter(s => s.requirement_id === this.selectedRequirementId);

    const genCountIn = document.getElementById('sc-generate-count');
    const genBtn = document.getElementById('btn-generate-scenarios');
    
    genBtn.onclick = async () => {
      const count = parseInt(genCountIn.value) || 3;
      container.innerHTML = Components.Spinner(`AI is generating ${count} scenarios for this requirement...`);
      genBtn.disabled = true;
      try {
        await API.generateScenarios(this.currentProject.id, this.selectedRequirementId, count);
        this.addLog(`Generated ${count} scenarios`);
        await this.refreshProjectData();
      } catch (err) {
        alert(`Scenario generation failed: ${err.message}`);
        this.renderScenarios();
      } finally {
        genBtn.disabled = false;
      }
    };

    container.innerHTML = Components.ScenariosTable(requirementScenarios, {
      onApprove: async (id) => {
        try {
          await API.updateScenario(this.currentProject.id, id, { approved: true });
          this.addLog("Scenario approved");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to approve: ${err.message}`);
        }
      },
      onReject: async (id) => {
        try {
          await API.updateScenario(this.currentProject.id, id, { approved: false });
          this.addLog("Scenario marked review pending");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to disapprove: ${err.message}`);
        }
      },
      onSave: async (id, name, desc, priority) => {
        try {
          await API.updateScenario(this.currentProject.id, id, { 
            scenario_name: name,
            description: desc,
            priority: priority
          });
          this.addLog("Scenario updated");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to save: ${err.message}`);
        }
      },
      onDuplicate: async (id) => {
        try {
          await API.duplicateScenario(this.currentProject.id, id);
          this.addLog("Scenario duplicated");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to duplicate: ${err.message}`);
        }
      },
      onDelete: async (id) => {
        if (!confirm("Are you sure you want to delete this scenario?")) return;
        try {
          await API.deleteScenario(this.currentProject.id, id);
          this.addLog("Scenario deleted");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to delete: ${err.message}`);
        }
      }
    });

    // Bind bulk actions toolbar events
    const bulkApprove = document.getElementById('btn-bulk-approve');
    const bulkReject = document.getElementById('btn-bulk-reject');
    if (bulkApprove && bulkReject) {
      bulkApprove.onclick = async () => {
        const ids = this.getSelectedScenarios();
        if (ids.length === 0) return alert("Select at least one scenario");
        for (const id of ids) {
          await API.updateScenario(this.currentProject.id, id, { approved: true });
        }
        this.addLog(`Bulk approved ${ids.length} scenarios`);
        await this.refreshProjectData();
      };
      bulkReject.onclick = async () => {
        const ids = this.getSelectedScenarios();
        if (ids.length === 0) return alert("Select at least one scenario");
        for (const id of ids) {
          await API.updateScenario(this.currentProject.id, id, { approved: false });
        }
        this.addLog(`Bulk rejected ${ids.length} scenarios`);
        await this.refreshProjectData();
      };
    }
  }

  getSelectedScenarios() {
    const checked = [];
    document.querySelectorAll('.scenario-checkbox:checked').forEach(cb => {
      checked.push(cb.getAttribute('data-id'));
    });
    return checked;
  }

  // Test Cases Table
  renderTestCasesRequirementDropdown() {
    const select = document.getElementById('tc-req-select');
    if (!select) return;

    select.innerHTML = `
      <option value="" disabled ${!this.selectedRequirementId ? 'selected' : ''}>▼ Choose Requirement</option>
      ${this.requirements.map(r => `<option value="${r.id}" ${r.id === this.selectedRequirementId ? 'selected' : ''}>${escapeHTML(r.title)}</option>`).join('')}
    `;

    select.onchange = (e) => {
      this.selectedRequirementId = e.target.value;
      this.renderTestCases();
      this.renderScenariosRequirementDropdown();
    };
  }

  async renderTestCases() {
    this.renderTestCasesRequirementDropdown();
    const container = document.getElementById('testcases-list-container');
    
    if (!this.selectedRequirementId) {
      container.innerHTML = Components.EmptyState("Select Requirement", "Choose a requirement from the dropdown list to view or generate test cases.");
      document.getElementById('testcases-actions-toolbar').style.display = 'none';
      return;
    }

    document.getElementById('testcases-actions-toolbar').style.display = 'flex';
    
    const requirementScenarios = this.scenarios.filter(s => s.requirement_id === this.selectedRequirementId);
    const approvedScenarios = requirementScenarios.filter(s => s.approved);
    
    const genBtn = document.getElementById('btn-generate-testcases');
    const warningLabel = document.getElementById('tc-generation-warning');

    if (approvedScenarios.length === 0) {
      genBtn.disabled = true;
      warningLabel.style.display = 'inline';
      warningLabel.innerText = "No approved scenarios exist for this requirement. Approve scenarios first.";
    } else {
      genBtn.disabled = false;
      warningLabel.style.display = 'none';
    }

    genBtn.onclick = async () => {
      container.innerHTML = Components.Spinner("AI Agents are generating and evaluating test cases...");
      genBtn.disabled = true;
      try {
        await API.generateTestCases(this.currentProject.id, this.selectedRequirementId);
        this.addLog("Test cases generated and evaluated");
        await this.refreshProjectData();
      } catch (err) {
        alert(`Test case generation failed: ${err.message}`);
        this.renderTestCases();
      } finally {
        genBtn.disabled = false;
      }
    };

    const scenarioIds = new Set(requirementScenarios.map(s => s.id));
    const requirementTestCases = this.testCases.filter(tc => scenarioIds.has(tc.scenario_id));

    container.innerHTML = Components.TestCasesTable(requirementTestCases, {
      onApprove: async (id) => {
        try {
          await API.updateTestCase(this.currentProject.id, id, { evaluation_status: 'approved' });
          this.addLog("Test case approved");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to approve: ${err.message}`);
        }
      },
      onReject: async (id) => {
        try {
          await API.updateTestCase(this.currentProject.id, id, { evaluation_status: 'rejected' });
          this.addLog("Test case rejected");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to reject: ${err.message}`);
        }
      },
      onSave: async (id, data) => {
        try {
          await API.updateTestCase(this.currentProject.id, id, data);
          this.addLog("Test case updated");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to save: ${err.message}`);
        }
      },
      onDelete: async (id) => {
        if (!confirm("Are you sure you want to delete this test case?")) return;
        try {
          await API.deleteTestCase(this.currentProject.id, id);
          this.addLog("Test case deleted");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to delete: ${err.message}`);
        }
      },
      onViewScript: (id) => {
        this.openPlaywrightScriptWorkspace(id);
      }
    });

    // Bulk actions
    const bulkTcApprove = document.getElementById('btn-bulk-tc-approve');
    const bulkTcReject = document.getElementById('btn-bulk-tc-reject');
    if (bulkTcApprove && bulkTcReject) {
      bulkTcApprove.onclick = async () => {
        const ids = this.getSelectedTestCases();
        if (ids.length === 0) return alert("Select at least one test case");
        for (const id of ids) {
          await API.updateTestCase(this.currentProject.id, id, { evaluation_status: 'approved' });
        }
        this.addLog(`Bulk approved ${ids.length} test cases`);
        await this.refreshProjectData();
      };
      bulkTcReject.onclick = async () => {
        const ids = this.getSelectedTestCases();
        if (ids.length === 0) return alert("Select at least one test case");
        for (const id of ids) {
          await API.updateTestCase(this.currentProject.id, id, { evaluation_status: 'rejected' });
        }
        this.addLog(`Bulk rejected ${ids.length} test cases`);
        await this.refreshProjectData();
      };
    }
  }

  getSelectedTestCases() {
    const checked = [];
    document.querySelectorAll('.tc-checkbox:checked').forEach(cb => {
      checked.push(cb.getAttribute('data-id'));
    });
    return checked;
  }

  // Playwright script viewer Workspace
  openPlaywrightScriptWorkspace(testCaseId) {
    const tc = this.testCases.find(t => t.id === testCaseId);
    if (!tc) return;

    this.openModal('script-workspace-modal');
    this.renderScriptWorkspace(tc);
  }

  renderScriptWorkspace(tc) {
    const container = document.getElementById('script-modal-workspace-body');
    const hasScript = !!tc.playwright_script;

    if (!hasScript) {
      container.innerHTML = `
        <div style="text-align: center; padding: 40px 0;">
          <p style="color: var(--text-secondary); margin-bottom: 20px;">No Playwright script generated for this test case yet.</p>
          <button class="btn btn-primary" id="btn-modal-generate-script">Generate Script</button>
        </div>
      `;

      document.getElementById('btn-modal-generate-script').onclick = async () => {
        container.innerHTML = Components.Spinner("AI Agent is writing Playwright TypeScript test...");
        try {
          const updated = await API.generatePlaywrightScript(this.currentProject.id, tc.id);
          this.addLog(`Playwright script generated for '${tc.title}'`);
          await this.refreshProjectData();
          this.renderScriptWorkspace(updated);
        } catch (err) {
          alert(`Script generation failed: ${err.message}`);
          this.renderScriptWorkspace(tc);
        }
      };
      return;
    }

    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <div style="font-size: 0.85rem; color: var(--text-secondary); font-family: monospace;">playwright/test.spec.ts</div>
          <div class="gap-12">
            <button class="btn btn-secondary" id="btn-script-copy">Copy Code</button>
            <button class="btn btn-secondary" id="btn-script-regenerate">Re-generate</button>
            <button class="btn btn-primary" id="btn-script-run">Run Playwright Test</button>
          </div>
        </div>
        
        <pre style="background-color: var(--bg-primary); border: 1px solid var(--border-color); padding: 16px; border-radius: var(--border-radius-md); overflow-x: auto; max-height: 400px;"><code style="font-family: monospace; font-size: 0.85rem; color: #a5b4fc;">${escapeHTML(tc.playwright_script)}</code></pre>
      </div>
    `;

    document.getElementById('btn-script-copy').onclick = () => {
      navigator.clipboard.writeText(tc.playwright_script);
      alert("Script copied to clipboard");
    };

    document.getElementById('btn-script-regenerate').onclick = async () => {
      container.innerHTML = Components.Spinner("Re-generating Playwright script...");
      try {
        const updated = await API.generatePlaywrightScript(this.currentProject.id, tc.id);
        this.addLog(`Re-generated script for '${tc.title}'`);
        await this.refreshProjectData();
        this.renderScriptWorkspace(updated);
      } catch (err) {
        alert(`Script re-generation failed: ${err.message}`);
        this.renderScriptWorkspace(tc);
      }
    };

    document.getElementById('btn-script-run').onclick = () => {
      this.closeModal('script-workspace-modal');
      this.openExecutionWorkspace(tc.id);
    };
  }

  // Execution Workspace (Four-Panel Layout)
  openExecutionWorkspace(testCaseId) {
    const tc = this.testCases.find(t => t.id === testCaseId);
    if (!tc) return;

    this.openModal('execution-workspace-modal');
    
    // Initial static structure of workspace modal
    const body = document.getElementById('execution-workspace-modal-body');
    body.innerHTML = `
      <div style="display: grid; grid-template-rows: 1fr auto; height: 75vh; gap: 16px;">
        <!-- Top Triple panels -->
        <div style="display: grid; grid-template-columns: 240px 1fr 320px; gap: 16px; min-height: 0;">
          <!-- Left Timeline panel -->
          <div style="background-color: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--border-radius-md); padding: 16px; overflow-y: auto;">
            <h4 style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 16px; letter-spacing: 0.5px;">Timeline</h4>
            <div class="timeline" id="exec-timeline-list">
              <div class="timeline-item" id="time-gen"><div class="timeline-icon">1</div><div class="timeline-content"><div class="timeline-title">Generating</div><div class="timeline-desc">Setting up config...</div></div></div>
              <div class="timeline-item" id="time-run"><div class="timeline-icon">2</div><div class="timeline-content"><div class="timeline-title">Running</div><div class="timeline-desc">Playwright execution...</div></div></div>
              <div class="timeline-item" id="time-snap"><div class="timeline-icon">3</div><div class="timeline-content"><div class="timeline-title">Screen Capture</div><div class="timeline-desc">Analyzing pages...</div></div></div>
              <div class="timeline-item" id="time-trace"><div class="timeline-icon">4</div><div class="timeline-content"><div class="timeline-title">Collecting Trace</div><div class="timeline-desc">Saving trace.zip...</div></div></div>
              <div class="timeline-item" id="time-comp"><div class="timeline-icon">5</div><div class="timeline-content"><div class="timeline-title">Completed</div><div class="timeline-desc">Done.</div></div></div>
            </div>
          </div>
          
          <!-- Center Live Browser panel -->
          <div style="background-color: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--border-radius-md); padding: 16px; display: flex; flex-direction: column; min-height: 0;">
            <h4 style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 12px;">Live Browser View</h4>
            <div style="flex-grow: 1; border: 1px solid var(--border-color); border-radius: 4px; display: flex; align-items: center; justify-content: center; background-color: #020617; overflow: hidden; position: relative;" id="exec-browser-screen">
              <span style="color: var(--text-muted); font-size: 0.85rem;" id="exec-browser-placeholder">Waiting for browser launch...</span>
              <img id="exec-browser-img" style="display: none; max-width: 100%; max-height: 100%; object-fit: contain;" src="" />
            </div>
          </div>
          
          <!-- Right Console logs panel -->
          <div style="background-color: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--border-radius-md); padding: 16px; display: flex; flex-direction: column; min-height: 0;">
            <h4 style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 12px;">Console Logs</h4>
            <div style="flex-grow: 1; font-family: monospace; font-size: 0.75rem; background-color: #020617; padding: 12px; border-radius: 4px; overflow-y: auto; color: #cbd5e1; white-space: pre-wrap; line-height: 1.4;" id="exec-console-logs"></div>
          </div>
        </div>
        
        <!-- Bottom Artifacts panel -->
        <div style="background-color: var(--bg-primary); border: 1px solid var(--border-color); border-radius: var(--border-radius-md); padding: 16px; display: flex; justify-content: space-between; align-items: center;" id="exec-bottom-panel">
          <div>
            <span style="color: var(--text-secondary); font-size: 0.8rem;">Status: </span>
            <span id="exec-status-badge" class="badge badge-pending">Running</span>
          </div>
          <div class="gap-12" id="exec-artifacts-links">
            <span style="color: var(--text-muted); font-size: 0.8rem;">No artifacts collected yet.</span>
          </div>
        </div>
      </div>
    `;

    this.startExecutionStream(testCaseId);
  }

  async startExecutionStream(testCaseId) {
    if (this.activeExecutionStream) {
      this.activeExecutionStream.close();
    }

    const consoleDiv = document.getElementById('exec-console-logs');
    const timelineList = document.getElementById('exec-timeline-list');
    const browserPlaceholder = document.getElementById('exec-browser-placeholder');
    const browserImg = document.getElementById('exec-browser-img');
    const statusBadge = document.getElementById('exec-status-badge');
    const bottomPanelLinks = document.getElementById('exec-artifacts-links');

    // Trigger API execution call in backend
    try {
      await API.executeTestCase(this.currentProject.id, testCaseId);
    } catch (err) {
      consoleDiv.innerText += `\nError launching execution: ${err.message}`;
      statusBadge.className = "badge badge-rejected";
      statusBadge.innerText = "Error";
      return;
    }

    // Connect Server-Sent Events (SSE) Stream
    const stream = new EventSource(`/api/v1/projects/${this.currentProject.id}/testcases/${testCaseId}/execution-stream`);
    this.activeExecutionStream = stream;

    stream.onmessage = async (e) => {
      const data = JSON.parse(e.data);

      // Append log message
      if (data.log) {
        consoleDiv.innerText += `\n[${new Date().toLocaleTimeString()}] ${data.log}`;
        consoleDiv.scrollTop = consoleDiv.scrollHeight;
      }

      // Timeline status updates
      if (data.status) {
        document.querySelectorAll('.timeline-item').forEach(el => el.classList.remove('active', 'completed'));
        
        let activeId = "";
        if (data.status === "Generating") {
          activeId = "time-gen";
          document.getElementById('time-gen').classList.add('active');
        } else if (data.status === "Running") {
          document.getElementById('time-gen').classList.add('completed');
          document.getElementById('time-run').classList.add('active');
        } else if (data.status === "Capturing Screenshots") {
          document.getElementById('time-gen').classList.add('completed');
          document.getElementById('time-run').classList.add('completed');
          document.getElementById('time-snap').classList.add('active');
        } else if (data.status === "Collecting Trace") {
          document.getElementById('time-gen').classList.add('completed');
          document.getElementById('time-run').classList.add('completed');
          document.getElementById('time-snap').classList.add('completed');
          document.getElementById('time-trace').classList.add('active');
        } else if (data.status === "Completed") {
          document.getElementById('time-gen').classList.add('completed');
          document.getElementById('time-run').classList.add('completed');
          document.getElementById('time-snap').classList.add('completed');
          document.getElementById('time-trace').classList.add('completed');
          document.getElementById('time-comp').classList.add('completed');
        }
      }

      // Screenshot update
      if (data.screenshot) {
        browserPlaceholder.style.display = 'none';
        browserImg.style.display = 'block';
        // Add random timestamp query string to bypass browser cache
        browserImg.src = `${data.screenshot}?t=${new Date().getTime()}`;
      }

      // Execution complete
      if (data.status === "Completed") {
        stream.close();
        this.addLog("Execution complete");
        
        statusBadge.className = data.artifact && data.artifact.status === 'passed' ? 'badge badge-approved' : 'badge badge-rejected';
        statusBadge.innerText = data.artifact ? data.artifact.status : 'Finished';

        if (data.artifact) {
          // Render downloadable artifact links
          bottomPanelLinks.innerHTML = `
            <a href="${data.artifact.screenshot || '#'}" target="_blank" class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;">Screenshot</a>
            <a href="${data.artifact.video || '#'}" target="_blank" class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;">Video</a>
            <a href="${data.artifact.trace || '#'}" target="_blank" class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;">Trace.zip</a>
            <button class="btn btn-primary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="alert('HTML Report generated in artifacts folder')">HTML Report</button>
            <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 0.75rem;" onclick="alert('JSON Report generated in artifacts folder')">JSON Report</button>
          `;
        }

        // Re-fetch project datasets to synchronize backend source of truth
        await this.refreshProjectData();
      }
    };

    stream.onerror = () => {
      stream.close();
      statusBadge.className = "badge badge-rejected";
      statusBadge.innerText = "Error";
      consoleDiv.innerText += `\n[Stream Error] Connection terminated unexpectedly.`;
    };
  }

  // Documents Page / Knowledge Base
  renderDocuments() {
    const container = document.getElementById('documents-list-container');
    container.innerHTML = Components.DocumentsTable(this.documents, async (id) => {
      if (!confirm("Are you sure you want to delete this document from the Knowledge Base?")) return;
      try {
        await API.deleteDocument(this.currentProject.id, id);
        this.addLog("Document deleted from Knowledge Base");
        await this.refreshProjectData();
      } catch (err) {
        alert(`Failed to delete document: ${err.message}`);
      }
    });

    // Setup drag-and-drop listener for the upload widget
    const dropzone = document.getElementById('kb-dropzone');
    if (!dropzone) return;

    // Reset drag drop bindings to prevent duplication
    dropzone.ondragover = (e) => {
      e.preventDefault();
      dropzone.style.borderColor = 'var(--accent-primary)';
      dropzone.style.backgroundColor = 'rgba(59, 130, 246, 0.03)';
    };

    dropzone.ondragleave = () => {
      dropzone.style.borderColor = 'var(--border-color)';
      dropzone.style.backgroundColor = 'transparent';
    };

    dropzone.ondrop = async (e) => {
      e.preventDefault();
      dropzone.style.borderColor = 'var(--border-color)';
      dropzone.style.backgroundColor = 'transparent';

      const files = e.dataTransfer.files;
      if (files.length === 0) return;

      const file = files[0];
      const validExtensions = ['.pdf', '.docx', '.xlsx', '.csv', '.txt'];
      const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      if (!validExtensions.includes(fileExt)) {
        alert("Invalid file format. Upload PDF, DOCX, XLSX, CSV, or TXT.");
        return;
      }

      // Show mock upload progress bar
      dropzone.innerHTML = `
        <div style="width: 100%;">
          <div style="font-size: 0.8rem; margin-bottom: 8px;">Uploading ${escapeHTML(file.name)}...</div>
          <div style="background-color: var(--bg-primary); height: 8px; border-radius: 4px; overflow: hidden; border: 1px solid var(--border-color);">
            <div id="upload-progress-bar" style="background-color: var(--accent-primary); width: 0%; height: 100%; transition: width 0.15s ease;"></div>
          </div>
        </div>
      `;

      const progressBar = document.getElementById('upload-progress-bar');
      let progress = 0;
      const interval = setInterval(async () => {
        progress += 10;
        progressBar.style.width = `${progress}%`;
        if (progress >= 100) {
          clearInterval(interval);
          
          // Save document metadata
          try {
            await API.createDocument(this.currentProject.id, {
              filename: file.name,
              original_filename: file.name,
              mime_type: file.type || 'text/plain',
              size: file.size,
              storage_path: `/data/${file.name}`
            });
            this.addLog(`Document '${file.name}' added to Knowledge Base`);
            await this.refreshProjectData();
          } catch (err) {
            alert(`Upload failed: ${err.message}`);
          } finally {
            // Restore dropzone HTML
            dropzone.innerHTML = `
              Drag and drop target files here to parse (PDF, DOCX, XLSX, CSV, TXT)
              <div style="margin-top: 8px; font-size: 0.75rem; background-color: var(--bg-tertiary); padding: 4px 8px; border-radius: 4px; display: inline-block; border: 1px solid var(--border-color);">RAG Extraction Active</div>
            `;
          }
        }
      }, 100);
    };
  }

  // Executions History Renderer
  renderExecutions() {
    const container = document.getElementById('executions-list-container');
    container.innerHTML = Components.ExecutionsTable(this.executions);
  }

  // LangSmith Trace Logs
  async renderLangSmithTraces() {
    const container = document.getElementById('langsmith-traces-container');
    if (!container) return;

    try {
      const traceData = await API.getTraces(this.currentProject.id);
      container.innerHTML = Components.LangSmithTraces(traceData);
    } catch (err) {
      container.innerHTML = `<div style="color: var(--color-danger); font-size: 0.85rem;">Failed to load LangSmith traces: ${err.message}</div>`;
    }
  }

  // Reports view renderer
  renderReports() {
    const container = document.getElementById('reports-workspace-container');
    if (!container) return;

    if (this.executions.length === 0) {
      container.innerHTML = this.EmptyState("No Execution Reports", "No executions have occurred yet. Run scripts to compile JUnit, HTML, and JSON reports.");
      return;
    }

    const runTotal = this.executions.length;
    const passed = this.executions.filter(ex => ex.status === 'passed').length;
    const failed = this.executions.filter(ex => ex.status === 'failed').length;
    const errors = this.executions.filter(ex => ex.status === 'error').length;
    const skipped = this.executions.filter(ex => ex.status === 'skipped').length;
    
    // Average Timing calculation
    let totalSecs = 0;
    this.executions.forEach(ex => totalSecs += ex.duration_seconds);
    const avgDuration = runTotal > 0 ? (totalSecs / runTotal).toFixed(2) : "0";

    const passPct = Math.round((passed / runTotal) * 100);

    container.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px; margin-bottom: 32px;">
        <div class="metric-card">
          <div class="metric-label">Pass / Total Runs</div>
          <div class="metric-value" style="color: var(--color-success);">${passed} / ${runTotal}</div>
          <div class="metric-footer">${passPct}% success rate</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Failed Runs</div>
          <div class="metric-value" style="color: var(--color-danger);">${failed}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Errors / Blocked</div>
          <div class="metric-value" style="color: var(--color-warning);">${errors + skipped}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Avg Run Duration</div>
          <div class="metric-value">${avgDuration}s</div>
        </div>
      </div>

      <div class="section-card" style="margin-bottom: 24px;">
        <h2>Export Automation Reports</h2>
        <div style="display: flex; gap: 16px; margin-top: 12px;">
          <button class="btn btn-primary" onclick="alert('Download PDF report initiated...')">Download PDF Report</button>
          <button class="btn btn-secondary" onclick="alert('Download HTML report package...')">Download HTML Package</button>
          <button class="btn btn-secondary" onclick="alert('Download JSON report initiated...')">Download JSON Logs</button>
          <button class="btn btn-secondary" onclick="alert('Download JUnit XML log structure...')">Download JUnit XML</button>
        </div>
      </div>
    `;
  }

  // Modal helpers
  openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
  }

  closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const app = new App();
  window.appInstance = app;
  app.init().catch(console.error);
  
  window.closeModal = (modalId) => app.closeModal(modalId);
});
