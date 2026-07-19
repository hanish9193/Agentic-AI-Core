from uuid import uuid4
from backend.services.playwright_runner import PlaywrightRunner

def main():
    script = """
import { test, expect } from '@playwright/test';

test('browser test', async ({ page, context, browser }) => {
    expect(browser).toBeTruthy();
    expect(context).toBeTruthy();
    expect(page).toBeTruthy();
    await page.goto('https://example.com');
    const content = await page.content();
    expect(content).toBeTruthy();
    expect(content.length).toBeGreaterThan(0);
});
"""
    runner = PlaywrightRunner(timeout_seconds=30)
    run_id = str(uuid4())
    print("Running browser test...")
    result = runner.run(script=script, run_id=run_id, headless=True)
    print("Status:", result.status)
    print("Error Message:", result.error_message)
    print("Stdout lines:")
    for line in result.stdout_lines:
        print("  ", line)

if __name__ == '__main__':
    main()
