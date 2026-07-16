import { defineConfig } from '@playwright/test';
export default defineConfig({
  use: {
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    storageState: 'E:\\Agentic-AI-Automation\\backend\\playwright\\artifacts\\BATCH-20260715-115\\storage_state.json',
  },
  reporter: [
    ['line'],
    ['json', { outputFile: 'report.json' }]
  ],
  outputDir: 'E:\Agentic-AI-Automation\backend\playwrightt\artifacts\24d68dd7-3a02-47b2-be4b-b63dd299a96f\test-results',
  timeout: 60000,
});
