import json
import os

store_path = os.path.join("backend", "database", "project_store.json")

# Load clean database
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 1. Update project framework to 'playwright'
projects = data.get("projects", [])
target_project_id = "9752881f-0f09-4a35-a904-61745f0e2768"
for p in projects:
    if p.get("id") == target_project_id:
        p["framework"] = "playwright"
        print(f"Project '{p.get('name')}' framework set to 'playwright'.")

test_cases = data.get("test_cases", {})

# 2. Update No Location Selected Search Page Error testcase
location_error_id = "c414b552-5663-49aa-8829-5b7478a240a4"
if location_error_id in test_cases:
    test_cases[location_error_id]["playwright_script"] = """import { test, expect } from '@playwright/test';

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
    print("Updated location error test case.")

# 3. Update Valid Credentials Login Test Case
valid_login_id = "9ffdd15a-a59d-43ab-a49c-1c4c4f697d51"
if valid_login_id in test_cases:
    test_cases[valid_login_id]["playwright_script"] = """import { test, expect } from '@playwright/test';

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
    print("Updated valid login test case.")

# Save modified database
with open(store_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print("Database updated and saved successfully.")
