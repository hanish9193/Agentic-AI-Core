const API_BASE = '/api/v1';

async function request(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  // If body is FormData, do not set Content-Type header manually
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }

  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let errorMsg = `HTTP error! Status: ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) {
        errorMsg = errJson.detail;
      }
    } catch (e) {}
    throw new Error(errorMsg);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const API = {
  // Projects
  async getProjects() {
    return request('/projects');
  },

  async getProject(id) {
    return request(`/projects/${id}`);
  },

  async createProject(name, description, lineOfBusiness) {
    return request('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, description, line_of_business: lineOfBusiness })
    });
  },

  async updateProject(id, name, description, lineOfBusiness) {
    return request(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ name, description, line_of_business: lineOfBusiness })
    });
  },

  async deleteProject(id) {
    return request(`/projects/${id}`, {
      method: 'DELETE'
    });
  },

  // Requirements
  async getRequirements(projectId) {
    return request(`/projects/${projectId}/requirements`);
  },

  async createRequirement(projectId, title, description, priority, businessDomain) {
    return request(`/projects/${projectId}/requirements`, {
      method: 'POST',
      body: JSON.stringify({
        title,
        description,
        priority,
        business_domain: businessDomain
      })
    });
  },

  // Import Requirements File
  async importRequirements(projectId, fileObj) {
    const formData = new FormData();
    formData.append('file', fileObj);
    return request(`/projects/${projectId}/requirements/import`, {
      method: 'POST',
      body: formData
    });
  },

  // Scenarios
  async getScenarios(projectId) {
    return request(`/projects/${projectId}/scenarios`);
  },

  async generateScenarios(projectId, requirementId, count, mode = 'append') {
    return request(`/projects/${projectId}/requirements/${requirementId}/generate-scenarios`, {
      method: 'POST',
      body: JSON.stringify({ count, mode })
    });
  },

  async updateScenario(projectId, scenarioId, data) {
    return request(`/projects/${projectId}/scenarios/${scenarioId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  },

  async deleteScenario(projectId, scenarioId) {
    return request(`/projects/${projectId}/scenarios/${scenarioId}`, {
      method: 'DELETE'
    });
  },

  async duplicateScenario(projectId, scenarioId) {
    return request(`/projects/${projectId}/scenarios/duplicate/${scenarioId}`, {
      method: 'POST'
    });
  },

  // Scenario Notes
  async getScenarioNotes(scenarioId) {
    return request(`/scenarios/${scenarioId}/notes`);
  },

  async addScenarioNote(scenarioId, note) {
    return request(`/scenarios/${scenarioId}/notes`, {
      method: 'POST',
      body: JSON.stringify({ note })
    });
  },

  // Test Cases
  async getTestCases(projectId) {
    return request(`/projects/${projectId}/testcases`);
  },

  async generateTestCases(projectId, requirementId) {
    return request(`/projects/${projectId}/requirements/${requirementId}/generate-testcases`, {
      method: 'POST'
    });
  },

  async updateTestCase(projectId, testCaseId, data) {
    return request(`/projects/${projectId}/testcases/${testCaseId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  },

  async deleteTestCase(projectId, testCaseId) {
    return request(`/projects/${projectId}/testcases/${testCaseId}`, {
      method: 'DELETE'
    });
  },

  // Test Case Notes
  async getTestCaseNotes(testCaseId) {
    return request(`/testcases/${testCaseId}/notes`);
  },

  async addTestCaseNote(testCaseId, note) {
    return request(`/testcases/${testCaseId}/notes`, {
      method: 'POST',
      body: JSON.stringify({ note })
    });
  },

  // Playwright Code Generation
  async generatePlaywrightScript(projectId, testCaseId) {
    return request(`/projects/${projectId}/testcases/${testCaseId}/generate-script`, {
      method: 'POST'
    });
  },

  async saveTestCaseScript(projectId, testCaseId, script) {
    return request(`/projects/${projectId}/testcases/${testCaseId}/script`, {
      method: 'PUT',
      body: JSON.stringify({ script })
    });
  },

  // Playwright Execution Run
  async executeTestCase(projectId, testCaseId) {
    return request(`/projects/${projectId}/testcases/${testCaseId}/execute`, {
      method: 'POST'
    });
  },

  // Execution Results history
  async getExecutionResults(projectId) {
    return request(`/projects/${projectId}/executions`);
  },

  async getExecutionDetail(projectId, executionId) {
    return request(`/projects/${projectId}/executions/${executionId}`);
  },

  // Knowledge Base documents
  async getDocuments(projectId) {
    return request(`/projects/${projectId}/documents`);
  },

  async createDocument(projectId, docData) {
    return request(`/projects/${projectId}/documents`, {
      method: 'POST',
      body: JSON.stringify(docData)
    });
  },

  async deleteDocument(projectId, documentId) {
    return request(`/projects/${projectId}/documents/${documentId}`, {
      method: 'DELETE'
    });
  },

  // Settings
  async getSettings() {
    return request('/settings');
  },

  async updateSettings(settings) {
    return request('/settings', {
      method: 'PUT',
      body: JSON.stringify(settings)
    });
  },

  // LangSmith Trace Logs
  async getTraces(projectId) {
    return request(`/projects/${projectId}/traces`);
  }
};
export { API_BASE };
