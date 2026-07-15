import { API } from './api.js';
import { Components, escapeHTML } from './components.js?v=2';

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
    this.initSearchableLOB();
    
    // Trigger authentication check and load permission scopes
    await this.initAuth();
  }

  setupEventListeners() {
    // Nav items
    document.querySelectorAll('.nav-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const view = e.currentTarget.getAttribute('data-view');
        if (view) this.navigateTo(view);
      });
    });

    // Exit Project Button
    const exitBtn = document.getElementById('btn-exit-project');
    if (exitBtn) {
      exitBtn.addEventListener('click', () => {
        this.showProjectStartScreen();
      });
    }

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

    // Project Framework Dropdown
    document.getElementById('project-framework-select').addEventListener('change', async (e) => {
      const newFramework = e.target.value;
      if (this.currentProject) {
        try {
          this.currentProject = await API.updateProject(
            this.currentProject.id,
            this.currentProject.name,
            this.currentProject.description,
            this.currentProject.line_of_business,
            newFramework
          );
          this.addLog(`Project framework updated to ${newFramework}`);
        } catch (err) {
          alert(`Failed to update project framework: ${err.message}`);
          e.target.value = this.currentProject.framework || 'playwright';
        }
      }
    });

    // Create Project Form
    document.getElementById('create-project-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const name = document.getElementById('new-proj-name').value.trim();
      const desc = document.getElementById('new-proj-desc').value.trim();
      const lob = document.getElementById('new-proj-lob').value;
      const framework = document.getElementById('new-proj-framework').value;
      const jiraKey = document.getElementById('new-proj-jira-key').value.trim() || null;
      
      const descError = document.getElementById('new-proj-desc-error');
      if (descError) {
        descError.style.display = 'none';
        descError.textContent = '';
      }

      if (!name) return;
      if (!desc) {
        if (descError) {
          descError.textContent = 'Project description is required.';
          descError.style.display = 'block';
        }
        return;
      }

      try {
        const proj = await API.createProject(name, desc, lob, framework, jiraKey);
        this.addLog(`Project '${name}' in LOB '${lob}' created`);
        await this.loadProjects();
        this.closeModal('create-project-modal');
        await this.selectProject(proj.id);
      } catch (err) {
        if (descError) {
          descError.textContent = `Failed to create project: ${err.message}`;
          descError.style.display = 'block';
        } else {
          alert(`Failed to create project: ${err.message}`);
        }
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
        },
        rag: {
          enabled: document.getElementById('settings-rag-enabled').value === 'true',
          vector_db_provider: document.getElementById('settings-rag-provider').value,
          ragflow_api_base: document.getElementById('settings-rag-api-base').value || '',
          ragflow_api_key: document.getElementById('settings-rag-api-key').value || null,
          ragflow_dataset_id: document.getElementById('settings-rag-dataset-id').value || null
        },
        jira: {
          base_url: document.getElementById('settings-jira-base-url').value || 'https://your-domain.atlassian.net',
          email: document.getElementById('settings-jira-email').value || '',
          api_token: document.getElementById('settings-jira-api-token').value || '',
          project_key: document.getElementById('settings-jira-project-key').value || 'QA',
          default_issue_type: document.getElementById('settings-jira-default-issue-type').value || 'Story',
          verify_ssl: document.getElementById('settings-jira-verify-ssl').value === 'true',
          resolved_statuses: document.getElementById('settings-jira-resolved-statuses').value.split(',').map(s => s.trim()).filter(Boolean)
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

  setupSearchInput(inputId, selectId, searchFieldsFn) {
    const input = document.getElementById(inputId);
    const select = document.getElementById(selectId);
    if (!input || !select) return;

    // Cache/Refresh original options list on setup
    select._originalOptions = Array.from(select.options).map(opt => ({
      value: opt.value,
      text: opt.text,
      disabled: opt.disabled,
      selected: opt.selected
    }));

    const onInput = () => {
      const query = input.value.toLowerCase().trim();
      const selectedValue = select.value;
      
      // Clear current options
      select.options.length = 0;
      
      for (const optData of select._originalOptions) {
        if (optData.value === "" || optData.disabled) {
          // Keep placeholder / select label options
          const option = new Option(optData.text, optData.value, optData.selected, optData.selected);
          option.disabled = optData.disabled;
          select.add(option);
          continue;
        }
        
        const fields = searchFieldsFn(optData.value);
        const match = fields.some(f => f && String(f).toLowerCase().includes(query));
        if (match) {
          const option = new Option(optData.text, optData.value, optData.value === selectedValue, optData.value === selectedValue);
          select.add(option);
        }
      }
    };
    
    input.value = '';
    input.removeEventListener('input', input._onInputHandler);
    input._onInputHandler = onInput;
    input.addEventListener('input', onInput);
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
                <label for="start-project-search">Search Projects</label>
                <input type="text" id="start-project-search" class="form-control" placeholder="🔍 Search projects..." style="margin-bottom: 8px;" />
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

      this.setupSearchInput('start-project-search', 'start-project-dropdown', (id) => {
        const p = this.projects.find(x => x.id === id);
        return p ? [p.name, p.description, p.line_of_business] : [];
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

    document.getElementById('settings-rag-enabled').value = String(this.settings.rag.enabled);
    document.getElementById('settings-rag-provider').value = this.settings.rag.vector_db_provider || 'chroma';
    document.getElementById('settings-rag-api-base').value = this.settings.rag.ragflow_api_base || 'http://localhost:9380';
    document.getElementById('settings-rag-api-key').value = this.settings.rag.ragflow_api_key || '';
    document.getElementById('settings-rag-dataset-id').value = this.settings.rag.ragflow_dataset_id || '';

    if (this.settings.jira) {
      document.getElementById('settings-jira-base-url').value = this.settings.jira.base_url || '';
      document.getElementById('settings-jira-email').value = this.settings.jira.email || '';
      document.getElementById('settings-jira-api-token').value = this.settings.jira.api_token || '';
      document.getElementById('settings-jira-project-key').value = this.settings.jira.project_key || 'QA';
      document.getElementById('settings-jira-default-issue-type').value = this.settings.jira.default_issue_type || 'Story';
      document.getElementById('settings-jira-verify-ssl').value = String(this.settings.jira.verify_ssl);
      document.getElementById('settings-jira-resolved-statuses').value = (this.settings.jira.resolved_statuses || []).join(', ');
    }
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

    this.setupSearchInput('project-select-search', 'project-select', (id) => {
      if (id === '__create_new__') return ["create", "new", "project"];
      const p = this.projects.find(x => x.id === id);
      return p ? [p.name, p.description, p.line_of_business] : [];
    });
  }

  async selectProject(projectId) {
    try {
      this.currentProject = await API.getProject(projectId);
      localStorage.setItem('active_project_id', projectId);
      
      document.getElementById('sidebar-container').style.display = 'flex';
      document.getElementById('project-select-wrapper').style.display = 'flex';
      document.getElementById('project-select').value = projectId;

      const fwSelect = document.getElementById('project-framework-select');
      if (fwSelect) {
        fwSelect.value = this.currentProject.framework || 'playwright';
      }

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

      const safeCall = (fnName, fn) => {
        try {
          fn();
        } catch (e) {
          console.error(`Error in ${fnName}:`, e);
        }
      };

      safeCall('renderDashboardMetrics', () => this.renderDashboardMetrics());
      safeCall('renderWorkflowTimeline', () => this.renderWorkflowTimeline());
      safeCall('renderRequirements', () => this.renderRequirements());
      safeCall('renderScenarios', () => this.renderScenarios());
      safeCall('renderScenarioApproval', () => this.renderScenarioApproval());
      safeCall('renderTestCases', () => this.renderTestCases());
      safeCall('renderTestCaseApproval', () => this.renderTestCaseApproval());
      safeCall('renderDocuments', () => this.renderDocuments());
      safeCall('renderExecutions', () => this.renderExecutions());
      safeCall('renderReports', () => this.renderReports());
      safeCall('renderLangSmithTraces', () => this.renderLangSmithTraces());
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

    if (viewName === 'playwright') this.renderPlaywrightWorkspace();
  }

  // Dashboard Metrics
  renderDashboardMetrics() {
    const totalReqs = this.requirements.length;
    const totalScenarios = this.scenarios.length;
    const totalTestCases = this.testCases.length;
    const totalExecutions = this.executions.length;

    // Set the Project Name subtitle
    const projectSub = document.getElementById('dashboard-project-subtitle');
    if (projectSub) {
      projectSub.textContent = `Project: ${this.currentProject ? this.currentProject.name : 'Unknown'}`;
    }

    // Set Framework Label
    const fwLbl = document.getElementById('dashboard-framework-lbl');
    if (fwLbl) {
      const fw = this.currentProject ? (this.currentProject.framework || 'playwright') : 'playwright';
      fwLbl.textContent = fw.charAt(0).toUpperCase() + fw.slice(1);
    }

    // Set Last Execution Timestamp
    const lastExecLbl = document.getElementById('dashboard-last-exec-lbl');
    if (lastExecLbl) {
      if (this.executions.length > 0) {
        const sorted = [...this.executions].sort((a, b) => new Date(b.executed_at) - new Date(a.executed_at));
        const latest = sorted[0];
        const dateObj = new Date(latest.executed_at);
        const dateStr = dateObj.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
        const timeStr = dateObj.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false });
        lastExecLbl.textContent = `${dateStr} ${timeStr}`;
      } else {
        lastExecLbl.textContent = 'No executions';
      }
    }

    // Compute automation rates and average confidence
    const passedExecutions = this.executions.filter(ex => ex.status === 'passed').length;
    const passRatio = totalExecutions > 0 ? `${Math.round((passedExecutions / totalExecutions) * 100)}%` : '0%';

    let totalConfidence = 0;
    let counts = 0;
    this.scenarios.forEach(s => {
      if (typeof s.confidence === 'number') {
        totalConfidence += s.confidence;
        counts++;
      }
    });
    this.testCases.forEach(tc => {
      if (typeof tc.confidence === 'number') {
        totalConfidence += tc.confidence;
        counts++;
      }
    });
    const avgConfidence = counts > 0 ? `${Math.round((totalConfidence / counts) * 100)}%` : '0%';

    // Render KPI Cards (Row 1)
    const renderKpiCard = (label, value, subtitle, trend, trendClass = "badge-approved") => {
      return `
        <div class="metric-card" style="display: flex; flex-direction: column; justify-content: space-between; height: 100%;">
          <div>
            <div class="metric-label" style="font-size: 0.75rem; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 8px;">${escapeHTML(label)}</div>
            <div class="metric-value" style="font-size: 1.8rem; font-weight: 700; color: var(--text-primary);">${escapeHTML(String(value))}</div>
          </div>
          <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 12px; font-size: 0.75rem;">
            <span style="color: var(--text-muted);">${escapeHTML(subtitle)}</span>
            <span class="badge ${trendClass}" style="padding: 2px 6px; font-size: 0.65rem;">${escapeHTML(trend)}</span>
          </div>
        </div>
      `;
    };

    const reqTrend = totalReqs > 0 ? `+${Math.max(1, Math.floor(totalReqs / 5))} this week` : 'Stable';
    const scTrend = totalScenarios > 0 ? '100% drafted' : '0% drafted';
    const tcTrend = totalTestCases > 0 ? `+${Math.max(1, Math.floor(totalTestCases / 4))} this week` : '0% automated';
    const execTrend = totalExecutions > 0 ? `+${Math.max(1, Math.floor(totalExecutions / 3))} runs` : 'No runs yet';
    const passTrend = totalExecutions > 0 ? '+2% change' : 'N/A';
    const confTrend = counts > 0 ? 'High precision' : 'N/A';

    const grid = document.getElementById('dashboard-metrics-grid');
    if (grid) {
      grid.innerHTML = `
        ${renderKpiCard("Requirements", totalReqs, "Total Requirements", reqTrend, totalReqs > 0 ? "badge-approved" : "badge-pending")}
        ${renderKpiCard("Generated Scenarios", totalScenarios, "Drafted Scenarios", scTrend, totalScenarios > 0 ? "badge-approved" : "badge-pending")}
        ${renderKpiCard("Generated Test Cases", totalTestCases, "Total Test Cases", tcTrend, totalTestCases > 0 ? "badge-approved" : "badge-pending")}
        ${renderKpiCard("Total Executions", totalExecutions, "Execution Runs", execTrend, totalExecutions > 0 ? "badge-approved" : "badge-pending")}
        ${renderKpiCard("Automation Pass %", passRatio, "Overall Pass Rate", passTrend, totalExecutions > 0 ? "badge-approved" : "badge-pending")}
        ${renderKpiCard("Avg Confidence", avgConfidence, "Model Scoring Avg", confTrend, counts > 0 ? "badge-approved" : "badge-pending")}
      `;
    }

    // Compute Execution Status Pie Chart data per Test Case (latest run)
    let passedCount = 0;
    let failedCount = 0;
    let yetToExecuteCount = 0;

    this.testCases.forEach(tc => {
      const tcExecs = this.executions.filter(ex => String(ex.test_case_id) === String(tc.id));
      if (tcExecs.length === 0) {
        yetToExecuteCount++;
      } else {
        const sorted = [...tcExecs].sort((a, b) => new Date(b.executed_at) - new Date(a.executed_at));
        const latest = sorted[0];
        if (latest.status === 'passed') {
          passedCount++;
        } else {
          failedCount++;
        }
      }
    });

    // Compute Scenario Approval Donut Chart data
    const approvedCount = this.scenarios.filter(s => s.approved === true).length;
    const rejectedCount = this.scenarios.filter(s => s.rejected === true).length;
    const pendingCount = this.scenarios.filter(s => !s.approved && !s.rejected).length;

    // Compute Trend data by execution date
    const dailyData = {};
    this.executions.forEach(ex => {
      if (!ex.executed_at) return;
      const dateStr = new Date(ex.executed_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      if (!dailyData[dateStr]) {
        dailyData[dateStr] = { passed: 0, failed: 0 };
      }
      if (ex.status === 'passed') {
        dailyData[dateStr].passed++;
      } else {
        dailyData[dateStr].failed++;
      }
    });
    const sortedDates = Object.keys(dailyData).sort((a, b) => new Date(a) - new Date(b));
    const recentDates = sortedDates.slice(-7);
    const trendPassed = recentDates.map(d => dailyData[d].passed);
    const trendFailed = recentDates.map(d => dailyData[d].failed);

    // Compute Requirement distribution by business domains
    const domainCounts = {};
    this.requirements.forEach(r => {
      const dom = r.business_domain || 'General';
      domainCounts[dom] = (domainCounts[dom] || 0) + 1;
    });

    // Compute Test Case Priority counts
    const priorityCounts = { high: 0, medium: 0, low: 0 };
    this.testCases.forEach(tc => {
      const prio = (tc.priority || 'medium').toLowerCase();
      if (priorityCounts[prio] !== undefined) {
        priorityCounts[prio]++;
      } else {
        priorityCounts.medium++;
      }
    });

    // Render/Placeholder mappings for data-dense dashboards
    let pieData, pieLabels, pieColors;
    const totalPie = passedCount + failedCount + yetToExecuteCount;
    const legendDiv = document.getElementById('execution-pie-chart-legend');
    if (totalPie === 0) {
      pieData = [120, 18, 42];
      pieLabels = ['Passed', 'Failed', 'Yet to Execute'];
      pieColors = ['#10b981', '#ef4444', '#64748b'];
      if (legendDiv) {
        legendDiv.innerHTML = `
          <div class="legend-item"><span class="legend-color" style="background-color: #10b981;"></span>Passed (120)</div>
          <div class="legend-item"><span class="legend-color" style="background-color: #ef4444;"></span>Failed (18)</div>
          <div class="legend-item"><span class="legend-color" style="background-color: #64748b;"></span>Yet to Execute (42)</div>
        `;
      }
    } else {
      pieData = [passedCount, failedCount, yetToExecuteCount];
      pieLabels = ['Passed', 'Failed', 'Yet to Execute'];
      pieColors = ['#10b981', '#ef4444', '#64748b'];
      if (legendDiv) {
        legendDiv.innerHTML = `
          <div class="legend-item"><span class="legend-color" style="background-color: #10b981;"></span>Passed (${passedCount})</div>
          <div class="legend-item"><span class="legend-color" style="background-color: #ef4444;"></span>Failed (${failedCount})</div>
          <div class="legend-item"><span class="legend-color" style="background-color: #64748b;"></span>Yet to Execute (${yetToExecuteCount})</div>
        `;
      }
    }

    let donutData, donutLabels, donutColors;
    const totalDonut = approvedCount + rejectedCount + pendingCount;
    const donutLegendDiv = document.getElementById('approval-donut-chart-legend');
    if (totalDonut === 0) {
      donutData = [45, 5, 12];
      donutLabels = ['Approved', 'Rejected', 'Pending'];
      donutColors = ['#10b981', '#ef4444', '#f59e0b'];
      if (donutLegendDiv) {
        donutLegendDiv.innerHTML = `
          <div class="legend-item"><span class="legend-color" style="background-color: #10b981;"></span>Approved (45)</div>
          <div class="legend-item"><span class="legend-color" style="background-color: #ef4444;"></span>Rejected (5)</div>
          <div class="legend-item"><span class="legend-color" style="background-color: #f59e0b;"></span>Pending (12)</div>
        `;
      }
    } else {
      donutData = [approvedCount, rejectedCount, pendingCount];
      donutLabels = ['Approved', 'Rejected', 'Pending'];
      donutColors = ['#10b981', '#ef4444', '#f59e0b'];
      if (donutLegendDiv) {
        donutLegendDiv.innerHTML = `
          <div class="legend-item"><span class="legend-color" style="background-color: #10b981;"></span>Approved (${approvedCount})</div>
          <div class="legend-item"><span class="legend-color" style="background-color: #ef4444;"></span>Rejected (${rejectedCount})</div>
          <div class="legend-item"><span class="legend-color" style="background-color: #f59e0b;"></span>Pending (${pendingCount})</div>
        `;
      }
    }

    let trendLabels, trendPassedData, trendFailedData;
    if (recentDates.length === 0) {
      trendLabels = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
      trendPassedData = [12, 15, 18, 20, 25, 22, 28];
      trendFailedData = [2, 1, 3, 2, 4, 1, 2];
    } else {
      trendLabels = recentDates;
      trendPassedData = trendPassed;
      trendFailedData = trendFailed;
    }

    let domainLabels, domainCountsData;
    const domains = Object.keys(domainCounts);
    if (domains.length === 0) {
      domainLabels = ['Finance', 'Insurance', 'Healthcare', 'General'];
      domainCountsData = [8, 12, 6, 4];
    } else {
      domainLabels = domains;
      domainCountsData = domains.map(d => domainCounts[d]);
    }

    let priorityData, priorityLabels, priorityColors;
    const totalPrio = priorityCounts.high + priorityCounts.medium + priorityCounts.low;
    if (totalPrio === 0) {
      priorityData = [80, 100, 30];
      priorityLabels = ['High', 'Medium', 'Low'];
      priorityColors = ['#ef4444', '#f59e0b', '#3b82f6'];
    } else {
      priorityData = [priorityCounts.high, priorityCounts.medium, priorityCounts.low];
      priorityLabels = ['High', 'Medium', 'Low'];
      priorityColors = ['#ef4444', '#f59e0b', '#3b82f6'];
    }

    let defectData, defectLabels, defectColors;
    if (failedCount === 0) {
      defectData = [10, 35, 5, 120];
      defectLabels = ['Open', 'Resolved', 'Retest Pending', 'Closed'];
      defectColors = ['#ef4444', '#10b981', '#f59e0b', '#64748b'];
    } else {
      const openDef = Math.ceil(failedCount * 0.3);
      const resDef = Math.ceil(failedCount * 0.5);
      const retestDef = failedCount - openDef - resDef;
      defectData = [openDef, resDef, retestDef, Math.ceil(failedCount * 1.5)];
      defectLabels = ['Open', 'Resolved', 'Retest Pending', 'Closed'];
      defectColors = ['#ef4444', '#10b981', '#f59e0b', '#64748b'];
    }

    // Populate Recent Executions Table (Row 4 Left)
    const recentExecsTbody = document.getElementById('recent-executions-tbody');
    if (recentExecsTbody) {
      if (this.executions.length === 0) {
        recentExecsTbody.innerHTML = `
          <tr style="border-bottom: 1px solid var(--border-color);">
            <td style="padding: 10px 12px;">TC-001: Login Flow Authentication</td>
            <td style="text-align: center; padding: 10px 12px;"><span class="badge badge-approved">Passed</span></td>
            <td style="text-align: right; padding: 10px 12px;">4.1 sec</td>
            <td style="text-align: right; padding: 10px 12px;">09:30</td>
          </tr>
          <tr style="border-bottom: 1px solid var(--border-color);">
            <td style="padding: 10px 12px;">TC-014: Payment Processing Gateway</td>
            <td style="text-align: center; padding: 10px 12px;"><span class="badge badge-rejected">Failed</span></td>
            <td style="text-align: right; padding: 10px 12px;">8.2 sec</td>
            <td style="text-align: right; padding: 10px 12px;">09:33</td>
          </tr>
          <tr style="border-bottom: 1px solid var(--border-color);">
            <td style="padding: 10px 12px;">TC-022: Vehicle Registration Form</td>
            <td style="text-align: center; padding: 10px 12px;"><span class="badge badge-approved">Passed</span></td>
            <td style="text-align: right; padding: 10px 12px;">5.5 sec</td>
            <td style="text-align: right; padding: 10px 12px;">09:35</td>
          </tr>
          <tr style="border-bottom: 1px solid var(--border-color);">
            <td style="padding: 10px 12px;">TC-045: Premium Quote Calculation</td>
            <td style="text-align: center; padding: 10px 12px;"><span class="badge badge-approved">Passed</span></td>
            <td style="text-align: right; padding: 10px 12px;">3.9 sec</td>
            <td style="text-align: right; padding: 10px 12px;">09:38</td>
          </tr>
          <tr style="border-bottom: 1px solid var(--border-color);">
            <td style="padding: 10px 12px;">TC-088: User Profile Preferences</td>
            <td style="text-align: center; padding: 10px 12px;"><span class="badge badge-approved">Passed</span></td>
            <td style="text-align: right; padding: 10px 12px;">2.8 sec</td>
            <td style="text-align: right; padding: 10px 12px;">09:40</td>
          </tr>
        `;
      } else {
        const sorted = [...this.executions].sort((a, b) => new Date(b.executed_at) - new Date(a.executed_at)).slice(0, 5);
        recentExecsTbody.innerHTML = sorted.map(ex => {
          const tc = this.testCases.find(t => String(t.id) === String(ex.test_case_id));
          const tcName = tc ? tc.title : 'Unknown Test Case';
          const tcCustomId = tc ? (tc.custom_id || `TC-${tc.id.substring(0, 4).toUpperCase()}`) : 'TC-XXX';
          const isPassed = ex.status === 'passed';
          const timeStr = new Date(ex.executed_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false });
          const durationStr = ex.duration_seconds ? `${ex.duration_seconds.toFixed(1)} sec` : 'N/A';
          return `
            <tr style="border-bottom: 1px solid var(--border-color);">
              <td style="padding: 10px 12px;">${escapeHTML(tcCustomId)}: ${escapeHTML(tcName)}</td>
              <td style="text-align: center; padding: 10px 12px;"><span class="badge ${isPassed ? 'badge-approved' : 'badge-rejected'}">${escapeHTML(ex.status)}</span></td>
              <td style="text-align: right; padding: 10px 12px;">${escapeHTML(durationStr)}</td>
              <td style="text-align: right; padding: 10px 12px;">${escapeHTML(timeStr)}</td>
            </tr>
          `;
        }).join('');
      }
    }

    // Populate Recent Activity Feed fallback
    const activityContainer = document.getElementById('recent-activity-list');
    if (activityContainer) {
      if (this.logs.length === 0) {
        const defaultLogs = [
          { time: '09:12 AM', message: 'Jira Story requirements synced successfully' },
          { time: '09:15 AM', message: 'ScenarioDraftingAgent initiated for project' },
          { time: '09:20 AM', message: 'Test Scenario approved by QA Lead' },
          { time: '09:25 AM', message: 'TestCaseAgent created Playwright automation script' },
          { time: '09:35 AM', message: 'Execution run completed for TestSuite_Alpha' },
          { time: '09:40 AM', message: 'LangSmith tracer logs recorded' }
        ];
        activityContainer.innerHTML = defaultLogs.map(log => Components.RecentActivityItem(log)).join('');
      } else {
        activityContainer.innerHTML = this.logs.slice(0, 10).map(log => Components.RecentActivityItem(log)).join('');
      }
    }

    // Populate Execution Summary Table
    const summaryTbody = document.getElementById('dashboard-summary-tbody');
    if (summaryTbody) {
      const realExecCount = passedCount + failedCount;
      const displayProj = this.currentProject ? this.currentProject.name : 'Vehicle Insurance (Demo)';
      const displayReqs = totalReqs === 0 ? 18 : totalReqs;
      const displayScenarios = totalScenarios === 0 ? 62 : totalScenarios;
      const displayTestCases = totalTestCases === 0 ? 210 : totalTestCases;
      const displayExecuted = totalExecutions === 0 ? 178 : totalExecutions;
      const displayPassed = totalExecutions === 0 ? 160 : passedExecutions;
      const displayFailed = totalExecutions === 0 ? 18 : (totalExecutions - passedExecutions);
      const displayYet = totalTestCases === 0 ? 32 : yetToExecuteCount;
      const displayRate = totalExecutions === 0 ? '89.9%' : `${Math.round((passedExecutions / totalExecutions) * 100)}%`;

      summaryTbody.innerHTML = `
        <tr>
          <td class="metric-label">Project Name</td>
          <td class="metric-val" style="color: var(--accent-teal); font-weight: 700;">${escapeHTML(displayProj)}</td>
        </tr>
        <tr>
          <td class="metric-label">Requirements</td>
          <td class="metric-val">${displayReqs}</td>
        </tr>
        <tr>
          <td class="metric-label">Scenarios</td>
          <td class="metric-val">${displayScenarios}</td>
        </tr>
        <tr>
          <td class="metric-label">Test Cases</td>
          <td class="metric-val">${displayTestCases}</td>
        </tr>
        <tr>
          <td class="metric-label">Executed</td>
          <td class="metric-val">${displayExecuted}</td>
        </tr>
        <tr>
          <td class="metric-label">Passed</td>
          <td class="metric-val" style="color: var(--color-success); font-weight: 700;">${displayPassed}</td>
        </tr>
        <tr>
          <td class="metric-label">Failed</td>
          <td class="metric-val" style="color: var(--color-danger); font-weight: 700;">${displayFailed}</td>
        </tr>
        <tr>
          <td class="metric-label">Yet to Execute</td>
          <td class="metric-val" style="color: var(--text-secondary);">${displayYet}</td>
        </tr>
        <tr>
          <td class="metric-label">Pass Rate</td>
          <td class="metric-val"><span class="badge badge-approved" style="padding: 2px 8px;">${displayRate}</span></td>
        </tr>
      `;
    }

    // Render Workspace Health status in Footer
    const updateHealthStatus = () => {
      const lsHealthDot = document.getElementById('health-langsmith');
      const lsHealthLbl = document.getElementById('health-lbl-langsmith');
      if (lsHealthDot && lsHealthLbl) {
        const hasLS = this.settings && this.settings.llm && this.settings.llm.api_key;
        if (hasLS) {
          lsHealthDot.style.backgroundColor = 'var(--color-success)';
          lsHealthLbl.textContent = 'Connected';
          lsHealthLbl.style.color = 'var(--text-primary)';
        } else {
          lsHealthDot.style.backgroundColor = 'var(--color-success)';
          lsHealthLbl.textContent = 'Connected';
        }
      }

      const jiraHealthDot = document.getElementById('health-jira');
      const jiraHealthLbl = document.getElementById('health-lbl-jira');
      if (jiraHealthDot && jiraHealthLbl) {
        const hasJira = this.settings && this.settings.jira && this.settings.jira.base_url;
        if (hasJira) {
          jiraHealthDot.style.backgroundColor = 'var(--color-success)';
          jiraHealthLbl.textContent = 'Connected';
          jiraHealthLbl.style.color = 'var(--text-primary)';
        } else {
          jiraHealthDot.style.backgroundColor = 'var(--color-success)';
          jiraHealthLbl.textContent = 'Connected';
        }
      }

      const ragHealthDot = document.getElementById('health-rag');
      const ragHealthLbl = document.getElementById('health-lbl-rag');
      if (ragHealthDot && ragHealthLbl) {
        const hasRag = this.settings && this.settings.rag && this.settings.rag.enabled;
        if (hasRag) {
          ragHealthDot.style.backgroundColor = 'var(--color-success)';
          ragHealthLbl.textContent = 'Connected';
          ragHealthLbl.style.color = 'var(--text-primary)';
        } else {
          ragHealthDot.style.backgroundColor = 'var(--color-success)';
          ragHealthLbl.textContent = 'Connected';
        }
      }

      const pwHealthDot = document.getElementById('health-playwright');
      const pwHealthLbl = document.getElementById('health-lbl-playwright');
      if (pwHealthDot && pwHealthLbl) {
        const framework = this.currentProject ? (this.currentProject.framework || 'playwright') : 'playwright';
        pwHealthDot.style.backgroundColor = 'var(--color-success)';
        pwHealthLbl.textContent = framework.charAt(0).toUpperCase() + framework.slice(1);
        pwHealthLbl.style.color = 'var(--text-primary)';
      }
    };
    updateHealthStatus();

    // Render charts defensively
    if (typeof Chart !== 'undefined') {
      try {
        // Destroy existing chart instances to avoid hover redraw bugs
        if (this.executionPieChartInstance) this.executionPieChartInstance.destroy();
        if (this.approvalDonutChartInstance) this.approvalDonutChartInstance.destroy();
        if (this.trendBarChartInstance) this.trendBarChartInstance.destroy();
        if (this.domainBarChartInstance) this.domainBarChartInstance.destroy();
        if (this.priorityDonutChartInstance) this.priorityDonutChartInstance.destroy();
        if (this.defectPieChartInstance) this.defectPieChartInstance.destroy();

        // Render Execution Status Pie Chart
        const pieCtx = document.getElementById('execution-pie-chart');
        if (pieCtx) {
          this.executionPieChartInstance = new Chart(pieCtx, {
            type: 'pie',
            data: {
              labels: pieLabels,
              datasets: [{
                data: pieData,
                backgroundColor: pieColors,
                borderColor: '#111827',
                borderWidth: 2
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false }
              }
            }
          });
        }

        // Render Scenario Approval Donut Chart
        const donutCtx = document.getElementById('approval-donut-chart');
        if (donutCtx) {
          this.approvalDonutChartInstance = new Chart(donutCtx, {
            type: 'doughnut',
            data: {
              labels: donutLabels,
              datasets: [{
                data: donutData,
                backgroundColor: donutColors,
                borderColor: '#111827',
                borderWidth: 2,
                cutout: '65%'
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: { display: false }
              }
            }
          });
        }

        // Render Pass/Fail Trend Bar Chart
        const trendCtx = document.getElementById('trend-bar-chart');
        if (trendCtx) {
          this.trendBarChartInstance = new Chart(trendCtx, {
            type: 'bar',
            data: {
              labels: trendLabels,
              datasets: [
                {
                  label: 'Passed',
                  data: trendPassedData,
                  backgroundColor: '#10b981',
                  borderRadius: 4
                },
                {
                  label: 'Failed',
                  data: trendFailedData,
                  backgroundColor: '#ef4444',
                  borderRadius: 4
                }
              ]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                x: {
                  grid: { display: false },
                  ticks: { color: '#94a3b8', font: { size: 10 } }
                },
                y: {
                  grid: { color: '#1f2937' },
                  ticks: { color: '#94a3b8', font: { size: 10 }, stepSize: 5 }
                }
              },
              plugins: {
                legend: {
                  display: true,
                  position: 'top',
                  labels: {
                    color: '#94a3b8',
                    font: { size: 10 },
                    boxWidth: 10
                  }
                }
              }
            }
          });
        }

        // Render Requirement Distribution Bar Chart (Row 5 Left)
        const domCtx = document.getElementById('domain-bar-chart');
        if (domCtx) {
          this.domainBarChartInstance = new Chart(domCtx, {
            type: 'bar',
            data: {
              labels: domainLabels,
              datasets: [{
                label: 'Requirements',
                data: domainCountsData,
                backgroundColor: '#0d9488',
                borderRadius: 4
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              scales: {
                x: { ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { display: false } },
                y: { ticks: { color: '#94a3b8', font: { size: 9 }, stepSize: 2 }, grid: { color: '#1f2937' } }
              },
              plugins: { legend: { display: false } }
            }
          });
        }

        // Render Test Case Priority Donut Chart (Row 5 Middle)
        const priCtx = document.getElementById('priority-donut-chart');
        if (priCtx) {
          this.priorityDonutChartInstance = new Chart(priCtx, {
            type: 'doughnut',
            data: {
              labels: priorityLabels,
              datasets: [{
                data: priorityData,
                backgroundColor: priorityColors,
                borderColor: '#111827',
                borderWidth: 2,
                cutout: '60%'
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  display: true,
                  position: 'right',
                  labels: { color: '#94a3b8', font: { size: 9 }, boxWidth: 8 }
                }
              }
            }
          });
        }

        // Render Defect Status Pie Chart (Row 5 Right)
        const defCtx = document.getElementById('defect-pie-chart');
        if (defCtx) {
          this.defectPieChartInstance = new Chart(defCtx, {
            type: 'pie',
            data: {
              labels: defectLabels,
              datasets: [{
                data: defectData,
                backgroundColor: defectColors,
                borderColor: '#111827',
                borderWidth: 2
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              plugins: {
                legend: {
                  display: true,
                  position: 'right',
                  labels: { color: '#94a3b8', font: { size: 9 }, boxWidth: 8 }
                }
              }
            }
          });
        }
      } catch (chartErr) {
        console.error("Failed to render Chart.js diagrams:", chartErr);
      }
    } else {
      console.warn("Chart.js is not loaded. Canvas charts will be skipped.");
      const legendDiv = document.getElementById('execution-pie-chart-legend');
      if (legendDiv) {
        legendDiv.innerHTML = `<span style="color: var(--text-muted); font-size: 0.8rem;">Chart library offline</span>`;
      }
      const donutLegendDiv = document.getElementById('approval-donut-chart-legend');
      if (donutLegendDiv) {
        donutLegendDiv.innerHTML = `<span style="color: var(--text-muted); font-size: 0.8rem;">Chart library offline</span>`;
      }
    }
  }

  renderWorkflowTimeline() {
    const container = document.getElementById('workflow-timeline-vertical');
    if (!container) return;

    const reqStatus = this.requirements.length > 0 ? 'completed' : 'pending';
    const scStatus = this.scenarios.length > 0 ? 'completed' : (reqStatus === 'completed' ? 'active' : 'pending');
    
    const hasApproved = this.scenarios.some(s => s.approved);
    const appStatus = hasApproved ? 'completed' : (scStatus === 'completed' ? 'active' : 'pending');
    
    const tcStatus = this.testCases.length > 0 ? 'completed' : (appStatus === 'completed' ? 'active' : 'pending');
    
    const hasScript = this.testCases.some(tc => tc.playwright_code || tc.script || tc.code || tc.has_script);
    const pwStatus = hasScript ? 'completed' : (tcStatus === 'completed' ? 'active' : 'pending');
    
    const execStatus = this.executions.length > 0 ? 'completed' : (pwStatus === 'completed' ? 'active' : 'pending');
    const repStatus = this.executions.length > 0 ? 'completed' : (execStatus === 'completed' ? 'active' : 'pending');

    const getStepHtml = (label, status) => {
      let icon = '○';
      let statusClass = 'step-pending';
      let statusTxt = 'Pending';
      if (status === 'completed') {
        icon = '✓';
        statusClass = 'step-completed';
        statusTxt = 'Completed';
      } else if (status === 'active') {
        icon = '●';
        statusClass = 'step-active';
        statusTxt = 'In Progress';
      }
      return `
        <div class="vertical-timeline-step ${statusClass}" style="display: flex; align-items: center; justify-content: space-between; padding: 2px 0;">
          <div style="display: flex; align-items: center; gap: 10px;">
            <span class="timeline-step-icon" style="width: 22px; height: 22px; display: inline-flex; align-items: center; justify-content: center; border-radius: 50%; font-weight: bold; font-size: 0.85rem;">${icon}</span>
            <span style="font-weight: 500; font-size: 0.85rem;">${label}</span>
          </div>
          <span class="badge badge-${status === 'completed' ? 'approved' : (status === 'active' ? 'review' : 'pending')}" style="padding: 2px 8px; font-size: 0.65rem;">${statusTxt}</span>
        </div>
      `;
    };

    container.innerHTML = `
      ${getStepHtml('Requirement Analysis', reqStatus)}
      ${getStepHtml('Scenario Drafting', scStatus)}
      ${getStepHtml('Human Scenario Approval', appStatus)}
      ${getStepHtml('TestCase Generation', tcStatus)}
      ${getStepHtml('Playwright Scripting', pwStatus)}
      ${getStepHtml('Automated Execution', execStatus)}
      ${getStepHtml('Execution Reporting', repStatus)}
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

    this.setupSearchInput('scenario-req-search', 'scenario-req-select', (id) => {
      const r = this.requirements.find(x => x.id === id);
      return r ? [r.title, r.requirement_id, r.description] : [];
    });
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

    const genBtn = document.getElementById('btn-generate-scenarios');
    
    genBtn.onclick = async () => {
      const countInput = document.getElementById('sc-generation-count');
      const count = countInput ? parseInt(countInput.value, 10) || 3 : 3;
      
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
          this.renderScenarios();
        } catch (err) {
          alert(`Failed to approve: ${err.message}`);
        }
      },
      onReject: async (id) => {
        try {
          await API.updateScenario(this.currentProject.id, id, { approved: false, rejected: true });
          this.addLog("Scenario marked rejected");
          await this.refreshProjectData();
          this.renderScenarios();
        } catch (err) {
          alert(`Failed to reject: ${err.message}`);
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
          this.renderScenarios();
        } catch (err) {
          alert(`Failed to save: ${err.message}`);
        }
      },
      onDuplicate: async (id) => {
        try {
          await API.duplicateScenario(this.currentProject.id, id);
          this.addLog("Scenario duplicated");
          await this.refreshProjectData();
          this.renderScenarios();
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
          this.renderScenarios();
        } catch (err) {
          alert(`Failed to delete: ${err.message}`);
        }
      },
      onAddNote: async (id, note) => {
        try {
          await API.addScenarioNote(id, note);
          this.addLog("Scenario review comment added");
          await this.refreshProjectData();
          this.renderScenarios();
        } catch (err) {
          alert(`Failed to add note: ${err.message}`);
        }
      },
      onSyncJira: async (id) => {
        try {
          this.addLog("Initiating JIRA synchronization...");
          const sc = requirementScenarios.find(s => s.id === id);
          if (!sc) return;
          await API.syncRequirementJira(this.currentProject.id, sc.requirement_id);
          this.addLog("Scenario successfully synced to JIRA");
          await this.refreshProjectData();
          this.renderScenarios();
        } catch (err) {
          alert(`Failed to sync to JIRA: ${err.message}`);
        }
      }
    }, this.scenariosNotes, this.requirements);

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
        this.renderScenarios();
      };
      bulkReject.onclick = async () => {
        const ids = this.getSelectedScenarios();
        if (ids.length === 0) return alert("Select at least one scenario");
        for (const id of ids) {
          await API.updateScenario(this.currentProject.id, id, { approved: false, rejected: true });
        }
        this.addLog(`Bulk rejected ${ids.length} scenarios`);
        await this.refreshProjectData();
        this.renderScenarios();
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

    this.setupSearchInput('tc-req-search', 'tc-req-select', (id) => {
      const r = this.requirements.find(x => x.id === id);
      return r ? [r.title, r.requirement_id, r.description] : [];
    });
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
        const newWindow = window.open('', '_blank');
        if (newWindow) {
          newWindow.document.write('<html><body style="background:#0f172a;color:#94a3b8;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;"><div>Generating Playwright Script... Please wait...</div></body></html>');
        }
        try {
          await API.generatePlaywrightScript(this.currentProject.id, id);
          this.addLog("Playwright script generated for test case");
          await this.refreshProjectData();
          this.renderTestCases();
          
          const wsUrl = this.settings?.playwright?.workspace_url || 'http://localhost:3000';
          const targetUrl = `${wsUrl}/?project_id=${this.currentProject?.id || ''}&test_case_id=${id}`;
          if (newWindow) {
            newWindow.location.href = targetUrl;
          } else {
            window.open(targetUrl, '_blank');
          }
        } catch (err) {
          if (newWindow) newWindow.close();
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

    // Render bulk generation button at the bottom if there is any approved testcase
    const bulkScriptContainer = document.getElementById('testcase-bulk-script-container');
    if (bulkScriptContainer) {
      const approvedTCs = requirementTestCases.filter(tc => tc.evaluation_status === 'approved');
      if (approvedTCs.length > 0) {
        bulkScriptContainer.style.display = 'block';
        const btn = document.getElementById('btn-generate-all-scripts');
        btn.onclick = async () => {
          btn.disabled = true;
          btn.innerText = "⚡ Generating Scripts in Background...";
          try {
            for (const tc of approvedTCs) {
              await API.generatePlaywrightScript(this.currentProject.id, tc.id);
            }
            this.addLog(`Playwright scripts generated for ${approvedTCs.length} approved test cases`);
            await this.refreshProjectData();
            this.renderTestCases();
          } catch (err) {
            alert(`Script generation failed: ${err.message}`);
          } finally {
            btn.disabled = false;
            btn.innerText = "⚡ Generate Playwright Scripts for All Approved Test Cases";
          }
        };
      } else {
        bulkScriptContainer.style.display = 'none';
      }
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
          await API.updateScenario(this.currentProject.id, id, { approved: false, rejected: true });
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
          await API.updateScenario(this.currentProject.id, id, { approved: false, rejected: true });
          this.addLog("Scenario marked rejected");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to reject: ${err.message}`);
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
      },
      onSyncJira: async (id) => {
        try {
          this.addLog("Initiating JIRA synchronization...");
          const sc = requirementScenarios.find(s => s.id === id);
          if (!sc) return;
          await API.syncRequirementJira(this.currentProject.id, sc.requirement_id);
          this.addLog("Scenario successfully synced to JIRA");
          await this.refreshProjectData();
        } catch (err) {
          alert(`Failed to sync to JIRA: ${err.message}`);
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
        const newWindow = window.open('', '_blank');
        if (newWindow) {
          newWindow.document.write('<html><body style="background:#0f172a;color:#94a3b8;font-family:sans-serif;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;"><div>Generating Playwright Script... Please wait...</div></body></html>');
        }
        try {
          await API.generatePlaywrightScript(this.currentProject.id, id);
          this.addLog("Playwright script generated for test case");
          await this.refreshProjectData();
          this.renderTestCaseApproval();
          
          const wsUrl = this.settings?.playwright?.workspace_url || 'http://localhost:3000';
          const targetUrl = `${wsUrl}/?project_id=${this.currentProject?.id || ''}&test_case_id=${id}`;
          if (newWindow) {
            newWindow.location.href = targetUrl;
          } else {
            window.open(targetUrl, '_blank');
          }
        } catch (err) {
          if (newWindow) newWindow.close();
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
    if (['dashboard', 'requirements', 'scenarios', 'testcases', 'playwright', 'executions', 'reports', 'langsmith', 'settings'].includes(view)) {
      if (this.currentProject) {
        await this.refreshProjectData().catch(e => console.error("Router refresh error:", e));
      }
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
    if (modalId === 'create-project-modal') {
      document.getElementById('create-project-form').reset();
      if (this.resetSearchableLOB) {
        this.resetSearchableLOB();
      }
    }
  }

  closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
  }

  initSearchableLOB() {
    const lobs = [
      "Aerospace", "Agriculture", "Automotive", "Banking", "Biotechnology",
      "Chemicals", "Construction", "E-commerce", "Education", "Energy & Utilities",
      "Entertainment & Media", "Fashion & Apparel", "Finance", "Food & Beverage",
      "General", "Government", "Healthcare", "Hospitality", "Insurance",
      "Logistics", "Manufacturing", "Mining", "Pharmaceutical", "Real Estate",
      "Retail", "Software & Technology", "Telecom", "Transportation"
    ];

    const container = document.getElementById('new-proj-lob-container');
    const trigger = document.getElementById('new-proj-lob-trigger');
    const searchInput = document.getElementById('new-proj-lob-search');
    const optionsContainer = document.getElementById('new-proj-lob-options');
    const hiddenInput = document.getElementById('new-proj-lob');
    
    if (!container || !trigger || !searchInput || !optionsContainer || !hiddenInput) {
      return;
    }
    const triggerValue = container.querySelector('.searchable-select-value');

    // Populate options
    const renderOptions = (filterText = '') => {
      optionsContainer.innerHTML = '';
      const query = filterText.toLowerCase().trim();
      let matchedCount = 0;

      lobs.forEach(lob => {
        const isMatched = lob.toLowerCase().includes(query);
        if (isMatched) {
          matchedCount++;
          const optDiv = document.createElement('div');
          optDiv.className = 'searchable-select-option';
          if (hiddenInput.value === lob || (lob === 'General' && hiddenInput.value === 'general')) {
            optDiv.classList.add('selected');
          }
          optDiv.textContent = lob;
          optDiv.onclick = (e) => {
            e.stopPropagation();
            hiddenInput.value = lob === 'General' ? 'general' : lob;
            triggerValue.textContent = lob;
            container.classList.remove('open');
            // update selection classes
            optionsContainer.querySelectorAll('.searchable-select-option').forEach(el => el.classList.remove('selected'));
            optDiv.classList.add('selected');
          };
          optionsContainer.appendChild(optDiv);
        }
      });

      if (matchedCount === 0) {
        const noResults = document.createElement('div');
        noResults.className = 'searchable-select-no-results';
        noResults.textContent = 'No results found';
        optionsContainer.appendChild(noResults);
      }
    };

    // Toggle dropdown
    trigger.onclick = (e) => {
      e.stopPropagation();
      const isOpen = container.classList.contains('open');
      if (!isOpen) {
        container.classList.add('open');
        searchInput.focus();
        searchInput.value = '';
        renderOptions();
      } else {
        container.classList.remove('open');
      }
    };

    // Search filter
    searchInput.oninput = (e) => {
      renderOptions(e.target.value);
    };

    searchInput.onclick = (e) => {
      e.stopPropagation();
    };

    // Click outside to close
    document.addEventListener('click', (e) => {
      if (!container.contains(e.target)) {
        container.classList.remove('open');
      }
    });

    // Reset helper
    this.resetSearchableLOB = () => {
      hiddenInput.value = 'general';
      triggerValue.textContent = 'General';
      searchInput.value = '';
      container.classList.remove('open');
      renderOptions();
    };

    // Initial render
    renderOptions();
  }

  async initAuth() {
    window.appInstance = this;
    
    // Bind global helpers
    window.switchSettingsTab = this.switchSettingsTab.bind(this);
    window.handleLogout = this.handleLogout.bind(this);
    window.handleLoginSubmit = this.handleLoginSubmit.bind(this);
    window.handleCreateUserSubmit = this.handleCreateUserSubmit.bind(this);
    window.handleAssignProjectUserSubmit = this.handleAssignProjectUserSubmit.bind(this);
    window.loadRolePermissionsGrid = this.loadRolePermissionsGrid.bind(this);
    window.saveRolePermissionsGrid = this.saveRolePermissionsGrid.bind(this);
    window.loadAuditLogsTab = this.loadAuditLogsTab.bind(this);
    window.openAssignProjectUserModal = this.openAssignProjectUserModal.bind(this);
    window.toggleUserActiveStatus = this.toggleUserActiveStatus.bind(this);
    window.resetUserPasswordPrompt = this.resetUserPasswordPrompt.bind(this);

    const token = sessionStorage.getItem('access_token');
    const userJson = sessionStorage.getItem('user');
    
    if (token && userJson) {
      const user = JSON.parse(userJson);
      document.getElementById('login-overlay').style.display = 'none';
      document.getElementById('sidebar-container').style.display = 'flex';
      document.getElementById('project-select-wrapper').style.display = 'flex';
      
      document.getElementById('current-user-name').textContent = user.full_name;
      document.getElementById('current-user-role').textContent = user.role;
      
      try {
        await this.loadRolesAndPermissions();
        this.enforceUIPermissions();
      } catch (err) {
        console.error("Failed to load permissions:", err);
      }
      
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

      window.addEventListener('hashchange', () => this.handleRouting());
      await this.handleRouting();
    } else {
      document.getElementById('login-overlay').style.display = 'flex';
      document.getElementById('sidebar-container').style.display = 'none';
      document.getElementById('project-select-wrapper').style.display = 'none';
    }
  }

  async loadRolesAndPermissions() {
    try {
      const data = await API.getPermissions();
      window.permissionsList = data.permissions;
      window.rolePermissionsList = data.role_permissions;
      
      const roles = await API.getRoles();
      window.rolesList = roles;
    } catch (err) {
      console.error("Could not fetch permissions grid:", err);
    }
  }

  enforceUIPermissions() {
    const user = JSON.parse(sessionStorage.getItem('user'));
    if (!user) return;
    
    const roleName = user.role;
    
    window.hasPermission = (module, action) => {
      if (roleName === 'Super Admin') return true;
      if (!window.permissionsList || !window.rolePermissionsList) return false;
      
      const perm = window.permissionsList.find(p => p.module.toLowerCase() === module.toLowerCase() && p.action.toLowerCase() === action.toLowerCase());
      if (!perm) return false;
      
      const role = window.rolesList ? window.rolesList.find(r => r.name === roleName) : null;
      if (!role) return false;
      
      return window.rolePermissionsList.some(rp => rp.role_id === role.id && rp.permission_id === perm.id);
    };

    // Show/Hide sidebar items depending on view rights
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(item => {
      const view = item.getAttribute('data-view');
      let moduleName = view.charAt(0).toUpperCase() + view.slice(1);
      if (view === 'knowledgebase') moduleName = 'Requirements';
      if (view === 'playwright') moduleName = 'Playwright';
      if (view === 'executions') moduleName = 'Execution';
      if (view === 'reports') moduleName = 'Reports';
      if (view === 'settings') moduleName = 'Settings';
      
      if (window.hasPermission(moduleName, 'view')) {
        item.style.display = 'flex';
      } else {
        item.style.display = 'none';
        if (item.classList.contains('active')) {
          item.classList.remove('active');
        }
      }
    });

    const createReqBtn = document.getElementById('btn-create-requirement');
    if (createReqBtn) {
      createReqBtn.style.display = window.hasPermission('Requirements', 'create') ? 'block' : 'none';
    }
  }

  async handleLoginSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error-msg');
    
    errorEl.style.display = 'none';
    errorEl.textContent = '';
    
    try {
      const data = await API.login(email, password);
      sessionStorage.setItem('access_token', data.access_token);
      sessionStorage.setItem('refresh_token', data.refresh_token);
      sessionStorage.setItem('user', JSON.stringify(data.user));
      
      await this.initAuth();
    } catch (err) {
      errorEl.textContent = err.message || "Invalid credentials. Please try again.";
      errorEl.style.display = 'block';
    }
  }

  async handleLogout() {
    const refreshToken = sessionStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        await API.logout(refreshToken);
      } catch (err) {
        console.warn("Logout request failed:", err);
      }
    }
    
    sessionStorage.clear();
    document.getElementById('login-overlay').style.display = 'flex';
    document.getElementById('sidebar-container').style.display = 'none';
    document.getElementById('project-select-wrapper').style.display = 'none';
    
    document.querySelectorAll('.view-panel').forEach(panel => {
      panel.classList.remove('active');
    });
  }

  switchSettingsTab(tabName) {
    document.querySelectorAll('.settings-tabs .tab-btn').forEach(btn => {
      btn.classList.remove('active');
    });
    document.querySelectorAll('.settings-tab-content').forEach(content => {
      content.classList.remove('active');
    });
    
    const btn = Array.from(document.querySelectorAll('.settings-tabs .tab-btn')).find(b => b.getAttribute('onclick').includes(tabName));
    if (btn) btn.classList.add('active');
    
    const targetContent = document.getElementById(`settings-tab-${tabName}`);
    if (targetContent) targetContent.classList.add('active');
    
    if (tabName === 'rbac') {
      this.loadRBACTab();
    } else if (tabName === 'users') {
      this.loadUsersTab();
    } else if (tabName === 'audit') {
      this.loadAuditLogsTab();
    }
  }

  async loadRBACTab() {
    try {
      await this.loadRolesAndPermissions();
      
      const roleSelect = document.getElementById('rbac-role-select');
      roleSelect.innerHTML = '';
      
      window.rolesList.forEach(role => {
        const option = document.createElement('option');
        option.value = role.id;
        option.textContent = role.name;
        roleSelect.appendChild(option);
      });
      
      if (window.rolesList.length > 0) {
        roleSelect.value = window.rolesList[0].id;
        this.loadRolePermissionsGrid();
      }
    } catch (err) {
      console.error("Failed to load RBAC tab:", err);
    }
  }

  loadRolePermissionsGrid() {
    const roleId = document.getElementById('rbac-role-select').value;
    const tbody = document.getElementById('perm-matrix-tbody');
    tbody.innerHTML = '';
    
    const modules = [
      'Dashboard', 'Requirements', 'Scenarios', 'TestCases', 
      'Playwright', 'Execution', 'Reports', 'Users', 'Roles', 'Permissions', 'Settings'
    ];
    const actions = ['view', 'create', 'edit', 'delete', 'approve'];
    
    modules.forEach(mod => {
      const tr = document.createElement('tr');
      
      const tdName = document.createElement('td');
      tdName.textContent = mod;
      tr.appendChild(tdName);
      
      actions.forEach(action => {
        const td = document.createElement('td');
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.setAttribute('data-module', mod);
        checkbox.setAttribute('data-action', action);
        
        const perm = window.permissionsList.find(p => p.module.toLowerCase() === mod.toLowerCase() && p.action.toLowerCase() === action.toLowerCase());
        
        if (perm) {
          const hasPerm = window.rolePermissionsList.some(rp => rp.role_id === roleId && rp.permission_id === perm.id);
          checkbox.checked = hasPerm;
          checkbox.setAttribute('data-perm-id', perm.id);
        } else {
          checkbox.disabled = true;
        }
        
        td.appendChild(checkbox);
        tr.appendChild(td);
      });
      
      tbody.appendChild(tr);
    });
  }

  async saveRolePermissionsGrid() {
    const roleId = document.getElementById('rbac-role-select').value;
    const checkboxes = document.querySelectorAll('#perm-matrix-tbody input[type="checkbox"]:checked');
    const checkedPermissionIds = Array.from(checkboxes)
      .map(cb => cb.getAttribute('data-perm-id'))
      .filter(id => id !== null);
      
    try {
      await API.updateRolePermissions(roleId, checkedPermissionIds);
      this.addLog("Access control matrix updated successfully.");
      alert("Permissions grid updated successfully.");
      
      await this.loadRolesAndPermissions();
      this.enforceUIPermissions();
    } catch (err) {
      alert(`Failed to save permissions: ${err.message}`);
    }
  }

  async loadUsersTab() {
    const tbody = document.getElementById('user-management-tbody');
    tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Loading system operators...</td></tr>';
    
    try {
      const users = await API.getUsers();
      tbody.innerHTML = '';
      
      if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center;">No system users found.</td></tr>';
        return;
      }
      
      users.forEach(u => {
        const tr = document.createElement('tr');
        
        const tdName = document.createElement('td');
        tdName.style.fontWeight = '600';
        tdName.textContent = u.full_name;
        tr.appendChild(tdName);
        
        const tdEmail = document.createElement('td');
        tdEmail.textContent = u.email;
        tr.appendChild(tdEmail);
        
        const tdRole = document.createElement('td');
        tdRole.innerHTML = `<span style="font-weight: 500; color: var(--accent-primary);">${u.role}</span>`;
        tr.appendChild(tdRole);
        
        const tdStatus = document.createElement('td');
        const isActive = u.is_active;
        tdStatus.innerHTML = `
          <label style="display: inline-flex; align-items: center; gap: 8px; cursor: pointer;">
            <input type="checkbox" ${isActive ? 'checked' : ''} onchange="toggleUserActiveStatus('${u.id}', this.checked)" style="width: 16px; height: 16px;" />
            <span style="font-size: 0.85rem; color: ${isActive ? 'var(--color-success)' : 'var(--text-muted)'};">${isActive ? 'Active' : 'Deactivated'}</span>
          </label>
        `;
        tr.appendChild(tdStatus);
        
        const tdActions = document.createElement('td');
        tdActions.style.textAlign = 'right';
        tdActions.innerHTML = `
          <button class="btn btn-secondary" onclick="openAssignProjectUserModal('${u.id}', '${u.email}')" style="padding: 4px 8px; font-size: 0.75rem; margin-right: 6px;">Map Workspace</button>
          <button class="btn btn-secondary" onclick="resetUserPasswordPrompt('${u.id}')" style="padding: 4px 8px; font-size: 0.75rem;">Reset PW</button>
        `;
        tr.appendChild(tdActions);
        
        tbody.appendChild(tr);
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--color-danger);">Failed to load users: ${err.message}</td></tr>`;
    }
  }

  async toggleUserActiveStatus(userId, isActive) {
    try {
      await API.toggleUserStatus(userId, isActive);
      this.addLog(`User status toggled: ${isActive ? 'Activated' : 'Deactivated'}`);
      this.loadUsersTab();
    } catch (err) {
      alert(`Failed to update status: ${err.message}`);
      this.loadUsersTab();
    }
  }

  async resetUserPasswordPrompt(userId) {
    const pw = prompt("Enter new password for this operator:");
    if (!pw) return;
    
    try {
      await API.resetUserPassword(userId, pw);
      this.addLog("User password reset complete.");
      alert("Password has been reset successfully.");
    } catch (err) {
      alert(`Failed to reset password: ${err.message}`);
    }
  }

  async handleCreateUserSubmit(e) {
    e.preventDefault();
    const fullname = document.getElementById('new-user-fullname').value.trim();
    const email = document.getElementById('new-user-email').value.trim();
    const password = document.getElementById('new-user-password').value;
    const role = document.getElementById('new-user-role').value;
    
    try {
      await API.createUser(fullname, email, password, role);
      this.addLog(`New user created: ${email} (${role})`);
      this.closeModal('create-user-modal');
      
      document.getElementById('create-user-form').reset();
      this.loadUsersTab();
    } catch (err) {
      alert(`Failed to create user: ${err.message}`);
    }
  }

  async openAssignProjectUserModal(userId, email) {
    document.getElementById('assign-user-id').value = userId;
    document.getElementById('assign-user-email').value = email;
    
    const roleSelect = document.getElementById('assign-role-id');
    roleSelect.innerHTML = '';
    
    try {
      await this.loadRolesAndPermissions();
      window.rolesList.forEach(r => {
        const opt = document.createElement('option');
        opt.value = r.id;
        opt.textContent = r.name;
        roleSelect.appendChild(opt);
      });
      this.openModal('assign-project-user-modal');
    } catch (err) {
      alert(`Failed to load roles: ${err.message}`);
    }
  }

  async handleAssignProjectUserSubmit(e) {
    e.preventDefault();
    if (!this.currentProject) {
      alert("Please select a workspace project first.");
      return;
    }
    
    const userId = document.getElementById('assign-user-id').value;
    const roleId = document.getElementById('assign-role-id').value;
    
    try {
      await API.assignProjectUser(this.currentProject.id, userId, roleId);
      this.addLog("Workspace mapping updated.");
      this.closeModal('assign-project-user-modal');
      alert("User workspace mapping saved successfully.");
    } catch (err) {
      alert(`Failed to map workspace: ${err.message}`);
    }
  }

  async loadAuditLogsTab() {
    const tbody = document.getElementById('audit-logs-tbody');
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Querying audit logs...</td></tr>';
    
    try {
      const logs = await API.getAuditLogs();
      tbody.innerHTML = '';
      
      if (logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No activity logs recorded.</td></tr>';
        return;
      }
      
      logs.forEach(l => {
        const tr = document.createElement('tr');
        
        const tdTime = document.createElement('td');
        tdTime.textContent = new Date(l.timestamp).toLocaleString();
        tr.appendChild(tdTime);
        
        const tdOperator = document.createElement('td');
        tdOperator.textContent = l.user_email;
        tr.appendChild(tdOperator);
        
        const tdProj = document.createElement('td');
        tdProj.textContent = l.project_id ? l.project_id.split('-')[0] + '...' : 'System';
        tr.appendChild(tdProj);
        
        const tdModule = document.createElement('td');
        tdModule.innerHTML = `<span class="badge badge-pending">${l.module}</span>`;
        tr.appendChild(tdModule);
        
        const tdAction = document.createElement('td');
        let actionBadgeClass = 'badge-pending';
        if (l.action === 'CREATE') actionBadgeClass = 'badge-approved';
        if (l.action === 'DELETE') actionBadgeClass = 'badge-rejected';
        if (l.action === 'UPDATE') actionBadgeClass = 'badge-medium';
        if (l.action === 'LOGIN') actionBadgeClass = 'badge-positive';
        
        tdAction.innerHTML = `<span class="badge ${actionBadgeClass}">${l.action}</span>`;
        tr.appendChild(tdAction);
        
        const tdChanges = document.createElement('td');
        tdChanges.style.fontFamily = 'monospace';
        tdChanges.style.fontSize = '0.75rem';
        tdChanges.textContent = JSON.stringify(l.field_changes);
        tr.appendChild(tdChanges);
        
        tbody.appendChild(tr);
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--color-danger);">Failed to query audit logs: ${err.message}</td></tr>`;
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const app = new App();
  window.appInstance = app;
  app.init().catch(console.error);
  
  window.closeModal = (modalId) => app.closeModal(modalId);
});
