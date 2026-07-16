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
  outputDir: 'E:/Agentic-AI-Automation/backend/playwrightt/artifacts/b55244ae-79f8-4419-9ab9-bda37de50e7d/test-results',
  timeout: 60000,
});
