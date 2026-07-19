import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

test_cases = data.get("test_cases", {})
target_id = "ab3c07cb-5fde-4627-81ac-cf94c6d4d57e"

if target_id in test_cases:
    new_script = """import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TARGET_URL || 'https://adactinhotelapp.com/';
const USERNAME = process.env.TARGET_USERNAME || 'ADACTINFORQA';

test('Invalid Password Error', async ({ page }) => {
  console.log("[Timeline] Navigate: Navigating to target URL");
  await page.goto(BASE_URL);

  console.log("[Timeline] Locator: Entering username");
  await page.locator('input#username').fill(USERNAME);

  console.log("[Timeline] Locator: Entering invalid password");
  await page.locator('input#password').fill('invalid_password_123');

  console.log("[Timeline] Locator: Clicking login button");
  await page.locator('input#login').click();

  console.log("[Timeline] Search Page Load: Waiting for error message container");
  await page.locator('.loginerror').waitFor({ state: 'visible', timeout: 10000 });

  console.log("[Timeline] Locator: Asserting the error message");
  await expect(page.locator('.loginerror')).toContainText('Invalid Login details');
});"""

    test_cases[target_id]["playwright_script"] = new_script
    print("Invalid password test case successfully updated in database.")
    
    with open(store_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Database updated and saved successfully.")
else:
    print(f"Error: Test case with ID {target_id} not found in database.")
