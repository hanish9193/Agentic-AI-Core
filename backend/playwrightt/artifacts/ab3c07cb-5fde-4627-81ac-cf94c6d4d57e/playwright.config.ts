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
  outputDir: 'E:/Agentic-AI-Automation/backend/playwrightt/artifacts/ab3c07cb-5fde-4627-81ac-cf94c6d4d57e/test-results',
  timeout: 60000,
});
