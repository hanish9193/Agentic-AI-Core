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
    this.scenariosNotes = {};
    this.testCasesNotes = {};
    this.settings = null;
    this.logs = [];

    this.selectedRequirementId = null;
    this.activePlaywrightTestCaseId = null;
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

    this.selectedRequirementId = localStorage.getItem('playwright_active_req_id') || null;
    this.activePlaywrightTestCaseId = localStorage.getItem('playwright_active_testcase_id') || null;

    // Initialize SPA routing
    window.addEventListener('hashchange', () => this.handleRouting());
    await this.handleRouting();
  }

  setupEventListeners() {
    // Nav items
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const view = e.currentTarget.getAttribute('data-view');
        if (view) this.navigateTo(view);
      });
    });

    // Theme Toggle Trigger with Native View Transitions API
    const themeBtn = document.getElementById('theme-toggle-btn');
    if (themeBtn) {
      themeBtn.addEventListener('click', (e) => {
        const toggleTheme = () => {
          const isDark = !document.body.classList.contains('light-theme');
          if (isDark) {
            document.body.classList.add('light-theme');
            document.getElementById('theme-toggle-icon').innerHTML = `
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m12.728 12.728l.707-.707M12 8a4 4 0 100 8 4 4 0 000-8z" />
            `;
          } else {
            document.body.classList.remove('light-theme');
            document.getElementById('theme-toggle-icon').innerHTML = `
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            `;
          }
          if (window.monaco) {
            const currentTheme = document.body.classList.contains('light-theme') ? 'vs' : 'vs-dark';
            monaco.editor.setTheme(currentTheme);
          }
        };

        if (!document.startViewTransition) {
          toggleTheme();
          return;
        }

        // Get circular expansion coordinates centered on the toggle button
        const rect = themeBtn.getBoundingClientRect();
        const x = rect.left + rect.width / 2;
        const y = rect.top + rect.height / 2;
        const endRadius = Math.hypot(
          Math.max(x, window.innerWidth - x),
          Math.max(y, window.innerHeight - y)
        );

        const transition = document.startViewTransition(() => {
          toggleTheme();
        });

        transition.ready.then(() => {
          document.documentElement.animate(
            {
              clipPath: [
                `circle(0px at ${x}px ${y}px)`,
                `circle(${endRadius}px at ${x}px ${y}px)`
              ]
            },
            {
              duration: 400, // Super fast and fluid (400ms)
              easing: 'ease-out',
              pseudoElement: '::view-transition-new(root)'
            }
          );
        });
      });
    }

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
      const lob = document.getElementById('new-proj-lob').value;
      if (!name) return;

      try {
        const proj = await API.createProject(name, desc, lob);
        this.addLog(`Project '${name}' in LOB '${lob}' created`);
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

    // Requirement Import file browse trigger
    const fileInput = document.getElementById('import-req-file');
    if (fileInput) {
      fileInput.addEventListener('change', async (e) => {
        const files = e.target.files;
        if (files.length === 0) return;
        await this.uploadRequirementFile(files[0]);
        fileInput.value = '';
      });
    }

    // Requirements Upload Dropzone
    const reqDropzone = document.getElementById('req-upload-dropzone');
    if (reqDropzone) {
      reqDropzone.onclick = () => fileInput.click();

      reqDropzone.ondragover = (e) => {
        e.preventDefault();
        reqDropzone.style.borderColor = 'var(--accent-primary)';
        reqDropzone.style.backgroundColor = 'rgba(59, 130, 246, 0.03)';
      };

      reqDropzone.ondragleave = () => {
        reqDropzone.style.borderColor = 'var(--border-color)';
        reqDropzone.style.backgroundColor = 'var(--bg-secondary)';
      };

      reqDropzone.ondrop = async (e) => {
        e.preventDefault();
        reqDropzone.style.borderColor = 'var(--border-color)';
        reqDropzone.style.backgroundColor = 'var(--bg-secondary)';

        const files = e.dataTransfer.files;
        if (files.length > 0) {
          await this.uploadRequirementFile(files[0]);
        }
      };
    }

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

  async uploadRequirementFile(file) {
    const container = document.getElementById('requirements-list-container');
    container.innerHTML = Components.Spinner(`Importing and parsing '${file.name}' requirements...`);
    try {
      const imported = await API.importRequirements(this.currentProject.id, file);
      this.addLog(`Imported ${imported.length} requirement(s) from '${file.name}'`);
      await this.refreshProjectData();
    } catch (err) {
      alert(`Import failed: ${err.message}`);
      await this.refreshProjectData();
    }
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
      ${this.projects.map(p => `<option value="${p.id}">${escapeHTML(p.name)} [${escapeHTML(p.line_of_business)}]</option>`).join('')}
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
      
      // Concurrently fetch comments/notes for all scenarios and test cases
      this.scenariosNotes = {};
      this.testCasesNotes = {};
      
      await Promise.all([
        ...this.scenarios.map(async s => {
          try {
            const notes = await API.getScenarioNotes(s.id);
            this.scenariosNotes[s.id] = notes;
          } catch(e) {}
        }),
        ...this.testCases.map(async tc => {
          try {
            const notes = await API.getTestCaseNotes(tc.id);
            this.testCasesNotes[tc.id] = notes;
          } catch(e) {}
        })
      ]);

      this.renderDashboardMetrics();
      this.renderRequirements();
      this.renderScenarios();
      this.renderScenarioApproval();
      this.renderTestCases();
      this.renderTestCaseApproval();
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

    if (window.location.hash !== `#/${viewName}`) {
      window.location.hash = `#/${viewName}`;
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

    if (viewName === 'scenario-approval') this.renderScenarioApproval();
    if (viewName === 'testcase-approval') this.renderTestCaseApproval();
    if (viewName === 'playwright') this.renderPlaywrightWorkspace();
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

    // Mock/Dynamic Token Cost estimation based on LLM logs
    const scCount = this.scenarios.length;
    const tcCount = this.testCases.length;
    const inputTokens = scCount * 850 + tcCount * 1200;
    const outputTokens = scCount * 450 + tcCount * 800;
    const totalTokens = inputTokens + outputTokens;
    const estimatedCost = (inputTokens * 0.00015 + outputTokens * 0.0006) / 100;

    const grid = document.getElementById('dashboard-metrics-grid');
    grid.innerHTML = `
      ${Components.MetricCard("Requirements", totalReqs)}
      ${Components.MetricCard("Generated Scenarios", totalScenarios)}
      ${Components.MetricCard("Generated Test Cases", totalTestCases)}
      ${Components.MetricCard("Automation Pass %", passRatio, `Total executed runs: ${runTotal}`)}
      ${Components.MetricCard("Avg Confidence", avgConfidence)}
      ${Components.MetricCard("Token Costs", `$${estimatedCost.toFixed(4)}`, `Total Tokens consumed: ${totalTokens}`)}
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
      }
    });

    container.innerHTML = tableHtml;
    
    const createBtn = document.getElementById('btn-create-requirement');
    if (createBtn) {
      createBtn.onclick = () => this.openModal('create-requirement-modal');
    }
  }

  formatRequirementLabel(r) {
    if (r.original_filename) {
      return r.original_filename;
    }
    if (r.requirement_id && r.requirement_title) {
      return `${r.requirement_id}: ${r.requirement_title}`;
    }
    if (r.requirement_title) {
      return r.requirement_title;
    }
    return r.title;
  }

  // Scenarios Table
  renderScenariosRequirementDropdown() {
    const select = document.getElementById('scenario-req-select');
    if (!select) return;

    select.innerHTML = `
      <option value="" disabled ${!this.selectedRequirementId ? 'selected' : ''}>▼ Choose Requirement</option>
      ${this.requirements.map(r => `<option value="${r.id}" ${r.id === this.selectedRequirementId ? 'selected' : ''}>${escapeHTML(this.formatRequirementLabel(r))}</option>`).join('')}
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
      
      const runGeneration = async (mode) => {
        container.innerHTML = Components.Spinner(`AI is generating ${count} scenarios for this requirement...`);
        genBtn.disabled = true;
        try {
          await API.generateScenarios(this.currentProject.id, this.selectedRequirementId, count, mode);
          this.addLog(`Generated ${count} scenarios (${mode})`);
          await this.refreshProjectData();
        } catch (err) {
          alert(`Scenario generation failed: ${err.message}`);
          this.renderScenarios();
        } finally {
          genBtn.disabled = false;
        }
      };

      if (requirementScenarios.length > 0) {
        this.openModal('confirm-scenarios-modal');
        
        document.getElementById('btn-confirm-sc-append').onclick = async () => {
          this.closeModal('confirm-scenarios-modal');
          await runGeneration('append');
        };

        document.getElementById('btn-confirm-sc-replace').onclick = async () => {
          this.closeModal('confirm-scenarios-modal');
          await runGeneration('replace');
        };
      } else {
        await runGeneration('replace');
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
      },
      onAddNote: async (id, note) => {
        try {
          await API.addScenarioNote(id, note);
          this.addLog("Scenario review comment added");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to add note: ${err.message}`);
        }
      }
    }, this.scenariosNotes);

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
      ${this.requirements.map(r => `<option value="${r.id}" ${r.id === this.selectedRequirementId ? 'selected' : ''}>${escapeHTML(this.formatRequirementLabel(r))}</option>`).join('')}
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
      genBtn.innerText = "Generate Test Cases (Approve at least one Scenario)";
      warningLabel.style.display = 'none';
    } else {
      genBtn.disabled = false;
      genBtn.innerText = "Generate & Evaluate Test Cases";
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

    const approvedScenarioIds = new Set(approvedScenarios.map(s => s.id));
    const requirementTestCases = this.testCases.filter(tc => approvedScenarioIds.has(tc.scenario_id));

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
      },
      onGenerateScript: async (id, btn) => {
        btn.disabled = true;
        btn.innerText = "Generating...";
        try {
          await API.generatePlaywrightScript(this.currentProject.id, id);
          this.addLog("Playwright script generated for test case");
          await this.refreshProjectData();
          this.renderTestCases();
          this.openPlaywrightScriptWorkspace(id);
        } catch (err) {
          alert(`Script generation failed: ${err.message}`);
          btn.disabled = false;
          btn.innerText = "Generate Script";
        }
      },
      onAddNote: async (id, note) => {
        try {
          await API.addTestCaseNote(id, note);
          this.addLog("Test case comment added");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to add note: ${err.message}`);
        }
      }
    }, this.testCasesNotes);

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

  renderScenarioApprovalRequirementDropdown() {
    const select = document.getElementById('sc-approval-req-select');
    if (!select) return;

    select.innerHTML = `
      <option value="" disabled ${!this.selectedRequirementId ? 'selected' : ''}>▼ Choose Requirement</option>
      ${this.requirements.map(r => `<option value="${r.id}" ${r.id === this.selectedRequirementId ? 'selected' : ''}>${escapeHTML(this.formatRequirementLabel(r))}</option>`).join('')}
    `;

    select.onchange = (e) => {
      this.selectedRequirementId = e.target.value;
      this.renderScenarioApproval();
    };
  }

  async renderScenarioApproval() {
    this.renderScenarioApprovalRequirementDropdown();
    const container = document.getElementById('scenario-approval-list-container');
    if (!container) return;
    
    if (!this.selectedRequirementId) {
      container.innerHTML = Components.EmptyState("Select Requirement", "Choose a requirement from the dropdown list to approve scenarios.");
      document.getElementById('sc-approval-actions-toolbar').style.display = 'none';
      return;
    }

    document.getElementById('sc-approval-actions-toolbar').style.display = 'flex';
    const requirementScenarios = this.scenarios.filter(s => s.requirement_id === this.selectedRequirementId);

    // Bind bulk approval triggers
    const bulkApprove = document.getElementById('btn-sc-approval-bulk-approve');
    const bulkReject = document.getElementById('btn-sc-approval-bulk-reject');
    if (bulkApprove) {
      bulkApprove.onclick = async () => {
        const ids = this.getSelectedScenarios();
        if (ids.length === 0) return alert("Select at least one scenario");
        for (const id of ids) {
          await API.updateScenario(this.currentProject.id, id, { approved: true });
        }
        this.addLog(`Bulk approved ${ids.length} scenarios`);
        await this.refreshProjectData();
      };
    }
    if (bulkReject) {
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
      },
      onAddNote: async (id, note) => {
        try {
          await API.addScenarioNote(id, note);
          this.addLog("Scenario review comment added");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to add note: ${err.message}`);
        }
      }
    }, this.scenariosNotes);
  }

  renderTestCaseApprovalRequirementDropdown() {
    const select = document.getElementById('tc-approval-req-select');
    if (!select) return;

    select.innerHTML = `
      <option value="" disabled ${!this.selectedRequirementId ? 'selected' : ''}>▼ Choose Requirement</option>
      ${this.requirements.map(r => `<option value="${r.id}" ${r.id === this.selectedRequirementId ? 'selected' : ''}>${escapeHTML(this.formatRequirementLabel(r))}</option>`).join('')}
    `;

    select.onchange = (e) => {
      this.selectedRequirementId = e.target.value;
      this.renderTestCaseApproval();
    };
  }

  async renderTestCaseApproval() {
    this.renderTestCaseApprovalRequirementDropdown();
    const container = document.getElementById('testcase-approval-list-container');
    if (!container) return;

    if (!this.selectedRequirementId) {
      container.innerHTML = Components.EmptyState("Select Requirement", "Choose a requirement from the dropdown list to approve test cases.");
      document.getElementById('tc-approval-actions-toolbar').style.display = 'none';
      return;
    }

    document.getElementById('tc-approval-actions-toolbar').style.display = 'flex';
    const requirementScenarios = this.scenarios.filter(s => s.requirement_id === this.selectedRequirementId);
    const approvedScenarios = requirementScenarios.filter(s => s.approved);
    const approvedScenarioIds = new Set(approvedScenarios.map(s => s.id));
    const requirementTestCases = this.testCases.filter(tc => approvedScenarioIds.has(tc.scenario_id));

    // Bind bulk approval triggers
    const bulkTCApprove = document.getElementById('btn-tc-approval-bulk-approve');
    const bulkTCReject = document.getElementById('btn-tc-approval-bulk-reject');
    if (bulkTCApprove) {
      bulkTCApprove.onclick = async () => {
        const ids = this.getSelectedTestCases();
        if (ids.length === 0) return alert("Select at least one test case");
        for (const id of ids) {
          await API.updateTestCase(this.currentProject.id, id, { evaluation_status: 'approved' });
        }
        this.addLog(`Bulk approved ${ids.length} test cases`);
        await this.refreshProjectData();
      };
    }
    if (bulkTCReject) {
      bulkTCReject.onclick = async () => {
        const ids = this.getSelectedTestCases();
        if (ids.length === 0) return alert("Select at least one test case");
        for (const id of ids) {
          await API.updateTestCase(this.currentProject.id, id, { evaluation_status: 'rejected' });
        }
        this.addLog(`Bulk rejected ${ids.length} test cases`);
        await this.refreshProjectData();
      };
    }

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
      },
      onGenerateScript: async (id, btn) => {
        btn.disabled = true;
        btn.innerText = "Generating...";
        try {
          await API.generatePlaywrightScript(this.currentProject.id, id);
          this.addLog("Playwright script generated for test case");
          await this.refreshProjectData();
          this.renderTestCaseApproval();
          this.openPlaywrightScriptWorkspace(id);
        } catch (err) {
          alert(`Script generation failed: ${err.message}`);
          btn.disabled = false;
          btn.innerText = "Generate Script";
        }
      },
      onAddNote: async (id, note) => {
        try {
          await API.addTestCaseNote(id, note);
          this.addLog("Test case comment added");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to add note: ${err.message}`);
        }
      }
    }, this.testCasesNotes);
  }

  renderPlaywrightWorkspaceRequirementDropdown() {
    const select = document.getElementById('playwright-req-select');
    if (!select) return;

    select.innerHTML = `
      <option value="" disabled ${!this.selectedRequirementId ? 'selected' : ''}>▼ Choose Requirement</option>
      ${this.requirements.map(r => `<option value="${r.id}" ${r.id === this.selectedRequirementId ? 'selected' : ''}>${escapeHTML(this.formatRequirementLabel(r))}</option>`).join('')}
    `;

    select.onchange = (e) => {
      this.selectedRequirementId = e.target.value;
      localStorage.setItem('playwright_active_req_id', this.selectedRequirementId);
      this.activePlaywrightTestCaseId = null;
      localStorage.removeItem('playwright_active_testcase_id');
      this.renderPlaywrightWorkspace();
    };
  }

  async renderPlaywrightWorkspace() {
    this.renderPlaywrightWorkspaceRequirementDropdown();
    
    const reqSelect = document.getElementById('playwright-req-select');
    const scenarioSelect = document.getElementById('playwright-scenario-select');
    const listContainer = document.getElementById('playwright-list-container');
    const editorContainer = document.getElementById('playwright-editor-container');
    const executionsContainer = document.getElementById('playwright-executions-container');
    const approvedCountEl = document.getElementById('playwright-approved-count');
    const activeTitleEl = document.getElementById('playwright-active-title');
    const unsavedDot = document.getElementById('playwright-unsaved-dot');
    const editorActions = document.getElementById('playwright-editor-actions');

    if (!reqSelect || !listContainer) return;

    if (!this.selectedRequirementId) {
      const savedReqId = localStorage.getItem('playwright_active_req_id');
      if (savedReqId && this.requirements.some(r => r.id === savedReqId)) {
        this.selectedRequirementId = savedReqId;
      }
    }

    if (!this.selectedRequirementId && this.requirements.length > 0) {
      this.selectedRequirementId = this.requirements[0].id;
    }

    if (this.selectedRequirementId) {
      localStorage.setItem('playwright_active_req_id', this.selectedRequirementId);
      reqSelect.value = this.selectedRequirementId;
    }

    const requirementScenarios = this.scenarios.filter(s => s.requirement_id === this.selectedRequirementId);
    scenarioSelect.innerHTML = `
      <option value="all">Show All Scenarios</option>
      ${requirementScenarios.map(s => `<option value="${s.id}">${escapeHTML(s.scenario_name)}</option>`).join('')}
    `;

    let activeScenarioFilter = localStorage.getItem('playwright_active_scenario_filter') || 'all';
    if (activeScenarioFilter !== 'all' && !requirementScenarios.some(s => s.id === activeScenarioFilter)) {
      activeScenarioFilter = 'all';
    }
    scenarioSelect.value = activeScenarioFilter;
    localStorage.setItem('playwright_active_scenario_filter', activeScenarioFilter);

    const approvedScenarios = requirementScenarios.filter(s => s.approved);
    const approvedScenarioIds = new Set(approvedScenarios.map(s => s.id));
    
    let approvedTestCases = this.testCases.filter(
      tc => approvedScenarioIds.has(tc.scenario_id) && tc.evaluation_status === 'approved'
    );

    if (activeScenarioFilter !== 'all') {
      approvedTestCases = approvedTestCases.filter(tc => tc.scenario_id === activeScenarioFilter);
    }

    approvedCountEl.innerText = approvedTestCases.length;

    if (!this.activePlaywrightTestCaseId) {
      const savedTcId = localStorage.getItem('playwright_active_testcase_id');
      if (savedTcId && approvedTestCases.some(t => t.id === savedTcId)) {
        this.activePlaywrightTestCaseId = savedTcId;
      }
    }

    const handlers = {
      onSelectTestCase: (id) => {
        this.activePlaywrightTestCaseId = id;
        localStorage.setItem('playwright_active_testcase_id', id);
        this.renderPlaywrightWorkspace();
      },
      onGenerateScript: async (id, btn) => {
        btn.disabled = true;
        btn.innerText = "Generating...";
        try {
          await API.generatePlaywrightScript(this.currentProject.id, id);
          this.addLog(`Playwright script generated`);
          await this.refreshProjectData();
          this.activePlaywrightTestCaseId = id;
          localStorage.setItem('playwright_active_testcase_id', id);
          this.renderPlaywrightWorkspace();
        } catch (err) {
          alert(`Script generation failed: ${err.message}`);
          btn.disabled = false;
          btn.innerText = "Generate Script";
        }
      }
    };

    listContainer.innerHTML = Components.PlaywrightApprovedCardList(approvedTestCases, this.activePlaywrightTestCaseId, handlers);

    const reqExecutions = this.executions.filter(ex => {
      const tc = this.testCases.find(t => t.id === ex.test_case_id);
      return tc && tc.scenario_id && approvedScenarioIds.has(tc.scenario_id);
    });
    executionsContainer.innerHTML = Components.PlaywrightExecutionsHistory(reqExecutions);

    scenarioSelect.onchange = (e) => {
      localStorage.setItem('playwright_active_scenario_filter', e.target.value);
      this.renderPlaywrightWorkspace();
    };

    const activeTestCase = this.testCases.find(t => t.id === this.activePlaywrightTestCaseId);
    if (!activeTestCase || !approvedTestCases.some(t => t.id === this.activePlaywrightTestCaseId)) {
      activeTitleEl.innerText = "No test case selected";
      unsavedDot.style.display = "none";
      editorActions.style.display = "none";
      editorContainer.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 20px;">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" style="width: 48px; height: 48px; margin-bottom: 12px; color: var(--border-color);"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          Select an approved test case from the left panel to load the Playwright scripting workspace.
        </div>
      `;
      return;
    }

    activeTitleEl.innerText = `playwright/${activeTestCase.title.replace(/\s+/g, '_').toLowerCase()}.spec.ts`;
    editorActions.style.display = "flex";

    const hasScript = !!activeTestCase.playwright_script;
    if (!hasScript) {
      unsavedDot.style.display = "none";
      document.getElementById('btn-playwright-save').disabled = true;
      document.getElementById('btn-playwright-run').disabled = true;
      editorContainer.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; text-align: center; padding: 40px 20px;">
          <p style="color: var(--text-secondary); margin-bottom: 20px; font-size: 0.85rem;">No Playwright script generated for this test case yet.</p>
          <button class="btn btn-primary" id="btn-workspace-generate-script">Generate Script</button>
        </div>
      `;
      document.getElementById('btn-workspace-generate-script').onclick = async () => {
        editorContainer.innerHTML = Components.Spinner("AI Agent is writing Playwright TypeScript test...");
        try {
          await API.generatePlaywrightScript(this.currentProject.id, activeTestCase.id);
          this.addLog(`Playwright script generated for '${activeTestCase.title}'`);
          await this.refreshProjectData();
          this.renderPlaywrightWorkspace();
        } catch (err) {
          alert(`Script generation failed: ${err.message}`);
          this.renderPlaywrightWorkspace();
        }
      };
      return;
    }

    editorContainer.innerHTML = `<div id="playwright-monaco-editor" style="height: 100%; min-height: 350px;"></div>`;

    const initWorkspaceMonaco = () => {
      if (window.require) {
        window.require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.39.0/min/vs' } });
        window.require(['vs/editor/editor.main'], () => {
          const isLight = document.body.classList.contains('light-theme');
          const editorEl = document.getElementById('playwright-monaco-editor');
          if (!editorEl) return;
          
          const editor = monaco.editor.create(editorEl, {
            value: activeTestCase.playwright_script,
            language: 'typescript',
            theme: isLight ? 'vs' : 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            lineNumbers: 'on',
            fontSize: 13,
            tabSize: 2
          });

          editor.onDidChangeModelContent(() => {
            const currentVal = editor.getValue();
            const hasChanged = currentVal !== activeTestCase.playwright_script;
            unsavedDot.style.display = hasChanged ? 'inline-block' : 'none';
            document.getElementById('btn-playwright-save').disabled = !hasChanged;
          });

          document.getElementById('btn-playwright-save').onclick = async () => {
            const currentVal = editor.getValue();
            try {
              document.getElementById('btn-playwright-save').disabled = true;
              await API.saveTestCaseScript(this.currentProject.id, activeTestCase.id, currentVal);
              this.addLog(`Playwright script saved for '${activeTestCase.title}'`);
              activeTestCase.playwright_script = currentVal;
              unsavedDot.style.display = 'none';
              await this.refreshProjectData();
              this.renderPlaywrightWorkspace();
            } catch (err) {
              alert(`Failed to save: ${err.message}`);
              document.getElementById('btn-playwright-save').disabled = false;
            }
          };

          document.getElementById('btn-playwright-run').onclick = async () => {
            if (editor.getValue() !== activeTestCase.playwright_script) {
              alert("Please save your changes before running the test.");
              return;
            }
            try {
              document.getElementById('btn-playwright-run').disabled = true;
              const res = await API.executeTestCase(this.currentProject.id, activeTestCase.id);
              if (res && res.execution_id) {
                window.location.hash = `#/execution/${res.execution_id}`;
              } else {
                alert("Execution started but no execution ID was returned");
                document.getElementById('btn-playwright-run').disabled = false;
              }
            } catch (err) {
              alert(`Failed to start execution: ${err.message}`);
              document.getElementById('btn-playwright-run').disabled = false;
            }
          };

          this.activeMonacoEditor = editor;
        });
      } else {
        editorContainer.innerHTML = `<textarea id="script-textarea-fallback" class="form-control" style="font-family: monospace; font-size: 0.85rem; height: 100%; width: 100%;">${escapeHTML(activeTestCase.playwright_script)}</textarea>`;
      }
    };

    setTimeout(initWorkspaceMonaco, 100);
  }

  // Playwright script viewer Workspace
  openPlaywrightScriptWorkspace(testCaseId) {
    this.activePlaywrightTestCaseId = testCaseId;
    localStorage.setItem('playwright_active_testcase_id', testCaseId);
    this.navigateTo('playwright');
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
          <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 0.85rem; color: var(--text-secondary); font-family: monospace;">playwright/test.spec.ts</span>
            <span id="script-unsaved-dot" style="width: 8px; height: 8px; border-radius: 50%; background-color: var(--color-warning); display: none;" title="Unsaved changes"></span>
          </div>
          <div class="gap-12">
            <button class="btn btn-secondary" id="btn-script-save" disabled>Save Script</button>
            <button class="btn btn-secondary" id="btn-script-copy">Copy Code</button>
            <button class="btn btn-secondary" id="btn-script-regenerate">Re-generate</button>
            <button class="btn btn-primary" id="btn-script-run">Run Playwright Test</button>
          </div>
        </div>
        
        <div id="monaco-editor-container" style="height: 400px; border: 1px solid var(--border-color); border-radius: var(--border-radius-md); overflow: hidden; background-color: var(--bg-primary);"></div>
      </div>
    `;

    const initMonaco = () => {
      if (window.require) {
        window.require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.39.0/min/vs' } });
        window.require(['vs/editor/editor.main'], () => {
          const isLight = document.body.classList.contains('light-theme');
          const editor = monaco.editor.create(document.getElementById('monaco-editor-container'), {
            value: tc.playwright_script,
            language: 'typescript',
            theme: isLight ? 'vs' : 'vs-dark',
            automaticLayout: true,
            minimap: { enabled: false },
            lineNumbers: 'on',
            fontSize: 13,
            tabSize: 2
          });

          editor.onDidChangeModelContent(() => {
            const currentVal = editor.getValue();
            const hasChanged = currentVal !== tc.playwright_script;
            document.getElementById('script-unsaved-dot').style.display = hasChanged ? 'block' : 'none';
            document.getElementById('btn-script-save').disabled = !hasChanged;
          });

          document.getElementById('btn-script-save').onclick = async () => {
            const currentVal = editor.getValue();
            try {
              document.getElementById('btn-script-save').disabled = true;
              await API.saveTestCaseScript(this.currentProject.id, tc.id, currentVal);
              this.addLog(`Playwright script saved for '${tc.title}'`);
              tc.playwright_script = currentVal;
              document.getElementById('script-unsaved-dot').style.display = 'none';
              await this.refreshProjectData();
            } catch (err) {
              alert(`Failed to save: ${err.message}`);
              document.getElementById('btn-script-save').disabled = false;
            }
          };

          document.getElementById('btn-script-copy').onclick = () => {
            navigator.clipboard.writeText(editor.getValue());
            alert("Script copied to clipboard");
          };

          document.getElementById('btn-script-regenerate').onclick = async () => {
            if (editor.getValue() !== tc.playwright_script) {
              if (!confirm("You have unsaved changes. Are you sure you want to regenerate and overwrite your changes?")) return;
            }
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

          document.getElementById('btn-script-run').onclick = async () => {
            if (editor.getValue() !== tc.playwright_script) {
              alert("Please save your changes before running the test.");
              return;
            }
            try {
              document.getElementById('btn-script-run').disabled = true;
              this.closeModal('script-workspace-modal');
              const res = await API.executeTestCase(this.currentProject.id, tc.id);
              if (res && res.execution_id) {
                window.location.hash = `#/execution/${res.execution_id}`;
              } else {
                alert("Execution started but no execution ID was returned");
              }
            } catch (err) {
              alert(`Failed to start execution: ${err.message}`);
              document.getElementById('btn-script-run').disabled = false;
            }
          };

          this.activeMonacoEditor = editor;
        });
      } else {
        container.innerHTML = `<textarea id="script-textarea-fallback" class="form-control" style="font-family: monospace; font-size: 0.85rem; height: 400px; width: 100%;">${escapeHTML(tc.playwright_script)}</textarea>`;
      }
    };

    setTimeout(initMonaco, 100);
  }

  // Execution Workspace routing observer
  async handleRouting() {
    const hash = window.location.hash;
    const executionMatch = hash.match(/^#\/execution\/([a-f0-9\-]{36})/i);
    
    if (executionMatch) {
      const executionId = executionMatch[1];
      await this.showExecutionObserverWorkspace(executionId);
    } else {
      const view = hash.replace('#/', '') || 'dashboard';
      if (['dashboard', 'requirements', 'scenarios', 'scenario-approval', 'testcases', 'testcase-approval', 'playwright', 'executions', 'reports', 'langsmith', 'settings'].includes(view)) {
        this.navigateTo(view);
      }
    }
  }

  async showExecutionObserverWorkspace(executionId) {
    if (!this.currentProject) {
      this.showProjectStartScreen();
      return;
    }

    document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));
    const obsPanel = document.getElementById('execution-workspace-view');
    if (obsPanel) obsPanel.classList.add('active');

    document.querySelectorAll('.nav-item').forEach(item => {
      if (item.getAttribute('data-view') === 'executions') {
        item.classList.add('active');
      } else {
        item.classList.remove('active');
      }
    });

    const body = document.getElementById('execution-observer-body');
    body.innerHTML = Components.Spinner("Loading execution observer panels...");

    try {
      const data = await API.getExecutionDetail(this.currentProject.id, executionId);
      const result = data.execution;
      
      const timelineHtml = (data.timeline && data.timeline.length > 0)
        ? data.timeline.map(item => `
            <div class="timeline-item completed">
              <div class="timeline-icon">✓</div>
              <div class="timeline-content">
                <div class="timeline-title">${escapeHTML(item.title)}</div>
              </div>
            </div>
          `).join('')
        : `
            <div class="timeline-item active">
              <div class="timeline-icon">➔</div>
              <div class="timeline-content">
                <div class="timeline-title">Starting execution...</div>
              </div>
            </div>
          `;

      body.innerHTML = `
        <div class="exec-workspace-grid">
          <!-- Timeline panel -->
          <div class="panel timeline-panel">
            <h3>Timeline</h3>
            <div class="timeline" id="obs-timeline-list">
              ${timelineHtml}
            </div>
          </div>
          
          <!-- Live Browser panel -->
          <div class="panel browser-panel">
            <h3>Live Browser View</h3>
            <div class="browser-mockup" style="border: 1px solid var(--border-color); border-radius: var(--border-radius-md); overflow: hidden; background-color: var(--bg-tertiary); display: flex; flex-direction: column; height: 100%;">
              <div class="browser-header" style="background-color: var(--bg-tertiary); padding: 8px 12px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; gap: 8px;">
                <div style="display: flex; gap: 6px;">
                  <span style="width: 10px; height: 10px; border-radius: 50%; background-color: #ef4444; display: inline-block;"></span>
                  <span style="width: 10px; height: 10px; border-radius: 50%; background-color: #eab308; display: inline-block;"></span>
                  <span style="width: 10px; height: 10px; border-radius: 50%; background-color: #22c55e; display: inline-block;"></span>
                </div>
                <div style="flex-grow: 1; text-align: center; font-size: 0.75rem; background-color: var(--bg-primary); color: var(--text-secondary); border-radius: 4px; padding: 2px 10px; font-family: monospace; max-width: 400px; margin: 0 auto; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                  ${escapeHTML(this.settings?.playwright?.base_url || 'https://sampleapp.tricentis.com/101/app.php')}
                </div>
              </div>
              <div class="obs-browser-screen" id="obs-browser-screen" style="flex-grow: 1; display: flex; align-items: center; justify-content: center; background-color: #020617; overflow: hidden; position: relative; min-height: 300px;">
                ${result.screenshot_path ? `
                  <img style="max-width: 100%; max-height: 100%; object-fit: contain;" src="/api/v1/projects/${this.currentProject.id}/executions/${executionId}/screenshot?path=${encodeURIComponent(result.screenshot_path)}" />
                ` : `
                  <span style="color: var(--text-muted); font-size: 0.85rem;">No screenshot captured.</span>
                `}
              </div>
            </div>
          </div>
          
          <!-- Console logs panel -->
          <div class="panel console-panel">
            <h3>Console Logs</h3>
            <div class="obs-console-logs" id="obs-console-logs">${escapeHTML(data.logs.join('\n') || 'No console logs available.')}</div>
          </div>
          
          <!-- Details panel -->
          <div class="panel details-panel">
            <h3>Execution Details</h3>
            <div style="font-size: 0.85rem; color: var(--text-secondary); display: flex; flex-direction: column; gap: 8px;">
              <div><strong>Execution ID:</strong> <span style="font-family: monospace;">${escapeHTML(result.id)}</span></div>
              <div><strong>Test Case ID:</strong> <span style="font-family: monospace;">${escapeHTML(result.test_case_id)}</span></div>
              <div><strong>Status:</strong> <span class="badge ${result.status === 'passed' ? 'badge-approved' : 'badge-rejected'}">${escapeHTML(result.status)}</span></div>
              <div><strong>Duration:</strong> ${result.duration_seconds.toFixed(2)} seconds</div>
              <div><strong>Executed At:</strong> ${new Date(result.executed_at).toLocaleString()}</div>
            </div>
          </div>
          
          <!-- Artifacts panel -->
          <div class="panel artifacts-panel">
            <h3>Artifacts & Reports</h3>
            <div style="display: flex; flex-wrap: wrap; gap: 16px;" id="obs-artifacts-list">
              ${result.screenshot_path ? `
                <a class="btn btn-secondary" style="font-size: 0.8rem; display: flex; align-items: center; gap: 8px;" href="/api/v1/projects/${this.currentProject.id}/executions/${executionId}/screenshot?path=${encodeURIComponent(result.screenshot_path)}" target="_blank">
                  📷 Screenshot
                </a>
              ` : ''}
              ${result.video_path ? `
                <a class="btn btn-secondary" style="font-size: 0.8rem; display: flex; align-items: center; gap: 8px;" href="/api/v1/projects/${this.currentProject.id}/executions/${executionId}/video?path=${encodeURIComponent(result.video_path)}" target="_blank">
                  🎥 Video Capture
                </a>
              ` : ''}
              ${result.trace_path ? `
                <a class="btn btn-secondary" style="font-size: 0.8rem; display: flex; align-items: center; gap: 8px;" href="/api/v1/projects/${this.currentProject.id}/executions/${executionId}/trace?path=${encodeURIComponent(result.trace_path)}" download>
                  🔍 Trace ZIP
                </a>
              ` : ''}
              ${data.report && data.report.pdf_path ? `
                <a class="btn btn-secondary" style="font-size: 0.8rem; display: flex; align-items: center; gap: 8px;" href="/api/v1/projects/${this.currentProject.id}/executions/${executionId}/pdf" download>
                  📄 PDF Report
                </a>
              ` : ''}
              ${data.report && data.report.html_path ? `
                <a class="btn btn-secondary" style="font-size: 0.8rem; display: flex; align-items: center; gap: 8px;" href="/api/v1/projects/${this.currentProject.id}/executions/${executionId}/html" target="_blank">
                  🌐 HTML Report
                </a>
              ` : ''}
              ${data.report && data.report.junit_path ? `
                <a class="btn btn-secondary" style="font-size: 0.8rem; display: flex; align-items: center; gap: 8px;" href="/api/v1/projects/${this.currentProject.id}/executions/${executionId}/junit" download>
                  🧪 JUnit XML
                </a>
              ` : ''}
            </div>
          </div>
        </div>
      `;

      if (result.status === 'pending') {
        const streamUrl = `${API_BASE}/projects/${this.currentProject.id}/testcases/${result.test_case_id}/execution-stream`;
        if (this.activeExecutionStream) {
          this.activeExecutionStream.close();
        }
        
        const stream = new EventSource(streamUrl);
        this.activeExecutionStream = stream;
        
        const consoleEl = document.getElementById('obs-console-logs');
        const browserEl = document.getElementById('obs-browser-screen');
        const timelineList = document.getElementById('obs-timeline-list');
        
        stream.onmessage = (e) => {
          const ev = JSON.parse(e.data);
          if (ev.log) {
            consoleEl.textContent += '\n' + ev.log;
            consoleEl.scrollTop = consoleEl.scrollHeight;
          }
          if (ev.timeline) {
            this.addLog(`Execution update: ${ev.timeline}`);
            if (timelineList) {
              const newItem = document.createElement('div');
              newItem.className = 'timeline-item completed';
              newItem.innerHTML = `
                <div class="timeline-icon">✓</div>
                <div class="timeline-content">
                  <div class="timeline-title">${escapeHTML(ev.timeline)}</div>
                </div>
              `;
              timelineList.appendChild(newItem);
              timelineList.scrollTop = timelineList.scrollHeight;
            }
          }
          if (ev.screenshot) {
            browserEl.innerHTML = `<img style="max-width: 100%; max-height: 100%; object-fit: contain;" src="/api/v1/projects/${this.currentProject.id}/executions/${executionId}/screenshot?path=${encodeURIComponent(ev.screenshot)}" />`;
          }
          if (ev.status === 'Completed' || ev.status === 'Failed' || ev.status === 'Error') {
            stream.close();
            this.refreshProjectData();
            setTimeout(() => this.showExecutionObserverWorkspace(executionId), 1500);
          }
        };

        stream.onerror = () => {
          stream.close();
        };
      }
    } catch (err) {
      body.innerHTML = Components.EmptyState("Execution Not Found", `Unable to load execution details: ${err.message}`);
    }
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

    const dropzone = document.getElementById('kb-dropzone');
    if (!dropzone) return;

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
      container.innerHTML = Components.EmptyState("No Execution Reports", "No executions have occurred yet. Run scripts to compile JUnit, HTML, and JSON reports.");
      return;
    }

    const runTotal = this.executions.length;
    const passed = this.executions.filter(ex => ex.status === 'passed').length;
    const failed = this.executions.filter(ex => ex.status === 'failed').length;
    const errors = this.executions.filter(ex => ex.status === 'error').length;
    const skipped = this.executions.filter(ex => ex.status === 'skipped').length;
    
    let totalSecs = 0;
    this.executions.forEach(ex => totalSecs += ex.duration_seconds);
    const avgDuration = runTotal > 0 ? (totalSecs / runTotal).toFixed(2) : "0";

    const passPct = Math.round((passed / runTotal) * 100);

    const optionsHtml = this.executions.map(ex => {
      const date = new Date(ex.executed_at).toLocaleString();
      return `<option value="${ex.id}">${escapeHTML(date)} - Status: ${escapeHTML(ex.status)}</option>`;
    }).join('');

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
        <div style="margin-bottom: 20px; max-width: 400px;" class="form-group">
          <label for="report-execution-select">Select Execution Run</label>
          <select id="report-execution-select" class="form-control">
            ${optionsHtml}
          </select>
        </div>
        <div style="display: flex; gap: 16px; margin-top: 12px;">
          <button class="btn btn-primary" id="btn-dl-report-pdf">Download PDF Report</button>
          <button class="btn btn-secondary" id="btn-dl-report-html">View HTML Report</button>
          <button class="btn btn-secondary" id="btn-dl-report-junit">Download JUnit XML</button>
        </div>
      </div>
    `;

    const getSelectedExecId = () => document.getElementById('report-execution-select').value;

    document.getElementById('btn-dl-report-pdf').onclick = () => {
      const id = getSelectedExecId();
      if (!id) return alert("Select an execution");
      window.open(`/api/v1/projects/${this.currentProject.id}/executions/${id}/pdf`, '_blank');
    };

    document.getElementById('btn-dl-report-html').onclick = () => {
      const id = getSelectedExecId();
      if (!id) return alert("Select an execution");
      window.open(`/api/v1/projects/${this.currentProject.id}/executions/${id}/html`, '_blank');
    };

    document.getElementById('btn-dl-report-junit').onclick = () => {
      const id = getSelectedExecId();
      if (!id) return alert("Select an execution");
      window.open(`/api/v1/projects/${this.currentProject.id}/executions/${id}/junit`, '_blank');
    };
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
