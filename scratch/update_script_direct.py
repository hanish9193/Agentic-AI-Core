import psycopg2

login_script = """import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TARGET_URL || 'https://adactinhotelapp.com/';
const USERNAME = process.env.TARGET_USERNAME || 'ADACTINFORQA';
const PASSWORD = process.env.TARGET_PASSWORD || '3U0515';

test('Valid Login with Username and Password', async ({ page }) => {
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
});
"""

booking_script = """import { test, expect } from '@playwright/test';

const BASE_URL = process.env.TARGET_URL || 'https://adactinhotelapp.com/';
const USERNAME = process.env.TARGET_USERNAME || 'ADACTINFORQA';
const PASSWORD = process.env.TARGET_PASSWORD || '3U0515';

test('Valid Guest Information and Payment', async ({ page }) => {
  console.log("[Timeline] Navigate: to base URL");
  await page.goto(BASE_URL);

  console.log("[Timeline] Fill: username field");
  await page.locator('input#username').fill(USERNAME);

  console.log("[Timeline] Fill: password field");
  await page.locator('input#password').fill(PASSWORD);

  console.log("[Timeline] Click: login button");
  await page.locator('input#login').click();

  console.log("[Timeline] Search Page Load: Wait for redirection to SearchHotel.php");
  await expect(page).toHaveURL(/SearchHotel\\.php/);

  console.log("[Timeline] SelectOption: Location dropdown");
  await page.locator('select#location').selectOption('Sydney');

  console.log("[Timeline] SelectOption: Hotels dropdown");
  await page.locator('select#hotels').selectOption('Hotel Creek');

  console.log("[Timeline] SelectOption: Room Type dropdown");
  await page.locator('select#room_type').selectOption('Standard');

  console.log("[Timeline] SelectOption: Number of Rooms dropdown");
  await page.locator('select#room_nos').selectOption('1 - One');

  console.log("[Timeline] Fill: Check-in Date");
  await page.locator('input#datepick_in').fill('20/08/2026');

  console.log("[Timeline] Fill: Check-out Date");
  await page.locator('input#datepick_out').fill('25/08/2026');

  console.log("[Timeline] SelectOption: Adults per Room dropdown");
  await page.locator('select#adult_room').selectOption('1');

  console.log("[Timeline] SelectOption: Children per Room dropdown");
  await page.locator('select#child_room').selectOption('0');

  console.log("[Timeline] Click: Search button");
  await page.locator('input#Submit').click();

  console.log("[Timeline] Wait: redirection to SelectHotel.php");
  await expect(page).toHaveURL(/SelectHotel\\.php/);

  console.log("[Timeline] Click: Radio button to select first hotel");
  await page.locator('input#radiobutton_0').check();

  console.log("[Timeline] Click: Continue button");
  await page.locator('input#continue').click();

  console.log("[Timeline] Wait: redirection to BookHotel.php");
  await expect(page).toHaveURL(/BookHotel\\.php/);

  console.log("[Timeline] Fill: First Name");
  await page.locator('input#first_name').fill('John');

  console.log("[Timeline] Fill: Last Name");
  await page.locator('input#last_name').fill('Doe');

  console.log("[Timeline] Fill: Billing Address");
  await page.locator('textarea#address').fill('123 Test Street, Sydney, NSW');

  console.log("[Timeline] Fill: Credit Card Number");
  await page.locator('input#cc_num').fill('1234567890123456');

  console.log("[Timeline] SelectOption: Credit Card Type");
  await page.locator('select#cc_type').selectOption('VISA');

  console.log("[Timeline] SelectOption: Expiry Month");
  await page.locator('select#cc_exp_month').selectOption('December');

  console.log("[Timeline] SelectOption: Expiry Year");
  await page.locator('select#cc_exp_year').selectOption('2028');

  console.log("[Timeline] Fill: CVV");
  await page.locator('input#cc_cvv').fill('123');

  console.log("[Timeline] Click: Book Now button");
  await page.locator('input#book_now').click();

  console.log("[Timeline] Wait: redirection to BookingConfirm.php");
  await expect(page).toHaveURL(/BookingConfirm\\.php/, { timeout: 15000 });

  console.log("[Timeline] Assertion: Retrieve Order Number");
  const orderNumber = await page.locator('input#order_no').inputValue();
  expect(orderNumber).toMatch(/^\\d+$/);
});
"""

login_id = "527350a5-3042-43c2-b19a-ab8c20f429c2"
booking_id = "18c09ec4-a136-4d8a-aa01-d50be7ed333c"

try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        database="Agentic_ai",
        user="postgres",
        password="hanish13"
    )
    cur = conn.cursor()
    
    # Update login test case
    cur.execute("UPDATE test_cases SET playwright_script = %s, evaluation_status = 'approved' WHERE id = %s", (login_script, login_id))
    print(f"Updated login test case script. Rows affected: {cur.rowcount}")
    
    # Update booking test case
    cur.execute("UPDATE test_cases SET playwright_script = %s, evaluation_status = 'approved' WHERE id = %s", (booking_script, booking_id))
    print(f"Updated booking test case script. Rows affected: {cur.rowcount}")
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database updates committed successfully.")
except Exception as e:
    print(f"PostgreSQL update failed: {e}")
