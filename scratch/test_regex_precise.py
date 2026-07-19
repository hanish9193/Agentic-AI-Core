import re

script = """
test('Valid Guest Info and Payment Booking', async ({ page }) => {
  console.log("[Timeline] Navigate: to base URL");
  await page.goto(BASE_URL);

  console.log("[Timeline] Fill: username field with secure credential");
  const USERNAME = process.env.TARGET_USERNAME || 'default_username';
  await page.locator('input#username').fill(USERNAME);

  console.log("[Timeline] Fill: password field with secure credential");
  const PASSWORD = process.env.TARGET_PASSWORD || 'default_password';
  await page.locator('input#password').fill(PASSWORD);

  console.log("[Timeline] Click: login button");
  await page.locator('input#login').click();
  
  await expect(page).toHaveURL(/SearchHotel\\.aspx/);
});
"""

# Matches from the first username fill to the login click, including timeline messages
pattern = r"((?:console\.log\([^)]+\);\s*)?await\s+page\.(?:locator\([^)]+\)\.)?fill\(\s*['\"](?:input)?#username['\"].*?await\s+page\.(?:locator\([^)]+\)\.)?click\(\s*['\"](?:input)?#login['\"]\);?)"

match = re.search(pattern, script, flags=re.DOTALL | re.IGNORECASE)
if match:
    print("SUCCESS: Matched actions block:")
    print("=" * 60)
    print(match.group(1))
    print("=" * 60)
else:
    print("FAILED to match actions block.")
