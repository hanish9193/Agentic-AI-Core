import { defineConfig } from '@playwright/test';
export default defineConfig({
  use: {
    headless: false,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    
  },
  reporter: [
    ['line'],
    ['json', { outputFile: 'report.json' }]
  ],
  outputDir: 'E:/Agentic-AI-Automation/backend/playwrightt/artifacts/0ff99db4-5bd9-4476-bc7d-5460a23f1b04/test-results',
  timeout: 60000,
});
