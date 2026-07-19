import json
import os

store_path = os.path.join("backend", "database", "project_store.json")
with open(store_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Ensure projects exist
projects = data.get("projects", [])
project_ids = [p.get("id") for p in projects]

project_template = {
  "name": "Agentic AI Automation",
  "description": "Browser automation workspace",
  "line_of_business": "general",
  "framework": "playwright",
  "jira_project_key": None,
  "target_url": "https://adactinhotelapp.com/",
  "target_username": "vault_secured",
  "target_password_enc": "vault_secured",
  "created_at": "2026-07-07T08:09:32.829394Z",
  "requirements": []
}

for pid in ["9752881f-0f09-4a35-a904-61745f0e2768", "b4c13430-f95f-4ea5-b0ed-a09a0b3b324c"]:
    if pid not in project_ids:
        new_proj = project_template.copy()
        new_proj["id"] = pid
        projects.append(new_proj)
        print(f"Added project: {pid}")
    else:
        # Ensure framework is playwright
        for p in projects:
            if p.get("id") == pid:
                p["framework"] = "playwright"

# Ensure test cases exist
test_cases = data.get("test_cases", {})

# 1. No Location Selected Search Page Error
location_error_script = """import { test, expect } from '@playwright/test';

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
    print(`[Error] Unexpected search result: ${error.message}`);
    throw error;
  }
});"""

test_cases["c414b552-5663-49aa-8829-5b7478a240a4"] = {
  "id": "c414b552-5663-49aa-8829-5b7478a240a4",
  "scenario_id": None,
  "title": "No Location Selected Search Page Error",
  "preconditions": [],
  "steps": [
    "Navigate to target URL",
    "Enter valid username and password and click login",
    "On Search page, click Search button without selecting location"
  ],
  "expected_result": "The error message 'Please Select a Location' is displayed",
  "priority": "high",
  "status": "passed",
  "confidence": 0.95,
  "evaluation_status": "approved",
  "playwright_script": location_error_script,
  "is_frozen": False,
  "automation_framework": "Playwright"
}

# 2. Valid Credentials Login Test Case
valid_login_script = """import { test, expect } from '@playwright/test';

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

test_cases["9ffdd15a-a59d-43ab-a49c-1c4c4f697d51"] = {
  "id": "9ffdd15a-a59d-43ab-a49c-1c4c4f697d51",
  "scenario_id": None,
  "title": "Valid Credentials Login Test Case",
  "preconditions": [],
  "steps": [
    "Navigate to target URL",
    "Enter valid username and password",
    "Click login"
  ],
  "expected_result": "The user is redirected to the Welcome Dashboard displaying 'Hello <Username>!'",
  "priority": "high",
  "status": "passed",
  "confidence": 0.95,
  "evaluation_status": "approved",
  "playwright_script": valid_login_script,
  "is_frozen": False,
  "automation_framework": "Playwright"
}

with open(store_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
print("Database updated and saved successfully.")
