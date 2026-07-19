import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
target_id = "c414b552-5663-49aa-8829-5b7478a240a4"

if target_id in test_cases:
    new_script = """import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TARGET_URL || 'https://adactinhotelapp.com/';

test('No Location Selected Search Page Error', async ({ page }) => {
  console.log('[Timeline] Navigate: Navigating to target URL');
  await page.goto(BASE_URL);

  console.log('[Timeline] Login Credentials: User credentials loaded');
  const USERNAME = process.env.TARGET_USERNAME || 'default_username';
  const PASSWORD = process.env.TARGET_PASSWORD || 'default_password';

  console.log('[Timeline] Login: Entering credentials');
  await page.locator('input[name="username"]').fill(USERNAME);
  await page.locator('input[name="password"]').fill(PASSWORD);

  console.log('[Timeline] Login: Clicking the login button');
  await page.locator('input#login').click();

  console.log('[Timeline] Search Page Load: Waiting for Search page to load');
  await page.locator('select#location').waitFor({ state: 'visible', timeout: 10000 });

  console.log('[Timeline] Search: Clicking the Search button without selecting location');
  try {
    await page.locator('input#Submit').click();
    console.log('[Timeline] Search Error Message: Verifying error message is displayed');
    const errorMessage = await page.locator('span#location_span').textContent();
    expect(errorMessage).toContain('Please Select a Location');
  } catch (error) {
    console.log(`[Error] Unexpected search result: ${error.message}`);
    throw error;
  }
});"""

    test_cases[target_id]["playwright_script"] = new_script
    print("Script successfully updated in database dictionary to use locator actions.")
    
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("JSON store saved successfully.")
else:
    print(f"Error: Test case with ID {target_id} not found in store.")
