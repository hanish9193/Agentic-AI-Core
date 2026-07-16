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
  outputDir: 'E:/Agentic-AI-Automation/backend/playwrightt/artifacts/c3657c82-3bc3-473d-8d34-037388af3e58/test-results',
  timeout: 60000,
});
