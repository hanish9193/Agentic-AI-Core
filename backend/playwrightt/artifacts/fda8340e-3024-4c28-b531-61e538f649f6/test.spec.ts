await page.goto('https://google.com');

test.afterEach(async ({ page }) => {
  try {
    await page.context().storageState({ path: 'E:/Agentic-AI-Automation/backend/playwright/artifacts/BATCH-20260716-715/storage_state.json' });
  } catch (e) {
    console.error('Failed to save storage state:', e);
  }
});
