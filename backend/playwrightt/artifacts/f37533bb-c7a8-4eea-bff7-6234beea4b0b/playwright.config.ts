import { defineConfig } from '@playwright/test';
export default defineConfig({
  use: {
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    storageState: 'E:/Agentic-AI-Automation/backend/playwright/artifacts/BATCH-20260715-154/storage_state.json',
  },
  reporter: [
    ['line'],
    ['json', { outputFile: 'report.json' }]
  ],
  outputDir: 'E:/Agentic-AI-Automation/backend/playwrightt/artifacts/f37533bb-c7a8-4eea-bff7-6234beea4b0b/test-results',
  timeout: 60000,
});
