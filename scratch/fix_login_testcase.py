import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
target_id = "9ffdd15a-a59d-43ab-a49c-1c4c4f697d51"

if target_id in test_cases:
    new_script = """import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TARGET_URL || 'https://adactinhotelapp.com/';
const USERNAME = process.env.TARGET_USERNAME || 'ADACTINFORQA';
const PASSWORD = process.env.TARGET_PASSWORD || '3U0515';

test('Valid Credentials Login Test Case', async ({ page }) => {
  console.log("[Timeline] Navigate: Navigating to target URL");
  await page.goto(BASE_URL);

  console.log("[Timeline] Fill: Entering valid username into Username field");
  await page.locator('input#username').fill(USERNAME);

  console.log("[Timeline] Fill: Entering valid password into Password field");
  await page.locator('input#password').fill(PASSWORD);

  console.log("[Timeline] Click: Clicking Login button");
  await page.locator('input#login').click();

  console.log("[Timeline] Search Page Load: Waiting for Search page to load");
  await page.locator('input#username_show').waitFor({ state: 'visible', timeout: 10000 });

  console.log("[Timeline] Locator: Checking the Welcome Username field for expected result");
  await expect(page.locator('input#username_show')).toHaveValue(`Hello ${USERNAME}!`);
});"""

    test_cases[target_id]["playwright_script"] = new_script
    print("Valid login test case script successfully updated in database dictionary.")
    
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("JSON store saved successfully.")
else:
    print(f"Error: Test case with ID {target_id} not found in store.")
