import { defineConfig } from '@playwright/test';
export default defineConfig({
  use: {
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    storageState: 'E:/Agentic-AI-Automation/backend/playwright/artifacts/BATCH-20260715-233/storage_state.json',
  },
  reporter: [
    ['line'],
    ['json', { outputFile: 'report.json' }]
  ],
  outputDir: 'E:/Agentic-AI-Automation/backend/playwrightt/artifacts/69fe9b86-2d31-43fa-b37e-586e803e1bec/test-results',
  timeout: 60000,
});
