import { defineConfig } from '@playwright/test';
export default defineConfig({
  use: {
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    storageState: 'E:/Agentic-AI-Automation/backend/playwright/artifacts/BATCH-20260715-023/storage_state.json',
  },
  reporter: [
    ['line'],
    ['json', { outputFile: 'report.json' }]
  ],
  outputDir: 'E:/Agentic-AI-Automation/backend/playwrightt/artifacts/710287a9-fa3d-4fec-b9fe-182c1a46158f/test-results',
  timeout: 60000,
});
