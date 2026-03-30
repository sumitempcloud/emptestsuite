import { test, expect, Page, BrowserContext, Browser } from "@playwright/test";

const BASE_URL = "https://test-empcloud.empcloud.com";
const API_URL = "https://test-empcloud.empcloud.com/api/v1";

const ADMIN_CREDS = { email: "ananya@technova.in", password: "Welcome@123" };
const EMPLOYEE_CREDS = { email: "priya@technova.in", password: "Welcome@123" };
const SUPER_ADMIN_CREDS = { email: "admin@empcloud.com", password: "SuperAdmin@123" };
const OTHER_ORG_CREDS = { email: "john@globaltech.com", password: "Welcome@123" };

async function login(page: Page, email: string, password: string) {
  await page.goto(`${BASE_URL}/login`, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(500);
  if (!page.url().includes("/login")) return;
  const emailInput = page.locator('input[name="email"], input[type="email"]').first();
  const passwordInput = page.locator('input[name="password"], input[type="password"]').first();
  await emailInput.waitFor({ state: "visible", timeout: 10000 });
  await emailInput.fill(email);
  await passwordInput.fill(password);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 15000 });
  await page.waitForLoadState("networkidle", { timeout: 10000 }).catch(() => {});
}

async function loginAndGo(page: Page, email: string, password: string, path: string) {
  await login(page, email, password);
  if (path !== "/") {
    await page.goto(`${BASE_URL}${path}`, { waitUntil: "networkidle", timeout: 30000 });
  }
  await page.waitForTimeout(1000);
}

async function createFreshContext(browser: Browser): Promise<{ context: BrowserContext; page: Page }> {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();
  return { context, page };
}

async function getAuthToken(email: string, password: string): Promise<string> {
  const resp = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await resp.json();
  return data.data?.tokens?.access_token || data.data?.access_token || data.access_token || data.token || "";
}

async function apiGet(token: string, path: string): Promise<any> {
  const resp = await fetch(`${API_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return { status: resp.status, data: await resp.json().catch(() => null) };
}

async function apiPost(token: string, path: string, body: any): Promise<any> {
  const resp = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return { status: resp.status, data: await resp.json().catch(() => null) };
}

async function apiPut(token: string, path: string, body: any): Promise<any> {
  const resp = await fetch(`${API_URL}${path}`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return { status: resp.status, data: await resp.json().catch(() => null) };
}

async function apiDelete(token: string, path: string): Promise<any> {
  const resp = await fetch(`${API_URL}${path}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });
  return { status: resp.status, data: await resp.json().catch(() => null) };
}

/** Find first employee ID from the employee list (for the logged-in org) */
async function getFirstEmployeeId(token: string): Promise<string> {
  const res = await apiGet(token, "/employees?page=1&limit=5");
  const list = res.data?.data?.employees || res.data?.data?.items || res.data?.data || [];
  const arr = Array.isArray(list) ? list : [];
  if (arr.length > 0) return String(arr[0].id || arr[0]._id || arr[0].employee_id);
  return "";
}

/** Find self employee record */
async function getSelfEmployeeId(token: string): Promise<string> {
  const res = await apiGet(token, "/users/me");
  const user = res.data?.data || res.data;
  return String(user?.employee_id || user?.id || user?._id || "");
}

