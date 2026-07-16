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
  outputDir: 'E:/Agentic-AI-Automation/backend/playwrightt/artifacts/369d987b-c07e-4b0c-839c-b6a6882ec0e5/test-results',
  timeout: 60000,
});
