const API_BASE = '/api/v1';

async function request(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

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

  async createProject(name, description) {
    return request('/projects', {
      method: 'POST',
      body: JSON.stringify({ name, description })
    });
  },

  async updateProject(id, name, description) {
    return request(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify({ name, description })
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

  // Scenarios
  async getScenarios(projectId) {
    return request(`/projects/${projectId}/scenarios`);
  },

  async generateScenarios(projectId, requirementId, count) {
    return request(`/projects/${projectId}/requirements/${requirementId}/generate-scenarios`, {
      method: 'POST',
      body: JSON.stringify({ count })
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

  // Playwright Code Generation
  async generatePlaywrightScript(projectId, testCaseId) {
    return request(`/projects/${projectId}/testcases/${testCaseId}/generate-script`, {
      method: 'POST'
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
