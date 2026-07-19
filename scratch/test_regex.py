import re

script = """
import { test, expect } from '@playwright/test';

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
});
"""

# Let's design a regex that matches:
# - page.goto
# - username fill (either style)
# - password fill (either style)
# - login click (either style)
pattern = r"(await\s+page\.goto\([^)]+\);?.*?username.*?\.fill\(.*?\);?.*?password.*?\.fill\(.*?\);?.*?login.*?\.click\(.*?\);?)"

replacement = """\\1""" # Just checking if it matches

match = re.search(pattern, script, flags=re.DOTALL | re.IGNORECASE)
if match:
    print("SUCCESS: Matched login block:")
    print("=" * 60)
    print(match.group(1))
    print("=" * 60)
else:
    print("FAILED to match login block.")
