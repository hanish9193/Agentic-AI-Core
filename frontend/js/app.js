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
      
      // Ensure selectedRequirementId is valid for the current project, otherwise reset it
      if (this.selectedRequirementId && !this.requirements.some(r => r.id === this.selectedRequirementId)) {
        this.selectedRequirementId = null;
      }
      // Default to the first requirement if none is selected
      if (this.requirements.length > 0 && !this.selectedRequirementId) {
        this.selectedRequirementId = this.requirements[0].id;
      }

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
    const btn = document.getElementById('btn-launch-playwright-workspace');
    if (btn) {
      btn.onclick = () => {
        const wsUrl = this.settings?.playwright?.workspace_url || 'http://localhost:3000';
        const url = `${wsUrl}/?project_id=${this.currentProject?.id || ''}`;
        window.open(url, '_blank');
      };
    }
  }

  // Playwright script viewer Workspace
  openPlaywrightScriptWorkspace(testCaseId) {
    const wsUrl = this.settings?.playwright?.workspace_url || 'http://localhost:3000';
    const url = `${wsUrl}/?project_id=${this.currentProject?.id || ''}&test_case_id=${testCaseId}`;
    window.open(url, '_blank');
  }

  async handleRouting() {
    const hash = window.location.hash;
    const view = hash.replace('#/', '') || 'dashboard';
    if (['dashboard', 'requirements', 'scenarios', 'scenario-approval', 'testcases', 'testcase-approval', 'playwright', 'executions', 'reports', 'langsmith', 'settings'].includes(view)) {
      this.navigateTo(view);
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