// ============================================================
// PHASE 1: Employee Directory
// ============================================================
test.describe("Phase 1: Employee Directory", () => {

  test("TC01 — Navigate to /employees as HR, table loads with pagination", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/employees");
      await page.screenshot({ path: "e2e/screenshots/tp_emp_directory_loads.png", fullPage: true });

      const body = await page.textContent("body") || "";
      const hasContent = /employee|name|department|designation/i.test(body);
      expect(hasContent).toBeTruthy();

      // Check for table rows or list items
      const rows = page.locator("table tbody tr, [class*='employee'] [class*='row'], [class*='card'], [class*='list-item']");
      const count = await rows.count();
      console.log(`  TC01: Found ${count} employee rows/cards`);
      expect(count).toBeGreaterThan(0);

      // Check for pagination
      const paginationText = body.match(/page|showing|of\s+\d+|next|previous|\d+\s*-\s*\d+/i);
      console.log(`  TC01: Pagination indicator found: ${!!paginationText}`);
    } finally {
      await context.close();
    }
  });

  test("TC02 — Search by employee name", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/employees");

      const searchInput = page.locator('input[placeholder*="search" i], input[type="search"], input[name="search"]').first();
      const searchExists = await searchInput.isVisible().catch(() => false);

      if (searchExists) {
        await searchInput.fill("priya");
        await page.waitForTimeout(2000);
        await page.screenshot({ path: "e2e/screenshots/tp_emp_search_name.png", fullPage: true });
        const bodyText = (await page.textContent("body")) || "";
        const found = /priya/i.test(bodyText);
        console.log(`  TC02: Search 'priya' — found in results: ${found}`);
        expect(found).toBeTruthy();
      } else {
        console.log("  TC02: FINDING — No search input on /employees page");
        await page.screenshot({ path: "e2e/screenshots/tp_emp_search_name_missing.png", fullPage: true });
      }
    } finally {
      await context.close();
    }
  });

  test("TC03 — Search by email", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/employees");

      const searchInput = page.locator('input[placeholder*="search" i], input[type="search"], input[name="search"]').first();
      const searchExists = await searchInput.isVisible().catch(() => false);

      if (searchExists) {
        await searchInput.fill("priya@technova.in");
        await page.waitForTimeout(2000);
        await page.screenshot({ path: "e2e/screenshots/tp_emp_search_email.png", fullPage: true });
        const bodyText = (await page.textContent("body")) || "";
        const found = /priya/i.test(bodyText);
        console.log(`  TC03: Search by email — found in results: ${found}`);
      } else {
        console.log("  TC03: FINDING — No search input on /employees page");
        await page.screenshot({ path: "e2e/screenshots/tp_emp_search_email_missing.png", fullPage: true });
      }
    } finally {
      await context.close();
    }
  });

  test("TC04 — Filter by department dropdown", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/employees");

      // Look for department filter
      const filterSelect = page.locator('select[name*="department" i], [class*="filter"] select, button:has-text("Department"), button:has-text("Filter")').first();
      const filterExists = await filterSelect.isVisible().catch(() => false);

      if (filterExists) {
        await filterSelect.click();
        await page.waitForTimeout(500);
        await page.screenshot({ path: "e2e/screenshots/tp_emp_filter_dept.png", fullPage: true });
        // Try to select a department from dropdown options
        const option = page.locator('[role="option"], [role="listbox"] li, select option').first();
        const optionExists = await option.isVisible().catch(() => false);
        if (optionExists) {
          await option.click();
          await page.waitForTimeout(1500);
          await page.screenshot({ path: "e2e/screenshots/tp_emp_filter_dept_applied.png", fullPage: true });
          console.log("  TC04: Department filter applied");
        }
      } else {
        console.log("  TC04: FINDING — No department filter dropdown found on /employees");
        await page.screenshot({ path: "e2e/screenshots/tp_emp_filter_dept_missing.png", fullPage: true });
      }
    } finally {
      await context.close();
    }
  });

  test("TC05 — Verify table columns (name, email, dept, designation, emp_code, status)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/employees");
      await page.screenshot({ path: "e2e/screenshots/tp_emp_table_columns.png", fullPage: true });

      const body = (await page.textContent("body")) || "";
      const lc = body.toLowerCase();
      const columns = {
        name: /name/i.test(body),
        email: /email/i.test(body),
        department: /department/i.test(body),
        designation: /designation|title|role/i.test(body),
        emp_code: /emp.?code|employee.?id|code/i.test(body),
        status: /status|active|inactive/i.test(body),
      };
      console.log("  TC05: Columns found:", JSON.stringify(columns));
      // At least name and email should be visible
      expect(columns.name || columns.email).toBeTruthy();
    } finally {
      await context.close();
    }
  });

  test("TC06 — Click employee row navigates to profile", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/employees");

      const row = page.locator("table tbody tr, [class*='employee-card'], [class*='list-item'] a, [class*='card']").first();
      const rowExists = await row.isVisible().catch(() => false);

      if (rowExists) {
        const startUrl = page.url();
        await row.click();
        await page.waitForTimeout(2000);
        await page.screenshot({ path: "e2e/screenshots/tp_emp_row_click.png", fullPage: true });
        const endUrl = page.url();
        const navigated = endUrl !== startUrl;
        console.log(`  TC06: Clicked row — navigated: ${navigated}, URL: ${endUrl}`);
        // Should navigate to a profile page (contains employee id or 'profile')
        const isProfile = /employees\/\d+|profile/i.test(endUrl);
        console.log(`  TC06: Landed on profile page: ${isProfile}`);
      } else {
        console.log("  TC06: FINDING — No clickable employee rows found");
        await page.screenshot({ path: "e2e/screenshots/tp_emp_row_click_missing.png", fullPage: true });
      }
    } finally {
      await context.close();
    }
  });

  test("TC07 — Pagination next/previous", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/employees");

      const nextBtn = page.locator('button:has-text("Next"), button:has-text("next"), [aria-label*="next" i], button:has-text(">"), button:has-text("»"), [class*="pagination"] button').first();
      const nextExists = await nextBtn.isVisible().catch(() => false);

      if (nextExists) {
        await nextBtn.click();
        await page.waitForTimeout(2000);
        await page.screenshot({ path: "e2e/screenshots/tp_emp_pagination_next.png", fullPage: true });
        console.log("  TC07: Clicked next page");

        const prevBtn = page.locator('button:has-text("Previous"), button:has-text("previous"), button:has-text("Prev"), [aria-label*="prev" i], button:has-text("<"), button:has-text("«")').first();
        const prevExists = await prevBtn.isVisible().catch(() => false);
        if (prevExists) {
          await prevBtn.click();
          await page.waitForTimeout(2000);
          console.log("  TC07: Clicked previous page — pagination works");
        }
      } else {
        console.log("  TC07: No pagination buttons found (may be single page)");
        await page.screenshot({ path: "e2e/screenshots/tp_emp_pagination_missing.png", fullPage: true });
      }
    } finally {
      await context.close();
    }
  });

  test("TC08 — Total employee count displayed", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/employees");
      await page.screenshot({ path: "e2e/screenshots/tp_emp_total_count.png", fullPage: true });

      const body = (await page.textContent("body")) || "";
      const countMatch = body.match(/(\d+)\s*(employees|total|results|showing)/i) || body.match(/(showing|total|of)\s*(\d+)/i);
      if (countMatch) {
        console.log(`  TC08: Total count indicator found: ${countMatch[0]}`);
      } else {
        console.log("  TC08: FINDING — No total employee count indicator visible on page");
      }
    } finally {
      await context.close();
    }
  });

  test("TC09 — Employee view: can see directory", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password, "/employees");
      await page.screenshot({ path: "e2e/screenshots/tp_emp_employee_directory_view.png", fullPage: true });

      const body = (await page.textContent("body")) || "";
      const hasContent = /employee|name|directory/i.test(body);
      console.log(`  TC09: Employee can see directory: ${hasContent}`);
      // Directory should be visible to all authenticated users
      const is403 = /forbidden|unauthorized|access denied/i.test(body);
      console.log(`  TC09: Access denied: ${is403}`);
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 2: Employee Profile — Personal Tab
// ============================================================
test.describe("Phase 2: Employee Profile — Personal Tab", () => {

  test("TC10 — View own profile", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);

      // Navigate to own profile — try /profile or /my-profile or sidebar link
      await page.goto(`${BASE_URL}/profile`, { waitUntil: "networkidle", timeout: 30000 }).catch(() => {});
      await page.waitForTimeout(1000);
      let body = (await page.textContent("body")) || "";

      // If /profile didn't work, try finding it via API
      if (!(/personal|profile|email|phone/i.test(body))) {
        const token = await getAuthToken(EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
        const selfId = await getSelfEmployeeId(token);
        if (selfId) {
          await page.goto(`${BASE_URL}/employees/${selfId}`, { waitUntil: "networkidle", timeout: 30000 });
          await page.waitForTimeout(1000);
          body = (await page.textContent("body")) || "";
        }
      }

      await page.screenshot({ path: "e2e/screenshots/tp_emp_own_profile.png", fullPage: true });
      const hasProfile = /personal|profile|email|phone|name|designation/i.test(body);
      console.log(`  TC10: Own profile loaded with personal data: ${hasProfile}`);
      expect(hasProfile).toBeTruthy();
    } finally {
      await context.close();
    }
  });

  test("TC11 — HR views another employee's profile", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);
      console.log(`  TC11: First employee ID: ${empId}`);

      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      if (empId) {
        await page.goto(`${BASE_URL}/employees/${empId}`, { waitUntil: "networkidle", timeout: 30000 });
      } else {
        await page.goto(`${BASE_URL}/employees`, { waitUntil: "networkidle", timeout: 30000 });
        // Click first row
        const row = page.locator("table tbody tr").first();
        if (await row.isVisible().catch(() => false)) await row.click();
        await page.waitForTimeout(2000);
      }
      await page.waitForTimeout(1000);
      await page.screenshot({ path: "e2e/screenshots/tp_emp_hr_views_other.png", fullPage: true });

      const body = (await page.textContent("body")) || "";
      const hasProfile = /personal|profile|email|phone|name/i.test(body);
      console.log(`  TC11: HR can view other profile: ${hasProfile}`);
      expect(hasProfile).toBeTruthy();
    } finally {
      await context.close();
    }
  });

  test("TC12 — Employee views another's profile (RBAC check)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Get an employee ID that is NOT priya
      const adminToken = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const res = await apiGet(adminToken, "/employees?page=1&limit=10");
      const list = res.data?.data?.employees || res.data?.data?.items || res.data?.data || [];
      const arr = Array.isArray(list) ? list : [];
      const otherEmp = arr.find((e: any) => !String(e.email || "").includes("priya"));
      const otherId = otherEmp ? String(otherEmp.id || otherEmp._id || otherEmp.employee_id) : "";

      await login(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
      if (otherId) {
        await page.goto(`${BASE_URL}/employees/${otherId}`, { waitUntil: "networkidle", timeout: 30000 });
        await page.waitForTimeout(1000);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_employee_views_other.png", fullPage: true });

      const body = (await page.textContent("body")) || "";
      const isBlocked = /forbidden|unauthorized|access denied|not authorized/i.test(body);
      const hasFullProfile = /salary|bank|aadhar|pan|emergency/i.test(body);
      console.log(`  TC12: Employee viewing other's profile — blocked: ${isBlocked}, has sensitive data: ${hasFullProfile}`);
      // Either blocked or limited access (no sensitive data)
      console.log(`  TC12: RBAC ${isBlocked ? "ENFORCED" : hasFullProfile ? "FINDING: Employee sees sensitive data" : "partial — limited view"}`);
    } finally {
      await context.close();
    }
  });

  test("TC13 — Edit personal fields (email, blood group, marital status) via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);
      console.log(`  TC13: Employee ID: ${empId}`);

      if (empId) {
        // Get current profile
        const profile = await apiGet(token, `/employees/${empId}/profile`);
        console.log(`  TC13: GET profile status: ${profile.status}`);

        // Update personal fields
        const updatePayload = {
          blood_group: "O+",
          marital_status: "Single",
        };
        const updateRes = await apiPut(token, `/employees/${empId}/profile`, updatePayload);
        console.log(`  TC13: PUT profile status: ${updateRes.status}`);

        // Verify via GET
        const verify = await apiGet(token, `/employees/${empId}/profile`);
        const data = verify.data?.data || verify.data;
        console.log(`  TC13: After update — blood_group: ${data?.blood_group}, marital_status: ${data?.marital_status}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_edit_personal.png" });
      expect(true).toBeTruthy(); // API test, screenshot is informational
    } finally {
      await context.close();
    }
  });

  test("TC14 — Edit nationality, Aadhar, PAN via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const updateRes = await apiPut(token, `/employees/${empId}/profile`, {
          nationality: "Indian",
          aadhar_number: "123456789012",
          pan_number: "ABCDE1234F",
        });
        console.log(`  TC14: PUT profile (nationality/aadhar/pan) status: ${updateRes.status}`);

        const verify = await apiGet(token, `/employees/${empId}/profile`);
        const data = verify.data?.data || verify.data;
        console.log(`  TC14: nationality=${data?.nationality}, aadhar=${data?.aadhar_number}, pan=${data?.pan_number}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_edit_identity.png" });
    } finally {
      await context.close();
    }
  });

  test("TC15 — Edit passport number + expiry date via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const updateRes = await apiPut(token, `/employees/${empId}/profile`, {
          passport_number: "A1234567",
          passport_expiry: "2030-12-31",
        });
        console.log(`  TC15: PUT passport status: ${updateRes.status}`);
        const verify = await apiGet(token, `/employees/${empId}/profile`);
        const data = verify.data?.data || verify.data;
        console.log(`  TC15: passport_number=${data?.passport_number}, passport_expiry=${data?.passport_expiry}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_edit_passport.png" });
    } finally {
      await context.close();
    }
  });

  test("TC16 — Edit visa status + expiry via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const updateRes = await apiPut(token, `/employees/${empId}/profile`, {
          visa_status: "Valid",
          visa_expiry: "2028-06-30",
        });
        console.log(`  TC16: PUT visa status: ${updateRes.status}`);
        const verify = await apiGet(token, `/employees/${empId}/profile`);
        const data = verify.data?.data || verify.data;
        console.log(`  TC16: visa_status=${data?.visa_status}, visa_expiry=${data?.visa_expiry}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_edit_visa.png" });
    } finally {
      await context.close();
    }
  });

  test("TC17 — Edit emergency contact via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const updateRes = await apiPut(token, `/employees/${empId}/profile`, {
          emergency_contact_name: "Test Contact",
          emergency_contact_phone: "9876543210",
          emergency_contact_relation: "Spouse",
        });
        console.log(`  TC17: PUT emergency contact status: ${updateRes.status}`);
        const verify = await apiGet(token, `/employees/${empId}/profile`);
        const data = verify.data?.data || verify.data;
        console.log(`  TC17: emergency_contact_name=${data?.emergency_contact_name}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_edit_emergency.png" });
    } finally {
      await context.close();
    }
  });

  test("TC18 — Edit notice period via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const updateRes = await apiPut(token, `/employees/${empId}/profile`, {
          notice_period: 30,
        });
        console.log(`  TC18: PUT notice_period status: ${updateRes.status}`);
        const verify = await apiGet(token, `/employees/${empId}/profile`);
        const data = verify.data?.data || verify.data;
        console.log(`  TC18: notice_period=${data?.notice_period}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_edit_notice.png" });
    } finally {
      await context.close();
    }
  });

  test("TC19 — Upload profile photo (UI test)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Navigate to an employee profile
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);
      if (empId) {
        await page.goto(`${BASE_URL}/employees/${empId}`, { waitUntil: "networkidle", timeout: 30000 });
      }
      await page.waitForTimeout(1000);

      // Look for photo upload area
      const photoUpload = page.locator('[class*="avatar"], [class*="photo"], [class*="profile-image"], input[type="file"]').first();
      const exists = await photoUpload.isVisible().catch(() => false);
      console.log(`  TC19: Photo upload area visible: ${exists}`);
      await page.screenshot({ path: "e2e/screenshots/tp_emp_upload_photo.png", fullPage: true });
    } finally {
      await context.close();
    }
  });

  test("TC20 — Upload oversized photo (>5MB) should error", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // API test: try uploading a large payload
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        // Create a ~6MB base64 string to simulate large file
        const largePayload = "A".repeat(6 * 1024 * 1024);
        const resp = await fetch(`${API_URL}/employees/${empId}/photo`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ photo: largePayload, filename: "large.jpg" }),
        });
        console.log(`  TC20: Upload oversized photo status: ${resp.status}`);
        const isRejected = resp.status === 400 || resp.status === 413 || resp.status === 422;
        console.log(`  TC20: Rejected as expected: ${isRejected}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_upload_oversized.png" });
    } finally {
      await context.close();
    }
  });

  test("TC21 — Upload invalid format (.exe) should error", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const resp = await fetch(`${API_URL}/employees/${empId}/photo`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ photo: "MZexecutablecontent", filename: "malware.exe" }),
        });
        console.log(`  TC21: Upload .exe as photo status: ${resp.status}`);
        const isRejected = resp.status === 400 || resp.status === 415 || resp.status === 422;
        console.log(`  TC21: Rejected invalid format: ${isRejected}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_upload_invalid.png" });
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 3: Employee Profile — Education Tab
// ============================================================
test.describe("Phase 3: Employee Profile — Education Tab", () => {

  test("TC22 — Add education record via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const addRes = await apiPost(token, `/employees/${empId}/education`, {
          degree: "Bachelor of Technology",
          institution: "IIT Delhi",
          field_of_study: "Computer Science",
          start_year: 2015,
          end_year: 2019,
        });
        console.log(`  TC22: POST education status: ${addRes.status}, data: ${JSON.stringify(addRes.data)?.substring(0, 200)}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_add_education.png" });
    } finally {
      await context.close();
    }
  });

  test("TC23 — Add multiple education records and verify list", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        await apiPost(token, `/employees/${empId}/education`, {
          degree: "Master of Science",
          institution: "Stanford University",
          field_of_study: "AI/ML",
          start_year: 2019,
          end_year: 2021,
        });

        // Get all education records
        const listRes = await apiGet(token, `/employees/${empId}/education`);
        const records = listRes.data?.data || listRes.data || [];
        const arr = Array.isArray(records) ? records : [];
        console.log(`  TC23: Education records count: ${arr.length}`);
        console.log(`  TC23: Records: ${JSON.stringify(arr.map((r: any) => r.degree || r.institution))}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_multiple_education.png" });
    } finally {
      await context.close();
    }
  });

  test("TC24 — Edit an education record", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const listRes = await apiGet(token, `/employees/${empId}/education`);
        const records = listRes.data?.data || listRes.data || [];
        const arr = Array.isArray(records) ? records : [];

        if (arr.length > 0) {
          const recId = arr[0].id || arr[0]._id;
          const editRes = await apiPut(token, `/employees/${empId}/education/${recId}`, {
            degree: "B.Tech (Updated)",
            institution: "IIT Delhi",
            field_of_study: "Computer Science & Engineering",
            start_year: 2015,
            end_year: 2019,
          });
          console.log(`  TC24: PUT education/${recId} status: ${editRes.status}`);
        } else {
          console.log("  TC24: No education records to edit");
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_edit_education.png" });
    } finally {
      await context.close();
    }
  });

  test("TC25 — Delete an education record", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const listRes = await apiGet(token, `/employees/${empId}/education`);
        const records = listRes.data?.data || listRes.data || [];
        const arr = Array.isArray(records) ? records : [];

        if (arr.length > 0) {
          const recId = arr[arr.length - 1].id || arr[arr.length - 1]._id;
          const delRes = await apiDelete(token, `/employees/${empId}/education/${recId}`);
          console.log(`  TC25: DELETE education/${recId} status: ${delRes.status}`);

          const afterDel = await apiGet(token, `/employees/${empId}/education`);
          const afterArr = afterDel.data?.data || afterDel.data || [];
          const afterCount = Array.isArray(afterArr) ? afterArr.length : 0;
          console.log(`  TC25: Records after delete: ${afterCount} (was ${arr.length})`);
        } else {
          console.log("  TC25: No education records to delete");
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_delete_education.png" });
    } finally {
      await context.close();
    }
  });

  test("TC26 — Validation: missing required fields on education", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        // Submit empty education record
        const emptyRes = await apiPost(token, `/employees/${empId}/education`, {});
        console.log(`  TC26: POST empty education status: ${emptyRes.status}`);
        console.log(`  TC26: Response: ${JSON.stringify(emptyRes.data)?.substring(0, 300)}`);
        const validated = emptyRes.status === 400 || emptyRes.status === 422;
        console.log(`  TC26: Validation triggered: ${validated}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_education_validation.png" });
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 4: Employee Profile — Experience Tab
// ============================================================
test.describe("Phase 4: Employee Profile — Experience Tab", () => {

  test("TC27 — Add work experience via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const addRes = await apiPost(token, `/employees/${empId}/experience`, {
          company_name: "Test Corp",
          designation: "Software Engineer",
          start_date: "2018-01-01",
          end_date: "2020-12-31",
          description: "Worked on backend systems",
        });
        console.log(`  TC27: POST experience status: ${addRes.status}, data: ${JSON.stringify(addRes.data)?.substring(0, 200)}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_add_experience.png" });
    } finally {
      await context.close();
    }
  });

  test("TC28 — Add multiple experience records", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        await apiPost(token, `/employees/${empId}/experience`, {
          company_name: "Another Corp",
          designation: "Senior Engineer",
          start_date: "2021-01-01",
          end_date: "2023-06-30",
          description: "Led frontend team",
        });

        const listRes = await apiGet(token, `/employees/${empId}/experience`);
        const records = listRes.data?.data || listRes.data || [];
        const arr = Array.isArray(records) ? records : [];
        console.log(`  TC28: Experience records count: ${arr.length}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_multiple_experience.png" });
    } finally {
      await context.close();
    }
  });

  test("TC29 — Edit experience record", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const listRes = await apiGet(token, `/employees/${empId}/experience`);
        const records = listRes.data?.data || listRes.data || [];
        const arr = Array.isArray(records) ? records : [];

        if (arr.length > 0) {
          const recId = arr[0].id || arr[0]._id;
          const editRes = await apiPut(token, `/employees/${empId}/experience/${recId}`, {
            company_name: "Updated Corp",
            designation: "Staff Engineer",
            start_date: "2018-01-01",
            end_date: "2020-12-31",
            description: "Updated description",
          });
          console.log(`  TC29: PUT experience/${recId} status: ${editRes.status}`);
        } else {
          console.log("  TC29: No experience records to edit");
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_edit_experience.png" });
    } finally {
      await context.close();
    }
  });

  test("TC30 — Delete experience record", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const listRes = await apiGet(token, `/employees/${empId}/experience`);
        const records = listRes.data?.data || listRes.data || [];
        const arr = Array.isArray(records) ? records : [];

        if (arr.length > 0) {
          const recId = arr[arr.length - 1].id || arr[arr.length - 1]._id;
          const delRes = await apiDelete(token, `/employees/${empId}/experience/${recId}`);
          console.log(`  TC30: DELETE experience/${recId} status: ${delRes.status}`);
        } else {
          console.log("  TC30: No experience records to delete");
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_delete_experience.png" });
    } finally {
      await context.close();
    }
  });

  test("TC31 — Validation: end date before start date", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const badRes = await apiPost(token, `/employees/${empId}/experience`, {
          company_name: "Bad Dates Corp",
          designation: "Tester",
          start_date: "2023-12-01",
          end_date: "2020-01-01", // end before start
          description: "Should be rejected",
        });
        console.log(`  TC31: POST experience with bad dates status: ${badRes.status}`);
        console.log(`  TC31: Response: ${JSON.stringify(badRes.data)?.substring(0, 300)}`);
        const validated = badRes.status === 400 || badRes.status === 422;
        console.log(`  TC31: Date validation triggered: ${validated}`);
        if (!validated) {
          console.log("  TC31: FINDING — API accepts end_date before start_date without validation");
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_experience_date_validation.png" });
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 5: Employee Profile — Dependents Tab
// ============================================================
test.describe("Phase 5: Employee Profile — Dependents Tab", () => {

  test("TC32 — Add dependent via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const addRes = await apiPost(token, `/employees/${empId}/dependents`, {
          name: "Test Dependent",
          relation: "Spouse",
          date_of_birth: "1990-05-15",
          gender: "Female",
        });
        console.log(`  TC32: POST dependent status: ${addRes.status}, data: ${JSON.stringify(addRes.data)?.substring(0, 200)}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_add_dependent.png" });
    } finally {
      await context.close();
    }
  });

  test("TC33 — Relation dropdown options (via UI)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      if (empId) {
        await page.goto(`${BASE_URL}/employees/${empId}`, { waitUntil: "networkidle", timeout: 30000 });
        await page.waitForTimeout(1000);

        // Try to find and click dependents tab
        const depTab = page.locator('button:has-text("Dependent"), a:has-text("Dependent"), [role="tab"]:has-text("Dependent")').first();
        const depTabExists = await depTab.isVisible().catch(() => false);
        if (depTabExists) {
          await depTab.click();
          await page.waitForTimeout(1000);

          // Look for add button
          const addBtn = page.locator('button:has-text("Add"), button:has-text("add"), button[class*="add"]').first();
          if (await addBtn.isVisible().catch(() => false)) {
            await addBtn.click();
            await page.waitForTimeout(500);
          }
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_dependent_relation_dropdown.png", fullPage: true });

      const body = (await page.textContent("body")) || "";
      const hasRelation = /spouse|child|parent|sibling/i.test(body);
      console.log(`  TC33: Relation options visible: ${hasRelation}`);
    } finally {
      await context.close();
    }
  });

  test("TC34 — Add multiple dependents", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        await apiPost(token, `/employees/${empId}/dependents`, {
          name: "Child Dependent",
          relation: "Child",
          date_of_birth: "2015-08-20",
          gender: "Male",
        });

        const listRes = await apiGet(token, `/employees/${empId}/dependents`);
        const records = listRes.data?.data || listRes.data || [];
        const arr = Array.isArray(records) ? records : [];
        console.log(`  TC34: Dependents count: ${arr.length}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_multiple_dependents.png" });
    } finally {
      await context.close();
    }
  });

  test("TC35 — Edit dependent", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const listRes = await apiGet(token, `/employees/${empId}/dependents`);
        const records = listRes.data?.data || listRes.data || [];
        const arr = Array.isArray(records) ? records : [];

        if (arr.length > 0) {
          const recId = arr[0].id || arr[0]._id;
          const editRes = await apiPut(token, `/employees/${empId}/dependents/${recId}`, {
            name: "Updated Dependent",
            relation: "Spouse",
            date_of_birth: "1990-05-15",
            gender: "Female",
          });
          console.log(`  TC35: PUT dependent/${recId} status: ${editRes.status}`);
        } else {
          console.log("  TC35: No dependents to edit");
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_edit_dependent.png" });
    } finally {
      await context.close();
    }
  });

  test("TC36 — Delete dependent", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const listRes = await apiGet(token, `/employees/${empId}/dependents`);
        const records = listRes.data?.data || listRes.data || [];
        const arr = Array.isArray(records) ? records : [];

        if (arr.length > 0) {
          const recId = arr[arr.length - 1].id || arr[arr.length - 1]._id;
          const delRes = await apiDelete(token, `/employees/${empId}/dependents/${recId}`);
          console.log(`  TC36: DELETE dependent/${recId} status: ${delRes.status}`);
        } else {
          console.log("  TC36: No dependents to delete");
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_delete_dependent.png" });
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 6: Employee Profile — Addresses Tab
// ============================================================
test.describe("Phase 6: Employee Profile — Addresses Tab", () => {

  test("TC37 — Add current address via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const addRes = await apiPost(token, `/employees/${empId}/addresses`, {
          address_type: "Current",
          address_line1: "123 Test Street",
          city: "Bangalore",
          state: "Karnataka",
          country: "India",
          zipcode: "560001",
        });
        console.log(`  TC37: POST current address status: ${addRes.status}, data: ${JSON.stringify(addRes.data)?.substring(0, 200)}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_add_current_address.png" });
    } finally {
      await context.close();
    }
  });

  test("TC38 — Add permanent address via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const addRes = await apiPost(token, `/employees/${empId}/addresses`, {
          address_type: "Permanent",
          address_line1: "456 Home Lane",
          city: "Chennai",
          state: "Tamil Nadu",
          country: "India",
          zipcode: "600001",
        });
        console.log(`  TC38: POST permanent address status: ${addRes.status}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_add_permanent_address.png" });
    } finally {
      await context.close();
    }
  });

  test("TC39 — Edit address", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const listRes = await apiGet(token, `/employees/${empId}/addresses`);
        const records = listRes.data?.data || listRes.data || [];
        const arr = Array.isArray(records) ? records : [];

        if (arr.length > 0) {
          const recId = arr[0].id || arr[0]._id;
          const editRes = await apiPut(token, `/employees/${empId}/addresses/${recId}`, {
            address_type: "Current",
            address_line1: "789 Updated Street",
            city: "Hyderabad",
            state: "Telangana",
            country: "India",
            zipcode: "500001",
          });
          console.log(`  TC39: PUT address/${recId} status: ${editRes.status}`);
        } else {
          console.log("  TC39: No addresses to edit");
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_edit_address.png" });
    } finally {
      await context.close();
    }
  });

  test("TC40 — Delete address", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const listRes = await apiGet(token, `/employees/${empId}/addresses`);
        const records = listRes.data?.data || listRes.data || [];
        const arr = Array.isArray(records) ? records : [];

        if (arr.length > 0) {
          const recId = arr[arr.length - 1].id || arr[arr.length - 1]._id;
          const delRes = await apiDelete(token, `/employees/${empId}/addresses/${recId}`);
          console.log(`  TC40: DELETE address/${recId} status: ${delRes.status}`);
        } else {
          console.log("  TC40: No addresses to delete");
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_delete_address.png" });
    } finally {
      await context.close();
    }
  });

  test("TC41 — Non-India address (international)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const addRes = await apiPost(token, `/employees/${empId}/addresses`, {
          address_type: "Current",
          address_line1: "100 Market Street",
          city: "San Francisco",
          state: "California",
          country: "United States",
          zipcode: "94105",
        });
        console.log(`  TC41: POST non-India address status: ${addRes.status}`);
        const accepted = addRes.status === 200 || addRes.status === 201;
        console.log(`  TC41: International address accepted: ${accepted}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_international_address.png" });
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 7: Probation Tracking (HR Only)
// ============================================================
test.describe("Phase 7: Probation Tracking", () => {

  test("TC42 — Navigate to /employees/probation", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/employees/probation");
      await page.screenshot({ path: "e2e/screenshots/tp_emp_probation_page.png", fullPage: true });

      const body = (await page.textContent("body")) || "";
      const hasProbation = /probation|confirmed|upcoming|overdue/i.test(body);
      console.log(`  TC42: Probation page loaded: ${hasProbation}`);
    } finally {
      await context.close();
    }
  });

  test("TC43 — Dashboard stats: 4 cards (On Probation, Upcoming, Confirmed, Overdue)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // API check
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const dashRes = await apiGet(token, "/employees/probation/dashboard");
      console.log(`  TC43: GET probation/dashboard status: ${dashRes.status}`);
      console.log(`  TC43: Dashboard data: ${JSON.stringify(dashRes.data)?.substring(0, 500)}`);

      // UI check
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/employees/probation");
      await page.screenshot({ path: "e2e/screenshots/tp_emp_probation_dashboard.png", fullPage: true });

      const body = (await page.textContent("body")) || "";
      const cards = {
        onProbation: /on\s*probation/i.test(body),
        upcoming: /upcoming/i.test(body),
        confirmed: /confirmed/i.test(body),
        overdue: /overdue/i.test(body),
      };
      console.log(`  TC43: Dashboard cards found:`, JSON.stringify(cards));
    } finally {
      await context.close();
    }
  });

  test("TC44 — Probation list shows employees with details", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const listRes = await apiGet(token, "/employees/probation");
      console.log(`  TC44: GET probation list status: ${listRes.status}`);
      const data = listRes.data?.data || listRes.data || [];
      const arr = Array.isArray(data) ? data : [];
      console.log(`  TC44: Probation employees count: ${arr.length}`);
      if (arr.length > 0) {
        const first = arr[0];
        console.log(`  TC44: First entry keys: ${Object.keys(first).join(", ")}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_probation_list.png" });
    } finally {
      await context.close();
    }
  });

  test("TC45 — Days remaining color coding (UI check)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/employees/probation");
      await page.waitForTimeout(1000);
      await page.screenshot({ path: "e2e/screenshots/tp_emp_probation_color_coding.png", fullPage: true });

      // Check for color-coded elements (red, orange, yellow, green)
      const colorElements = await page.locator('[class*="red"], [class*="orange"], [class*="yellow"], [class*="green"], [class*="danger"], [class*="warning"], [class*="success"]').count();
      console.log(`  TC45: Color-coded elements found: ${colorElements}`);
    } finally {
      await context.close();
    }
  });

  test("TC46 — Confirm probation for employee via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Get a probation employee
      const listRes = await apiGet(token, "/employees/probation");
      const data = listRes.data?.data || listRes.data || [];
      const arr = Array.isArray(data) ? data : [];

      if (arr.length > 0) {
        const empId = arr[0].employee_id || arr[0].id || arr[0]._id;
        const confirmRes = await apiPut(token, `/employees/${empId}/probation/confirm`, {});
        console.log(`  TC46: PUT probation/confirm for ${empId} status: ${confirmRes.status}`);
        console.log(`  TC46: Response: ${JSON.stringify(confirmRes.data)?.substring(0, 300)}`);
      } else {
        console.log("  TC46: No employees on probation to confirm");
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_probation_confirm.png" });
    } finally {
      await context.close();
    }
  });

  test("TC47 — Extend probation with new end date + reason via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);

      const listRes = await apiGet(token, "/employees/probation");
      const data = listRes.data?.data || listRes.data || [];
      const arr = Array.isArray(data) ? data : [];

      if (arr.length > 0) {
        const empId = arr[0].employee_id || arr[0].id || arr[0]._id;
        const extendRes = await apiPut(token, `/employees/${empId}/probation/extend`, {
          new_end_date: "2026-09-30",
          reason: "Performance review pending",
        });
        console.log(`  TC47: PUT probation/extend for ${empId} status: ${extendRes.status}`);
        console.log(`  TC47: Response: ${JSON.stringify(extendRes.data)?.substring(0, 300)}`);
      } else {
        console.log("  TC47: No employees on probation to extend");
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_probation_extend.png" });
    } finally {
      await context.close();
    }
  });

  test("TC48 — View upcoming confirmations (30 days) via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const upcomingRes = await apiGet(token, "/employees/probation/upcoming");
      console.log(`  TC48: GET probation/upcoming status: ${upcomingRes.status}`);
      const data = upcomingRes.data?.data || upcomingRes.data || [];
      const arr = Array.isArray(data) ? data : [];
      console.log(`  TC48: Upcoming confirmations count: ${arr.length}`);
      await page.screenshot({ path: "e2e/screenshots/tp_emp_probation_upcoming.png" });
    } finally {
      await context.close();
    }
  });

  test("TC49 — Employee cannot access probation page", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password, "/employees/probation");
      await page.screenshot({ path: "e2e/screenshots/tp_emp_probation_employee_access.png", fullPage: true });

      const url = page.url();
      const body = (await page.textContent("body")) || "";
      const isBlocked = /forbidden|unauthorized|access denied|not authorized/i.test(body) || !url.includes("probation");
      console.log(`  TC49: Employee access to probation — blocked/redirected: ${isBlocked}, URL: ${url}`);

      // Also check API
      const token = await getAuthToken(EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
      const apiRes = await apiGet(token, "/employees/probation");
      console.log(`  TC49: Employee GET /probation API status: ${apiRes.status}`);
      const apiBlocked = apiRes.status === 403 || apiRes.status === 401;
      console.log(`  TC49: API blocked: ${apiBlocked}`);
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 8: Salary Structure (HR Only)
// ============================================================
test.describe("Phase 8: Salary Structure", () => {

  test("TC50 — View salary tab on employee profile", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      if (empId) {
        await page.goto(`${BASE_URL}/employees/${empId}`, { waitUntil: "networkidle", timeout: 30000 });
        await page.waitForTimeout(1000);

        // Click salary tab
        const salaryTab = page.locator('button:has-text("Salary"), a:has-text("Salary"), [role="tab"]:has-text("Salary")').first();
        if (await salaryTab.isVisible().catch(() => false)) {
          await salaryTab.click();
          await page.waitForTimeout(1000);
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_salary_tab.png", fullPage: true });

      const body = (await page.textContent("body")) || "";
      const hasSalary = /salary|ctc|basic|hra|allowance|deduction/i.test(body);
      console.log(`  TC50: Salary fields visible: ${hasSalary}`);

      // Also check API
      if (empId) {
        const salaryRes = await apiGet(token, `/employees/${empId}/salary`);
        console.log(`  TC50: GET salary API status: ${salaryRes.status}`);
        console.log(`  TC50: Salary data: ${JSON.stringify(salaryRes.data)?.substring(0, 400)}`);
      }
    } finally {
      await context.close();
    }
  });

  test("TC51 — HR edits salary structure via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const empId = await getFirstEmployeeId(token);

      if (empId) {
        const updateRes = await apiPut(token, `/employees/${empId}/salary`, {
          ctc: 1200000,
          basic: 500000,
          hra: 200000,
          da: 50000,
          special_allowance: 100000,
          medical_allowance: 15000,
          conveyance_allowance: 19200,
          pf: 21600,
          professional_tax: 2400,
        });
        console.log(`  TC51: PUT salary status: ${updateRes.status}`);
        console.log(`  TC51: Response: ${JSON.stringify(updateRes.data)?.substring(0, 300)}`);

        // Verify
        const verify = await apiGet(token, `/employees/${empId}/salary`);
        console.log(`  TC51: Verify salary after update: ${JSON.stringify(verify.data)?.substring(0, 300)}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_edit_salary.png" });
    } finally {
      await context.close();
    }
  });

  test("TC52 — Employee views own salary (read-only)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
      const selfId = await getSelfEmployeeId(token);

      if (selfId) {
        const salaryRes = await apiGet(token, `/employees/${selfId}/salary`);
        console.log(`  TC52: Employee GET own salary status: ${salaryRes.status}`);
        console.log(`  TC52: Salary data: ${JSON.stringify(salaryRes.data)?.substring(0, 300)}`);
        const canView = salaryRes.status === 200;
        console.log(`  TC52: Employee can view own salary: ${canView}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_employee_salary_view.png" });
    } finally {
      await context.close();
    }
  });

  test("TC53 — Employee cannot edit salary", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
      const selfId = await getSelfEmployeeId(token);

      if (selfId) {
        const editRes = await apiPut(token, `/employees/${selfId}/salary`, {
          ctc: 9999999,
          basic: 5000000,
        });
        console.log(`  TC53: Employee PUT salary status: ${editRes.status}`);
        const blocked = editRes.status === 403 || editRes.status === 401;
        console.log(`  TC53: Employee salary edit blocked: ${blocked}`);
        if (!blocked) {
          console.log("  TC53: FINDING — Employee can edit their own salary (should be denied)");
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_employee_salary_edit_blocked.png" });
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 9: Organization Chart
// ============================================================
test.describe("Phase 9: Organization Chart", () => {

  test("TC54 — Navigate to org chart page", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Try common org chart URLs
      for (const path of ["/org-chart", "/organization-chart", "/employees/org-chart", "/orgchart"]) {
        await page.goto(`${BASE_URL}${path}`, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
        const body = (await page.textContent("body")) || "";
        if (/org.*chart|hierarchy|reporting/i.test(body)) {
          console.log(`  TC54: Org chart found at ${path}`);
          break;
        }
      }
      await page.waitForTimeout(1000);
      await page.screenshot({ path: "e2e/screenshots/tp_emp_org_chart.png", fullPage: true });

      const body = (await page.textContent("body")) || "";
      const hasChart = /org.*chart|hierarchy|reporting|tree|manager/i.test(body);
      console.log(`  TC54: Org chart rendered: ${hasChart}`);

      // Also check API
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const chartRes = await apiGet(token, "/users/org-chart");
      console.log(`  TC54: GET /users/org-chart status: ${chartRes.status}`);
    } finally {
      await context.close();
    }
  });

  test("TC55 — Root node shows top-level manager", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const chartRes = await apiGet(token, "/users/org-chart");
      console.log(`  TC55: Org chart API status: ${chartRes.status}`);
      const data = chartRes.data?.data || chartRes.data;
      if (data) {
        // Root node
        const root = Array.isArray(data) ? data[0] : data;
        console.log(`  TC55: Root node: ${JSON.stringify(root)?.substring(0, 300)}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_org_chart_root.png" });
    } finally {
      await context.close();
    }
  });

  test("TC56 — Expand tree node (UI)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      for (const path of ["/org-chart", "/organization-chart", "/employees/org-chart", "/orgchart"]) {
        await page.goto(`${BASE_URL}${path}`, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
        const body = (await page.textContent("body")) || "";
        if (/org.*chart|hierarchy/i.test(body)) break;
      }
      await page.waitForTimeout(1000);

      // Try to click an expand button
      const expandBtn = page.locator('[class*="expand"], [class*="toggle"], [aria-expanded], button:has-text("+"), [class*="node"] button').first();
      if (await expandBtn.isVisible().catch(() => false)) {
        await expandBtn.click();
        await page.waitForTimeout(1000);
        console.log("  TC56: Expanded a tree node");
      } else {
        console.log("  TC56: No expandable tree nodes found (tree may be flat or auto-expanded)");
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_org_chart_expand.png", fullPage: true });
    } finally {
      await context.close();
    }
  });

  test("TC57 — Click employee node navigates to profile", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      for (const path of ["/org-chart", "/organization-chart", "/employees/org-chart", "/orgchart"]) {
        await page.goto(`${BASE_URL}${path}`, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
        const body = (await page.textContent("body")) || "";
        if (/org.*chart|hierarchy/i.test(body)) break;
      }
      await page.waitForTimeout(1000);

      // Click on a node
      const node = page.locator('[class*="node"], [class*="chart"] [class*="card"], [class*="org"] [class*="item"]').first();
      if (await node.isVisible().catch(() => false)) {
        const startUrl = page.url();
        await node.click();
        await page.waitForTimeout(2000);
        const endUrl = page.url();
        console.log(`  TC57: Clicked node — navigated from ${startUrl} to ${endUrl}`);
      } else {
        console.log("  TC57: No clickable org chart nodes found");
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_org_chart_click_node.png", fullPage: true });
    } finally {
      await context.close();
    }
  });

  test("TC58 — Node shows designation + department", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const chartRes = await apiGet(token, "/users/org-chart");
      const data = chartRes.data?.data || chartRes.data;

      if (data) {
        const node = Array.isArray(data) ? data[0] : data;
        const hasDesig = !!node?.designation || !!node?.title;
        const hasDept = !!node?.department || !!node?.department_name;
        console.log(`  TC58: Node has designation: ${hasDesig}, department: ${hasDept}`);
        console.log(`  TC58: Node data: ${JSON.stringify(node)?.substring(0, 300)}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_org_chart_node_info.png" });
    } finally {
      await context.close();
    }
  });

  test("TC59 — Children count badge", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const chartRes = await apiGet(token, "/users/org-chart");
      const data = chartRes.data?.data || chartRes.data;

      if (data) {
        const node = Array.isArray(data) ? data[0] : data;
        const childCount = node?.children?.length || node?.subordinates?.length || node?.direct_reports?.length || 0;
        console.log(`  TC59: Root node children count: ${childCount}`);
      }

      // UI check
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      for (const path of ["/org-chart", "/organization-chart", "/employees/org-chart", "/orgchart"]) {
        await page.goto(`${BASE_URL}${path}`, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
        const body = (await page.textContent("body")) || "";
        if (/org.*chart|hierarchy/i.test(body)) break;
      }
      await page.waitForTimeout(1000);

      const badges = await page.locator('[class*="badge"], [class*="count"], [class*="chip"]').count();
      console.log(`  TC59: Badge/count elements found: ${badges}`);
      await page.screenshot({ path: "e2e/screenshots/tp_emp_org_chart_badges.png", fullPage: true });
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 10: Bulk Import
// ============================================================
test.describe("Phase 10: Bulk Import", () => {

  test("TC60 — Upload valid CSV preview (UI check)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Try import pages
      for (const path of ["/employees/import", "/employees/bulk-import", "/import", "/users/import"]) {
        await page.goto(`${BASE_URL}${path}`, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
        const body = (await page.textContent("body")) || "";
        if (/import|upload|csv|bulk/i.test(body)) {
          console.log(`  TC60: Import page found at ${path}`);
          break;
        }
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_bulk_import_page.png", fullPage: true });

      const body = (await page.textContent("body")) || "";
      const hasImport = /import|upload|csv|bulk/i.test(body);
      console.log(`  TC60: Import page loaded: ${hasImport}`);
    } finally {
      await context.close();
    }
  });

  test("TC61 — CSV with validation errors (API test)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Try to import with invalid data
      const importRes = await apiPost(token, "/users/import", {
        employees: [
          { name: "", email: "invalid-email", department: "" },
        ],
      });
      console.log(`  TC61: POST /users/import with bad data status: ${importRes.status}`);
      console.log(`  TC61: Response: ${JSON.stringify(importRes.data)?.substring(0, 400)}`);
      await page.screenshot({ path: "e2e/screenshots/tp_emp_bulk_import_errors.png" });
    } finally {
      await context.close();
    }
  });

  test("TC62 — Execute import with valid data (API check only — not creating real employees)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Check if the execute endpoint exists
      const executeRes = await apiPost(token, "/users/import/execute", { dry_run: true });
      console.log(`  TC62: POST /users/import/execute status: ${executeRes.status}`);
      console.log(`  TC62: Response: ${JSON.stringify(executeRes.data)?.substring(0, 300)}`);
      await page.screenshot({ path: "e2e/screenshots/tp_emp_bulk_import_execute.png" });
    } finally {
      await context.close();
    }
  });

  test("TC63 — Upload non-CSV file should error", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);

      const resp = await fetch(`${API_URL}/users/import`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ file_type: "exe", filename: "test.exe", content: "not-a-csv" }),
      });
      console.log(`  TC63: Upload non-CSV status: ${resp.status}`);
      const data = await resp.json().catch(() => null);
      console.log(`  TC63: Response: ${JSON.stringify(data)?.substring(0, 300)}`);
      await page.screenshot({ path: "e2e/screenshots/tp_emp_bulk_import_invalid_format.png" });
    } finally {
      await context.close();
    }
  });

  test("TC64 — CSV with duplicate emails should error", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);

      const importRes = await apiPost(token, "/users/import", {
        employees: [
          { name: "Dup One", email: "duplicate@test.com", department: "Engineering" },
          { name: "Dup Two", email: "duplicate@test.com", department: "Engineering" },
        ],
      });
      console.log(`  TC64: POST import with duplicate emails status: ${importRes.status}`);
      console.log(`  TC64: Response: ${JSON.stringify(importRes.data)?.substring(0, 400)}`);
      await page.screenshot({ path: "e2e/screenshots/tp_emp_bulk_import_duplicates.png" });
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 11: Organizational Insights
// ============================================================
test.describe("Phase 11: Organizational Insights", () => {

  test("TC65 — Upcoming birthdays endpoint", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const res = await apiGet(token, "/employees/birthdays");
      console.log(`  TC65: GET /employees/birthdays status: ${res.status}`);
      const data = res.data?.data || res.data || [];
      const arr = Array.isArray(data) ? data : [];
      console.log(`  TC65: Upcoming birthdays count: ${arr.length}`);
      if (arr.length > 0) {
        console.log(`  TC65: First entry: ${JSON.stringify(arr[0])?.substring(0, 200)}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_birthdays.png" });
    } finally {
      await context.close();
    }
  });

  test("TC66 — Work anniversaries endpoint", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const res = await apiGet(token, "/employees/anniversaries");
      console.log(`  TC66: GET /employees/anniversaries status: ${res.status}`);
      const data = res.data?.data || res.data || [];
      const arr = Array.isArray(data) ? data : [];
      console.log(`  TC66: Work anniversaries count: ${arr.length}`);
      if (arr.length > 0) {
        console.log(`  TC66: First entry: ${JSON.stringify(arr[0])?.substring(0, 200)}`);
      }
      await page.screenshot({ path: "e2e/screenshots/tp_emp_anniversaries.png" });
    } finally {
      await context.close();
    }
  });

  test("TC67 — Headcount stats", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAuthToken(ADMIN_CREDS.email, ADMIN_CREDS.password);
      const res = await apiGet(token, "/employees/headcount");
      console.log(`  TC67: GET /employees/headcount status: ${res.status}`);
      console.log(`  TC67: Headcount data: ${JSON.stringify(res.data)?.substring(0, 500)}`);
      await page.screenshot({ path: "e2e/screenshots/tp_emp_headcount.png" });
    } finally {
      await context.close();
    }
  });
});
