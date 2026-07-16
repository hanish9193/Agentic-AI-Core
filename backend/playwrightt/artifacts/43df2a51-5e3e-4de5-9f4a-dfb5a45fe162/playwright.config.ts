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
  outputDir: 'E:/Agentic-AI-Automation/backend/playwrightt/artifacts/43df2a51-5e3e-4de5-9f4a-dfb5a45fe162/test-results',
  timeout: 60000,
});
