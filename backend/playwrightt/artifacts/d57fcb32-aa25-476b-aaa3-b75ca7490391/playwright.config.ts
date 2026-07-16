import { defineConfig } from '@playwright/test';
export default defineConfig({
  use: {
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    storageState: 'E:/Agentic-AI-Automation/backend/playwright/artifacts/BATCH-20260715-691/storage_state.json',
  },
  reporter: [
    ['line'],
    ['json', { outputFile: 'report.json' }]
  ],
  outputDir: 'E:/Agentic-AI-Automation/backend/playwrightt/artifacts/d57fcb32-aa25-476b-aaa3-b75ca7490391/test-results',
  timeout: 60000,
});
