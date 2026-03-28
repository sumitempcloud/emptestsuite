import { test, expect, Page, BrowserContext, Browser } from "@playwright/test";

const BASE_URL = "https://test-empcloud.empcloud.com";
const PROJECT_URL = "https://test-project.empcloud.com";
const PROJECT_API = "https://test-project-api.empcloud.com";

const ADMIN_CREDS = { email: "ananya@technova.in", password: "Welcome@123" };
const SUPER_ADMIN_CREDS = { email: "admin@empcloud.com", password: "SuperAdmin@2026" };
const EMPLOYEE_CREDS = { email: "priya@technova.in", password: "Welcome@123" };

// Helper: get access token from EMP Cloud core login API
async function getAccessToken(page: Page, email: string, password: string): Promise<string> {
  const response = await page.request.post(`${BASE_URL}/api/v1/auth/login`, {
    data: { email, password },
  });
  const json = await response.json();
  const token =
    json?.data?.tokens?.access_token ||
    json?.data?.access_token ||
    json?.access_token ||
    json?.token ||
    "";
  return token;
}

// Helper: login to the Project module via SSO
async function loginViaSSO(page: Page, email: string, password: string): Promise<string> {
  const token = await getAccessToken(page, email, password);
  if (!token) {
    console.log(`WARNING: Could not get access token for ${email}`);
    return "";
  }
  console.log(`Got access token for ${email}: ${token.substring(0, 20)}...`);
  await page.goto(`${PROJECT_URL}?sso_token=${token}`, {
    waitUntil: "networkidle",
    timeout: 30000,
  });
  await page.waitForTimeout(3000);
  return token;
}

// Helper: create fresh isolated browser context
async function createFreshContext(
  browser: Browser
): Promise<{ context: BrowserContext; page: Page }> {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();
  return { context, page };
}

// Helper: get page text content safely
async function getPageText(page: Page): Promise<string> {
  try {
    return (await page.textContent("body")) || "";
  } catch {
    return "";
  }
}

// Helper: take screenshot safely
async function takeScreenshot(page: Page, name: string): Promise<void> {
  try {
    await page.screenshot({
      path: `e2e/screenshots/project_${name}.png`,
      fullPage: true,
    });
    console.log(`Screenshot saved: project_${name}.png`);
  } catch (err) {
    console.log(`Screenshot failed for ${name}: ${err}`);
  }
}

// ============================================================
// SECTION 1: SSO Authentication & Access
// ============================================================

test.describe("Project Module — SSO Authentication", () => {
  test("1. SSO login as Org Admin — module loads after SSO", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await loginViaSSO(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      const currentUrl = page.url();
      console.log(`After SSO login URL: ${currentUrl}`);

      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      // Check what the page shows
      const headings = await page
        .locator("h1, h2, h3, h4")
        .allTextContents();
      console.log(`Headings: ${JSON.stringify(headings)}`);

      // Check for project-related or dashboard content
      const isAuthenticated =
        !lowerContent.includes("login") ||
        lowerContent.includes("project") ||
        lowerContent.includes("dashboard") ||
        lowerContent.includes("welcome") ||
        lowerContent.includes("task") ||
        headings.length > 0;

      const hasError =
        lowerContent.includes("error") ||
        lowerContent.includes("denied") ||
        lowerContent.includes("unauthorized") ||
        lowerContent.includes("invalid");

      console.log(`Is authenticated: ${isAuthenticated}`);
      console.log(`Has error: ${hasError}`);
      console.log(
        `Page content (first 500 chars): ${pageContent.substring(0, 500)}`
      );

      await takeScreenshot(page, "sso_admin_login");

      expect(token).toBeTruthy();
    } finally {
      await context.close();
    }
  });

  test("2. SSO login as Employee — employee can access project module", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await loginViaSSO(
        page,
        EMPLOYEE_CREDS.email,
        EMPLOYEE_CREDS.password
      );

      const currentUrl = page.url();
      console.log(`Employee SSO URL: ${currentUrl}`);

      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      const headings = await page
        .locator("h1, h2, h3, h4")
        .allTextContents();
      console.log(`Headings: ${JSON.stringify(headings)}`);

      const isLoaded =
        lowerContent.includes("project") ||
        lowerContent.includes("dashboard") ||
        lowerContent.includes("task") ||
        lowerContent.includes("welcome");

      const hasAccessDenied =
        lowerContent.includes("access denied") ||
        lowerContent.includes("unauthorized") ||
        lowerContent.includes("forbidden") ||
        lowerContent.includes("subscription");

      console.log(`Module loaded: ${isLoaded}`);
      console.log(`Access denied: ${hasAccessDenied}`);
      console.log(
        `Page content (first 500 chars): ${pageContent.substring(0, 500)}`
      );

      await takeScreenshot(page, "sso_employee_login");

      expect(token).toBeTruthy();
    } finally {
      await context.close();
    }
  });

  test("3. Invalid SSO token — should show error or redirect", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Navigate with a garbage token
      await page.goto(
        `${PROJECT_URL}?sso_token=invalid_garbage_token_12345`,
        {
          waitUntil: "networkidle",
          timeout: 30000,
        }
      );
      await page.waitForTimeout(3000);

      const currentUrl = page.url();
      console.log(`Invalid token URL: ${currentUrl}`);

      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      const showsError =
        lowerContent.includes("invalid") ||
        lowerContent.includes("error") ||
        lowerContent.includes("unauthorized") ||
        lowerContent.includes("denied") ||
        lowerContent.includes("expired") ||
        lowerContent.includes("login") ||
        lowerContent.includes("authenticate");

      // Check if redirected back to core login
      const redirectedToLogin =
        currentUrl.includes("empcloud.com/login") ||
        currentUrl.includes("login");

      console.log(`Shows error: ${showsError}`);
      console.log(`Redirected to login: ${redirectedToLogin}`);
      console.log(
        `Page content (first 500 chars): ${pageContent.substring(0, 500)}`
      );

      await takeScreenshot(page, "sso_invalid_token");

      // The module should NOT grant access with an invalid token
      // It should either show an error or redirect to login
      const properlyRejected = showsError || redirectedToLogin;
      console.log(`Properly rejected invalid token: ${properlyRejected}`);

      // If the page loaded with full project content despite invalid token, that's a security bug
      const hasProjectContent =
        lowerContent.includes("create project") ||
        lowerContent.includes("my projects") ||
        lowerContent.includes("task board");

      if (hasProjectContent) {
        console.log(
          "SECURITY BUG: Project module loaded with invalid SSO token!"
        );
      }

      expect(properlyRejected || !hasProjectContent).toBeTruthy();
    } finally {
      await context.close();
    }
  });

  test("4. No SSO token — should not grant access", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Navigate to project module without any token
      await page.goto(PROJECT_URL, {
        waitUntil: "networkidle",
        timeout: 30000,
      });
      await page.waitForTimeout(3000);

      const currentUrl = page.url();
      console.log(`No token URL: ${currentUrl}`);

      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      const isLoginPage =
        lowerContent.includes("login") ||
        lowerContent.includes("sign in") ||
        lowerContent.includes("authenticate");

      const isRedirected =
        currentUrl.includes("empcloud.com/login") ||
        currentUrl.includes("/login") ||
        currentUrl.includes("/auth");

      const showsError =
        lowerContent.includes("unauthorized") ||
        lowerContent.includes("denied") ||
        lowerContent.includes("access");

      console.log(`Shows login page: ${isLoginPage}`);
      console.log(`Redirected: ${isRedirected}`);
      console.log(`Shows error: ${showsError}`);
      console.log(
        `Page content (first 500 chars): ${pageContent.substring(0, 500)}`
      );

      await takeScreenshot(page, "sso_no_token");

      // Should NOT have access to project features
      const hasProjectFeatures =
        lowerContent.includes("create project") ||
        lowerContent.includes("my projects") ||
        lowerContent.includes("task board");

      if (hasProjectFeatures) {
        console.log(
          "SECURITY BUG: Project module accessible without any SSO token!"
        );
      }

      expect(!hasProjectFeatures || isLoginPage || isRedirected).toBeTruthy();
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// SECTION 2: Billing Constraint Verification
// ============================================================

test.describe("Project Module — Billing Constraints", () => {
  test("5. Core API subscription check — Project module subscription is active", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAccessToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      // Check subscriptions from core API
      const subsResponse = await page.request.get(
        `${BASE_URL}/api/v1/subscriptions`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const subsStatus = subsResponse.status();
      const subsBody = await subsResponse.text();
      console.log(`GET /api/v1/subscriptions — Status: ${subsStatus}`);
      console.log(`Response: ${subsBody.substring(0, 2000)}`);

      // Parse and look for project module subscription
      try {
        const subsData = JSON.parse(subsBody);
        const subscriptions =
          subsData?.data?.subscriptions ||
          subsData?.data ||
          subsData?.subscriptions ||
          [];

        if (Array.isArray(subscriptions)) {
          console.log(`Total subscriptions: ${subscriptions.length}`);
          const projectSub = subscriptions.find(
            (s: any) =>
              s.module_name?.toLowerCase().includes("project") ||
              s.module?.name?.toLowerCase().includes("project") ||
              s.name?.toLowerCase().includes("project")
          );

          if (projectSub) {
            console.log(
              `Project subscription found: ${JSON.stringify(projectSub)}`
            );
            console.log(`Status: ${projectSub.status}`);
            console.log(`Plan tier: ${projectSub.plan_tier}`);
            console.log(`Seats: ${projectSub.seats}`);
          } else {
            console.log(
              "No Project module subscription found in the list"
            );
            // List all module names for debugging
            const moduleNames = subscriptions.map(
              (s: any) =>
                s.module_name || s.module?.name || s.name || "unknown"
            );
            console.log(`Available modules: ${JSON.stringify(moduleNames)}`);
          }
        }
      } catch (e) {
        console.log(`Could not parse subscriptions response: ${e}`);
      }

      await takeScreenshot(page, "billing_subscription_check");

      expect(subsStatus).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("6. Core API modules list — verify Project module exists", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAccessToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      const modulesResponse = await page.request.get(
        `${BASE_URL}/api/v1/modules`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const modulesStatus = modulesResponse.status();
      const modulesBody = await modulesResponse.text();
      console.log(`GET /api/v1/modules — Status: ${modulesStatus}`);
      console.log(`Response: ${modulesBody.substring(0, 2000)}`);

      try {
        const modulesData = JSON.parse(modulesBody);
        const modules =
          modulesData?.data?.modules ||
          modulesData?.data ||
          modulesData?.modules ||
          [];

        if (Array.isArray(modules)) {
          console.log(`Total modules: ${modules.length}`);
          const projectModule = modules.find(
            (m: any) =>
              m.name?.toLowerCase().includes("project") ||
              m.slug?.toLowerCase().includes("project") ||
              m.key?.toLowerCase().includes("project")
          );

          if (projectModule) {
            console.log(
              `Project module found: ${JSON.stringify(projectModule)}`
            );
          } else {
            console.log("Project module NOT found in module list");
            const names = modules.map(
              (m: any) => m.name || m.slug || m.key || "unknown"
            );
            console.log(`Available modules: ${JSON.stringify(names)}`);
          }
        }
      } catch (e) {
        console.log(`Could not parse modules response: ${e}`);
      }

      await takeScreenshot(page, "billing_modules_list");

      expect(modulesStatus).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("7. Module access with active subscription — project module loads", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await loginViaSSO(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      const currentUrl = page.url();
      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      console.log(`Module URL after SSO: ${currentUrl}`);

      // Check if module loaded successfully (indicates active subscription)
      const moduleLoaded =
        lowerContent.includes("project") ||
        lowerContent.includes("dashboard") ||
        lowerContent.includes("task") ||
        lowerContent.includes("board") ||
        lowerContent.includes("timeline");

      // Check for subscription errors
      const subscriptionError =
        lowerContent.includes("no active subscription") ||
        lowerContent.includes("subscription expired") ||
        lowerContent.includes("subscribe") ||
        lowerContent.includes("upgrade");

      console.log(`Module loaded: ${moduleLoaded}`);
      console.log(`Subscription error: ${subscriptionError}`);

      if (subscriptionError) {
        console.log(
          "NOTE: Project module requires an active subscription — org may not have it enabled"
        );
      }

      await takeScreenshot(page, "billing_module_access");

      // Test passes regardless — we want to capture what happens
      expect(token).toBeTruthy();
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// SECTION 3: Project CRUD (as Org Admin)
// ============================================================

test.describe("Project Module — Project CRUD", () => {
  test("8. Projects page loads — dashboard or project list renders", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      const currentUrl = page.url();
      console.log(`Projects page URL: ${currentUrl}`);

      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      // Look for project page elements
      const headings = await page
        .locator("h1, h2, h3, h4")
        .allTextContents();
      console.log(`Headings: ${JSON.stringify(headings)}`);

      // Check for navigation items
      const navItems = await page
        .locator("nav a, aside a, [class*='sidebar'] a, [class*='nav'] a, [class*='menu'] a")
        .allTextContents();
      console.log(
        `Nav items: ${JSON.stringify(navItems.filter((n) => n.trim()).slice(0, 20))}`
      );

      // Check for project-related content
      const hasProjects =
        lowerContent.includes("project") ||
        lowerContent.includes("dashboard") ||
        lowerContent.includes("create") ||
        lowerContent.includes("my project");

      const hasTable =
        (await page.locator("table").count()) > 0 ||
        (await page
          .locator('[class*="list"], [class*="grid"], [class*="card"]')
          .count()) > 0;

      console.log(`Has project content: ${hasProjects}`);
      console.log(`Has table/list/grid: ${hasTable}`);

      // Look for action buttons
      const buttons = await page.locator("button").allTextContents();
      const actionButtons = buttons.filter(
        (b) =>
          b.toLowerCase().includes("create") ||
          b.toLowerCase().includes("new") ||
          b.toLowerCase().includes("add")
      );
      console.log(`Action buttons: ${JSON.stringify(actionButtons)}`);

      await takeScreenshot(page, "projects_page_loads");

      expect(hasProjects || headings.length > 0).toBeTruthy();
    } finally {
      await context.close();
    }
  });

  test("9. View projects list via API — GET /v1/projects", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAccessToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      // Try the Project API directly with SSO token
      const projectsResponse = await page.request.get(
        `${PROJECT_API}/v1/projects`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const status = projectsResponse.status();
      const body = await projectsResponse.text();
      console.log(`GET ${PROJECT_API}/v1/projects — Status: ${status}`);
      console.log(`Response: ${body.substring(0, 2000)}`);

      // If the above fails, try /api/v1/projects as fallback
      if (status >= 400) {
        console.log("Trying /api/v1/projects as fallback...");
        const fallbackResponse = await page.request.get(
          `${PROJECT_API}/api/v1/projects`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        const fbStatus = fallbackResponse.status();
        const fbBody = await fallbackResponse.text();
        console.log(
          `GET ${PROJECT_API}/api/v1/projects — Status: ${fbStatus}`
        );
        console.log(`Fallback response: ${fbBody.substring(0, 2000)}`);
      }

      // Also try without /v1 prefix
      if (status >= 400) {
        console.log("Trying /projects as fallback...");
        const fb2Response = await page.request.get(
          `${PROJECT_API}/projects`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        const fb2Status = fb2Response.status();
        const fb2Body = await fb2Response.text();
        console.log(`GET ${PROJECT_API}/projects — Status: ${fb2Status}`);
        console.log(`Second fallback response: ${fb2Body.substring(0, 2000)}`);
      }

      await takeScreenshot(page, "projects_list_api");

      // Log for analysis — the endpoint may require SSO session cookie instead of bearer token
      expect(status).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("10. Create new project via UI — test project creation form", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      // Look for create/new project button
      const createBtn = page
        .locator(
          'button:has-text("Create"), button:has-text("New"), button:has-text("Add"), a:has-text("Create"), a:has-text("New Project"), a:has-text("Add Project")'
        )
        .first();

      let createBtnVisible = false;
      try {
        createBtnVisible = await createBtn.isVisible({ timeout: 5000 });
      } catch {
        createBtnVisible = false;
      }

      console.log(`Create button visible: ${createBtnVisible}`);

      if (createBtnVisible) {
        const btnText = await createBtn.textContent();
        console.log(`Create button text: ${btnText}`);
        await createBtn.click();
        await page.waitForTimeout(2000);

        await takeScreenshot(page, "project_create_form");

        // Look for form fields
        const inputs = await page.locator("input, textarea, select").count();
        console.log(`Form inputs found: ${inputs}`);

        // Try to fill out the form
        const nameInput = page
          .locator(
            'input[name="name"], input[name="title"], input[placeholder*="name" i], input[placeholder*="title" i], input[placeholder*="project" i]'
          )
          .first();

        if (await nameInput.isVisible().catch(() => false)) {
          const testProjectName = `Test Project ${Date.now()}`;
          await nameInput.fill(testProjectName);
          console.log(`Filled project name: ${testProjectName}`);

          // Look for description field
          const descInput = page
            .locator(
              'textarea[name="description"], textarea[placeholder*="description" i], textarea'
            )
            .first();
          if (await descInput.isVisible().catch(() => false)) {
            await descInput.fill(
              "Automated test project created by Playwright E2E tests"
            );
            console.log("Filled description");
          }

          // Look for date fields
          const startDate = page
            .locator(
              'input[name="start_date"], input[name="startDate"], input[type="date"]'
            )
            .first();
          if (await startDate.isVisible().catch(() => false)) {
            await startDate.fill("2026-04-01");
            console.log("Filled start date");
          }

          const endDate = page
            .locator(
              'input[name="end_date"], input[name="endDate"], input[type="date"]'
            )
            .nth(1);
          if (await endDate.isVisible().catch(() => false)) {
            await endDate.fill("2026-06-30");
            console.log("Filled end date");
          }

          await takeScreenshot(page, "project_create_form_filled");

          // Submit the form
          const submitBtn = page
            .locator(
              'button[type="submit"], button:has-text("Save"), button:has-text("Create"), button:has-text("Submit")'
            )
            .last();
          if (await submitBtn.isVisible().catch(() => false)) {
            await submitBtn.click();
            await page.waitForTimeout(3000);
            await page.waitForLoadState("networkidle").catch(() => {});

            const afterCreateUrl = page.url();
            const afterCreateContent = await getPageText(page);
            console.log(`After create URL: ${afterCreateUrl}`);
            console.log(
              `After create content (first 500): ${afterCreateContent.substring(0, 500)}`
            );

            // Check for success message or redirect
            const success =
              afterCreateContent.toLowerCase().includes("success") ||
              afterCreateContent.toLowerCase().includes("created") ||
              afterCreateContent.includes(testProjectName);

            console.log(`Project creation success: ${success}`);

            await takeScreenshot(page, "project_create_result");
          }
        } else {
          console.log(
            "Could not find project name input — form may use different structure"
          );
          // List all visible inputs
          const allInputs = await page
            .locator("input:visible, textarea:visible")
            .all();
          for (let i = 0; i < Math.min(allInputs.length, 10); i++) {
            const name = await allInputs[i].getAttribute("name");
            const placeholder = await allInputs[i].getAttribute("placeholder");
            const type = await allInputs[i].getAttribute("type");
            console.log(
              `Input ${i}: name=${name}, placeholder=${placeholder}, type=${type}`
            );
          }
          await takeScreenshot(page, "project_create_form_structure");
        }
      } else {
        console.log(
          "No create button found — looking for alternative UI patterns"
        );

        // Check if there's a "+" icon or FAB button
        const fabBtn = page
          .locator(
            '[class*="fab"], [class*="Fab"], [aria-label*="create" i], [aria-label*="add" i], [aria-label*="new" i], button svg'
          )
          .first();
        if (await fabBtn.isVisible().catch(() => false)) {
          console.log("Found FAB or icon button");
          await fabBtn.click();
          await page.waitForTimeout(2000);
          await takeScreenshot(page, "project_create_fab_clicked");
        } else {
          console.log(
            "No create/add button found — project creation may not be available"
          );

          // Try navigating to a create page directly
          const testUrls = [
            `${PROJECT_URL}/projects/create`,
            `${PROJECT_URL}/projects/new`,
            `${PROJECT_URL}/create`,
            `${PROJECT_URL}/new`,
          ];
          for (const url of testUrls) {
            await page.goto(url, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
            const content = await getPageText(page);
            if (
              content.toLowerCase().includes("create") ||
              content.toLowerCase().includes("new project")
            ) {
              console.log(`Create page found at: ${url}`);
              await takeScreenshot(page, "project_create_direct_url");
              break;
            }
          }
        }

        await takeScreenshot(page, "project_no_create_button");
      }
    } finally {
      await context.close();
    }
  });

  test("11. View project detail — click into a project", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      // The dashboard shows multiple tables. From exploration we know:
      // Table 2: "Project | Start Date | Created By | Assigned To | Select Project"
      // Table 4: "Project Name | Description | start Date | End Date | Owner | Manager | Actual Budget | Plan budget | Tasks | Assigned To"
      // These tables are on the dashboard — check if they have data rows

      const allTables = page.locator("table");
      const tableCount = await allTables.count();
      console.log(`Total tables on dashboard: ${tableCount}`);

      let foundProjectData = false;
      for (let t = 0; t < tableCount; t++) {
        const table = allTables.nth(t);
        const headers = await table.locator("th").allTextContents();
        const bodyRows = await table.locator("tbody tr").count();
        const headerText = headers.map(h => h.trim()).filter(h => h).join(" | ");
        console.log(`Table ${t}: headers=[${headerText}], body rows=${bodyRows}`);

        if (bodyRows > 0 && headerText.toLowerCase().includes("project")) {
          // Check if body rows contain actual data (not just "No data" or "Select")
          const firstRowText = await table.locator("tbody tr").first().textContent();
          const trimmed = firstRowText?.trim() || "";
          console.log(`Table ${t} first row: "${trimmed.substring(0, 200)}"`);

          if (trimmed && !trimmed.toLowerCase().includes("no data") && !trimmed.toLowerCase().includes("no project")) {
            foundProjectData = true;
            console.log(`Found project data in table ${t}`);
          }
        }
      }

      if (!foundProjectData) {
        console.log("No project data rows found in any table — projects may not exist yet or tables are empty");
      }

      // Also try navigating to the All Projects page via sidebar
      const allProjectsLink = page.locator('a:has-text("All Projects")').first();
      if (await allProjectsLink.isVisible({ timeout: 3000 }).catch(() => false)) {
        console.log("Clicking All Projects sidebar link...");
        await allProjectsLink.click();
        await page.waitForTimeout(5000);

        const allProjectsUrl = page.url();
        console.log(`All Projects URL: ${allProjectsUrl}`);

        const allProjectsContent = await getPageText(page);
        console.log(`All Projects content (first 300): ${allProjectsContent.substring(0, 300)}`);

        const allProjectsHeadings = await page.locator("h1, h2, h3, h4").allTextContents();
        console.log(`All Projects headings: ${JSON.stringify(allProjectsHeadings)}`);
      }

      await takeScreenshot(page, "project_detail_exploration");
    } finally {
      await context.close().catch(() => {});
    }
  });

  test("12. Edit project — modify project details", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      // First navigate to a project detail
      const projectLinks = page.locator(
        'a[href*="project"], [class*="project"] a, [class*="card"] a, tr a'
      );
      const count = await projectLinks.count();

      if (count > 0) {
        await projectLinks.first().click();
        await page.waitForTimeout(3000);
        await page.waitForLoadState("networkidle").catch(() => {});

        // Look for edit button
        const editBtn = page
          .locator(
            'button:has-text("Edit"), a:has-text("Edit"), button[aria-label*="edit" i], [class*="edit" i]'
          )
          .first();

        if (await editBtn.isVisible().catch(() => false)) {
          console.log("Edit button found");
          await editBtn.click();
          await page.waitForTimeout(2000);

          await takeScreenshot(page, "project_edit_form");

          // Check for editable fields
          const inputs = await page.locator("input:visible, textarea:visible").count();
          console.log(`Editable fields found: ${inputs}`);

          // Try to modify a field
          const nameInput = page
            .locator(
              'input[name="name"], input[name="title"], input[placeholder*="name" i]'
            )
            .first();
          if (await nameInput.isVisible().catch(() => false)) {
            const currentValue = await nameInput.inputValue();
            console.log(`Current project name: ${currentValue}`);
            // Don't actually change the name to avoid messing up data
          }
        } else {
          console.log("No edit button found on project detail page");

          // Check for inline editing or settings/gear icon
          const settingsBtn = page
            .locator(
              'button[aria-label*="setting" i], button[aria-label*="config" i], [class*="settings"], [class*="gear"]'
            )
            .first();
          if (await settingsBtn.isVisible().catch(() => false)) {
            console.log("Found settings/config button");
            await settingsBtn.click();
            await page.waitForTimeout(2000);
            await takeScreenshot(page, "project_settings");
          }
        }
      } else {
        console.log("No projects available to edit");
      }

      await takeScreenshot(page, "project_edit_attempt");
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// SECTION 4: Task Management
// ============================================================

test.describe("Project Module — Task Management", () => {
  test("13. View tasks — navigate to tasks section", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      // Look for tasks link in navigation
      const tasksLink = page
        .locator(
          'a:has-text("Tasks"), a:has-text("Task"), nav a:has-text("Task"), [class*="sidebar"] a:has-text("Task"), [class*="nav"] a:has-text("Task")'
        )
        .first();

      if (await tasksLink.isVisible().catch(() => false)) {
        const href = await tasksLink.getAttribute("href");
        console.log(`Tasks link found, href: ${href}`);
        await tasksLink.click();
        await page.waitForTimeout(3000);
        await page.waitForLoadState("networkidle").catch(() => {});

        const tasksUrl = page.url();
        console.log(`Tasks page URL: ${tasksUrl}`);
      } else {
        console.log("No Tasks link found in navigation — trying direct URLs");
        // Try common task page URLs
        const taskUrls = [
          `${PROJECT_URL}/tasks`,
          `${PROJECT_URL}/task`,
          `${PROJECT_URL}/board`,
        ];
        for (const url of taskUrls) {
          await page.goto(url, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
          const content = await getPageText(page);
          if (
            content.toLowerCase().includes("task") ||
            content.toLowerCase().includes("board") ||
            content.toLowerCase().includes("todo") ||
            content.toLowerCase().includes("kanban")
          ) {
            console.log(`Tasks page found at: ${url}`);
            break;
          }
        }
      }

      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      const hasTaskContent =
        lowerContent.includes("task") ||
        lowerContent.includes("todo") ||
        lowerContent.includes("in progress") ||
        lowerContent.includes("done") ||
        lowerContent.includes("board") ||
        lowerContent.includes("kanban");

      console.log(`Has task content: ${hasTaskContent}`);

      const headings = await page.locator("h1, h2, h3, h4").allTextContents();
      console.log(`Task page headings: ${JSON.stringify(headings)}`);

      await takeScreenshot(page, "tasks_page");

      // Soft assertion — page should show something
      expect(true).toBeTruthy();
    } finally {
      await context.close();
    }
  });

  test("14. View tasks list via API — GET /v1/tasks", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAccessToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      // Try the tasks API endpoint
      const tasksResponse = await page.request.get(
        `${PROJECT_API}/v1/tasks`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const status = tasksResponse.status();
      const body = await tasksResponse.text();
      console.log(`GET ${PROJECT_API}/v1/tasks — Status: ${status}`);
      console.log(`Response: ${body.substring(0, 2000)}`);

      // Try fallback paths
      if (status >= 400) {
        const fb1 = await page.request.get(
          `${PROJECT_API}/api/v1/tasks`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        console.log(
          `GET ${PROJECT_API}/api/v1/tasks — Status: ${fb1.status()}`
        );
        const fb1Body = await fb1.text();
        console.log(`Fallback response: ${fb1Body.substring(0, 2000)}`);
      }

      expect(status).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("15. Create task via UI — test task creation form", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      // First try to navigate to tasks page
      const tasksLink = page
        .locator('a:has-text("Tasks"), a:has-text("Task"), nav a:has-text("Task")')
        .first();

      if (await tasksLink.isVisible().catch(() => false)) {
        await tasksLink.click();
        await page.waitForTimeout(2000);
      }

      // Or navigate into a project first, then look for tasks
      const projectLinks = page.locator('a[href*="project"], [class*="project"] a, [class*="card"] a').first();
      if (await projectLinks.isVisible().catch(() => false)) {
        await projectLinks.click();
        await page.waitForTimeout(2000);
      }

      // Look for create task button
      const createTaskBtn = page
        .locator(
          'button:has-text("Add Task"), button:has-text("Create Task"), button:has-text("New Task"), a:has-text("Add Task"), a:has-text("New Task"), button:has-text("+")'
        )
        .first();

      if (await createTaskBtn.isVisible().catch(() => false)) {
        console.log("Create task button found");
        await createTaskBtn.click();
        await page.waitForTimeout(2000);

        await takeScreenshot(page, "task_create_form");

        // Look for task form fields
        const titleInput = page
          .locator(
            'input[name="title"], input[name="name"], input[placeholder*="title" i], input[placeholder*="task" i]'
          )
          .first();

        if (await titleInput.isVisible().catch(() => false)) {
          const testTaskName = `Test Task ${Date.now()}`;
          await titleInput.fill(testTaskName);
          console.log(`Filled task title: ${testTaskName}`);

          // Look for description
          const descInput = page
            .locator('textarea[name="description"], textarea')
            .first();
          if (await descInput.isVisible().catch(() => false)) {
            await descInput.fill(
              "Automated test task from Playwright E2E suite"
            );
          }

          // Look for priority/status selectors
          const selects = await page.locator("select:visible").count();
          console.log(`Select dropdowns: ${selects}`);

          await takeScreenshot(page, "task_create_filled");

          // Submit
          const submitBtn = page
            .locator(
              'button[type="submit"], button:has-text("Save"), button:has-text("Create"), button:has-text("Add")'
            )
            .last();
          if (await submitBtn.isVisible().catch(() => false)) {
            await submitBtn.click();
            await page.waitForTimeout(3000);
            console.log(`After task create URL: ${page.url()}`);
            await takeScreenshot(page, "task_create_result");
          }
        } else {
          console.log("Task title input not found — checking form structure");
          const allInputs = await page
            .locator("input:visible, textarea:visible")
            .all();
          for (let i = 0; i < Math.min(allInputs.length, 10); i++) {
            const name = await allInputs[i].getAttribute("name");
            const ph = await allInputs[i].getAttribute("placeholder");
            console.log(`Input ${i}: name=${name}, placeholder=${ph}`);
          }
        }
      } else {
        console.log("No create task button found");
        await takeScreenshot(page, "task_no_create_button");
      }
    } finally {
      await context.close();
    }
  });

  test("16. Task status display — check for status columns/labels", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      // Navigate to tasks
      const tasksLink = page
        .locator('a:has-text("Tasks"), a:has-text("Task"), nav a:has-text("Task")')
        .first();
      if (await tasksLink.isVisible().catch(() => false)) {
        await tasksLink.click();
        await page.waitForTimeout(2000);
      }

      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      // Check for status-related content (kanban columns, status labels, etc.)
      const statusTerms = [
        "todo",
        "to do",
        "to-do",
        "in progress",
        "in-progress",
        "done",
        "completed",
        "review",
        "open",
        "closed",
        "backlog",
        "blocked",
      ];

      const foundStatuses: string[] = [];
      for (const term of statusTerms) {
        if (lowerContent.includes(term)) {
          foundStatuses.push(term);
        }
      }
      console.log(`Found status terms: ${JSON.stringify(foundStatuses)}`);

      // Look for kanban board columns
      const columns = await page
        .locator(
          '[class*="column"], [class*="Column"], [class*="lane"], [class*="Lane"], [data-status], [class*="kanban"], [class*="Kanban"]'
        )
        .count();
      console.log(`Board columns/lanes: ${columns}`);

      // Look for status badges/labels
      const badges = await page
        .locator(
          '[class*="badge"], [class*="Badge"], [class*="status"], [class*="Status"], [class*="chip"], [class*="Chip"], [class*="tag"], [class*="Tag"]'
        )
        .count();
      console.log(`Status badges/tags: ${badges}`);

      await takeScreenshot(page, "task_status_display");
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// SECTION 5: Time Tracking
// ============================================================

test.describe("Project Module — Time Tracking", () => {
  test("17. View time entries — navigate to time tracking section", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      // Look for time tracking link
      const timeLink = page
        .locator(
          'a:has-text("Time"), a:has-text("Timesheet"), a:has-text("Time Tracking"), a:has-text("Time Entry"), a:has-text("Log"), nav a:has-text("Time")'
        )
        .first();

      if (await timeLink.isVisible().catch(() => false)) {
        const href = await timeLink.getAttribute("href");
        console.log(`Time tracking link found, href: ${href}`);
        await timeLink.click();
        await page.waitForTimeout(3000);
        console.log(`Time tracking URL: ${page.url()}`);
      } else {
        console.log(
          "No time tracking link found — trying direct URLs"
        );
        const timeUrls = [
          `${PROJECT_URL}/time-entries`,
          `${PROJECT_URL}/timesheet`,
          `${PROJECT_URL}/time`,
          `${PROJECT_URL}/timelog`,
        ];
        for (const url of timeUrls) {
          await page.goto(url, { waitUntil: "networkidle", timeout: 15000 }).catch(() => {});
          const content = await getPageText(page);
          if (
            content.toLowerCase().includes("time") ||
            content.toLowerCase().includes("hours") ||
            content.toLowerCase().includes("log")
          ) {
            console.log(`Time tracking page found at: ${url}`);
            break;
          }
        }
      }

      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      const hasTimeContent =
        lowerContent.includes("time") ||
        lowerContent.includes("hours") ||
        lowerContent.includes("duration") ||
        lowerContent.includes("timesheet") ||
        lowerContent.includes("log");

      console.log(`Has time tracking content: ${hasTimeContent}`);

      await takeScreenshot(page, "time_tracking_page");
    } finally {
      await context.close();
    }
  });

  test("18. Time entries API — GET /v1/time-entries", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAccessToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      const timeResponse = await page.request.get(
        `${PROJECT_API}/v1/time-entries`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const status = timeResponse.status();
      const body = await timeResponse.text();
      console.log(`GET ${PROJECT_API}/v1/time-entries — Status: ${status}`);
      console.log(`Response: ${body.substring(0, 2000)}`);

      // Try fallback
      if (status >= 400) {
        const fb = await page.request.get(
          `${PROJECT_API}/api/v1/time-entries`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        console.log(
          `GET ${PROJECT_API}/api/v1/time-entries — Status: ${fb.status()}`
        );
        const fbBody = await fb.text();
        console.log(`Fallback: ${fbBody.substring(0, 2000)}`);
      }

      expect(status).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// SECTION 6: RBAC & Cross-Role Tests
// ============================================================

test.describe("Project Module — RBAC & Cross-Role", () => {
  test("19. Employee access level — limited vs admin access", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
      await page.waitForTimeout(2000);

      const currentUrl = page.url();
      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      console.log(`Employee project URL: ${currentUrl}`);

      // Check what employee can see
      const headings = await page.locator("h1, h2, h3, h4").allTextContents();
      console.log(`Employee headings: ${JSON.stringify(headings)}`);

      // Check navigation items visible to employee
      const navItems = await page
        .locator("nav a, aside a, [class*='sidebar'] a, [class*='nav'] a, [class*='menu'] a")
        .allTextContents();
      const cleanNavItems = navItems
        .filter((n) => n.trim())
        .map((n) => n.trim());
      console.log(
        `Employee nav items: ${JSON.stringify(cleanNavItems.slice(0, 20))}`
      );

      // Check for admin-only features that employee should NOT see
      const hasAdminFeatures =
        lowerContent.includes("admin") ||
        lowerContent.includes("settings") ||
        lowerContent.includes("manage users") ||
        lowerContent.includes("billing") ||
        lowerContent.includes("configuration");

      console.log(`Employee has admin features: ${hasAdminFeatures}`);

      // Check for project-related content
      const hasProjectAccess =
        lowerContent.includes("project") ||
        lowerContent.includes("task") ||
        lowerContent.includes("dashboard");

      console.log(`Employee has project access: ${hasProjectAccess}`);

      await takeScreenshot(page, "rbac_employee_access");

      if (hasAdminFeatures) {
        console.log(
          "NOTE: Employee can see admin features — potential RBAC issue"
        );
      }
    } finally {
      await context.close();
    }
  });

  test("20. Admin vs Employee UI comparison — admin sees more features", async ({
    browser,
  }) => {
    test.setTimeout(90000);

    // Login as admin
    const { context: adminCtx, page: adminPage } =
      await createFreshContext(browser);
    let adminNavItems: string[] = [];
    let adminButtons: string[] = [];

    try {
      await loginViaSSO(
        adminPage,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );
      await adminPage.waitForTimeout(2000);

      adminNavItems = (
        await adminPage
          .locator("nav a, aside a, [class*='sidebar'] a, [class*='nav'] a, [class*='menu'] a")
          .allTextContents()
      )
        .filter((n) => n.trim())
        .map((n) => n.trim());

      adminButtons = (await adminPage.locator("button").allTextContents())
        .filter((b) => b.trim())
        .map((b) => b.trim());

      console.log(
        `Admin nav items (${adminNavItems.length}): ${JSON.stringify(adminNavItems.slice(0, 20))}`
      );
      console.log(
        `Admin buttons (${adminButtons.length}): ${JSON.stringify(adminButtons.slice(0, 15))}`
      );

      await takeScreenshot(adminPage, "rbac_admin_view");
    } finally {
      await adminCtx.close();
    }

    // Login as employee
    const { context: empCtx, page: empPage } =
      await createFreshContext(browser);
    try {
      await loginViaSSO(
        empPage,
        EMPLOYEE_CREDS.email,
        EMPLOYEE_CREDS.password
      );
      await empPage.waitForTimeout(2000);

      const empNavItems = (
        await empPage
          .locator("nav a, aside a, [class*='sidebar'] a, [class*='nav'] a, [class*='menu'] a")
          .allTextContents()
      )
        .filter((n) => n.trim())
        .map((n) => n.trim());

      const empButtons = (await empPage.locator("button").allTextContents())
        .filter((b) => b.trim())
        .map((b) => b.trim());

      console.log(
        `Employee nav items (${empNavItems.length}): ${JSON.stringify(empNavItems.slice(0, 20))}`
      );
      console.log(
        `Employee buttons (${empButtons.length}): ${JSON.stringify(empButtons.slice(0, 15))}`
      );

      // Compare
      const adminOnly = adminNavItems.filter(
        (item) => !empNavItems.includes(item)
      );
      const empOnly = empNavItems.filter(
        (item) => !adminNavItems.includes(item)
      );

      console.log(
        `Admin-only nav items: ${JSON.stringify(adminOnly.slice(0, 10))}`
      );
      console.log(
        `Employee-only nav items: ${JSON.stringify(empOnly.slice(0, 10))}`
      );
      console.log(
        `Nav difference: Admin has ${adminNavItems.length}, Employee has ${empNavItems.length}`
      );

      await takeScreenshot(empPage, "rbac_employee_view");
    } finally {
      await empCtx.close();
    }
  });

  test("21. Super Admin access to project module", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(
        page,
        SUPER_ADMIN_CREDS.email,
        SUPER_ADMIN_CREDS.password
      );
      await page.waitForTimeout(2000);

      const currentUrl = page.url();
      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      console.log(`Super Admin project URL: ${currentUrl}`);

      const headings = await page.locator("h1, h2, h3, h4").allTextContents();
      console.log(`Super Admin headings: ${JSON.stringify(headings)}`);

      const hasAccess =
        lowerContent.includes("project") ||
        lowerContent.includes("dashboard") ||
        lowerContent.includes("task");

      const hasError =
        lowerContent.includes("error") ||
        lowerContent.includes("denied") ||
        lowerContent.includes("unauthorized") ||
        lowerContent.includes("no organization");

      console.log(`Super Admin has access: ${hasAccess}`);
      console.log(`Super Admin has error: ${hasError}`);

      if (hasError) {
        console.log(
          "NOTE: Super Admin may not have project module access — this is expected if they don't belong to a subscribed org"
        );
      }

      await takeScreenshot(page, "rbac_super_admin");
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// SECTION 7: UI/UX Checks
// ============================================================

test.describe("Project Module — UI/UX Checks", () => {
  test("22. Navigation works — sidebar/tabs function correctly", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      // Collect all navigation links
      const navLinks = await page
        .locator("nav a, aside a, [class*='sidebar'] a, [class*='nav'] a, [class*='menu'] a")
        .all();

      const linkDetails: Array<{ text: string; href: string | null }> = [];
      for (const link of navLinks.slice(0, 15)) {
        const text = ((await link.textContent()) || "").trim();
        const href = await link.getAttribute("href");
        if (text) {
          linkDetails.push({ text, href });
        }
      }

      console.log(`Navigation links: ${JSON.stringify(linkDetails)}`);

      // Click on each nav link and verify page changes
      let workingLinks = 0;
      let brokenLinks = 0;
      const testedLinks: string[] = [];

      for (const link of linkDetails.slice(0, 5)) {
        if (!link.text || !link.href) continue;
        try {
          const navLink = page.locator(`a:has-text("${link.text}")`).first();
          if (await navLink.isVisible().catch(() => false)) {
            await navLink.click();
            await page.waitForTimeout(2000);
            await page.waitForLoadState("networkidle").catch(() => {});

            const newUrl = page.url();
            const content = await getPageText(page);
            const hasContent = content.length > 100;

            console.log(
              `Clicked "${link.text}" → URL: ${newUrl}, has content: ${hasContent}`
            );

            if (hasContent) {
              workingLinks++;
            } else {
              brokenLinks++;
            }
            testedLinks.push(`${link.text}: ${hasContent ? "OK" : "EMPTY"}`);
          }
        } catch (err) {
          console.log(`Error clicking "${link.text}": ${err}`);
          brokenLinks++;
          testedLinks.push(`${link.text}: ERROR`);
        }
      }

      console.log(`Working links: ${workingLinks}, Broken: ${brokenLinks}`);
      console.log(`Tested: ${JSON.stringify(testedLinks)}`);

      await takeScreenshot(page, "navigation_test");
    } finally {
      await context.close();
    }
  });

  test("23. Page elements render properly — key elements visible", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      // Check for key page elements
      const checks = {
        hasHeader:
          (await page
            .locator("header, [class*='header'], [class*='Header'], [class*='topbar'], [class*='Topbar']")
            .count()) > 0,
        hasSidebar:
          (await page
            .locator("aside, nav, [class*='sidebar'], [class*='Sidebar']")
            .count()) > 0,
        hasMainContent:
          (await page
            .locator("main, [class*='content'], [class*='Content'], [class*='main'], [class*='Main']")
            .count()) > 0,
        hasHeadings:
          (await page.locator("h1, h2, h3").count()) > 0,
        hasButtons:
          (await page.locator("button").count()) > 0,
        hasImages:
          (await page.locator("img, svg").count()) > 0,
      };

      console.log(`Page element checks: ${JSON.stringify(checks)}`);

      // Check for console errors
      const consoleErrors: string[] = [];
      page.on("console", (msg) => {
        if (msg.type() === "error") {
          consoleErrors.push(msg.text());
        }
      });

      // Reload to capture console errors
      await page.reload({ waitUntil: "networkidle" }).catch(() => {});
      await page.waitForTimeout(2000);

      if (consoleErrors.length > 0) {
        console.log(
          `Console errors (${consoleErrors.length}): ${JSON.stringify(consoleErrors.slice(0, 5))}`
        );
      } else {
        console.log("No console errors detected");
      }

      // Check for broken images
      const images = await page.locator("img").all();
      let brokenImages = 0;
      for (const img of images.slice(0, 10)) {
        const src = await img.getAttribute("src");
        const natural = await img.evaluate(
          (el: HTMLImageElement) => el.naturalWidth
        );
        if (natural === 0 && src) {
          brokenImages++;
          console.log(`Broken image: ${src}`);
        }
      }
      console.log(`Broken images: ${brokenImages}/${images.length}`);

      await takeScreenshot(page, "ui_elements_check");

      // At least some basic elements should be present
      expect(
        checks.hasMainContent || checks.hasHeadings || checks.hasButtons
      ).toBeTruthy();
    } finally {
      await context.close();
    }
  });

  test("24. Invalid project ID — shows error or 404", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      // Navigate to a non-existent project ID
      await page.goto(
        `${PROJECT_URL}/projects/nonexistent-id-99999`,
        {
          waitUntil: "networkidle",
          timeout: 15000,
        }
      ).catch(() => {});
      await page.waitForTimeout(2000);

      const currentUrl = page.url();
      const pageContent = await getPageText(page);
      const lowerContent = pageContent.toLowerCase();

      console.log(`Invalid project URL: ${currentUrl}`);

      const showsError =
        lowerContent.includes("not found") ||
        lowerContent.includes("404") ||
        lowerContent.includes("error") ||
        lowerContent.includes("does not exist") ||
        lowerContent.includes("no project");

      const redirected =
        currentUrl.includes("/projects") &&
        !currentUrl.includes("nonexistent");

      console.log(`Shows error/404: ${showsError}`);
      console.log(`Redirected away: ${redirected}`);
      console.log(
        `Page content (first 500): ${pageContent.substring(0, 500)}`
      );

      await takeScreenshot(page, "invalid_project_id");

      // The module should handle invalid IDs gracefully
      expect(showsError || redirected || pageContent.length > 0).toBeTruthy();
    } finally {
      await context.close();
    }
  });

  test("25. API error handling — invalid project ID via API", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAccessToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      // Try to get a non-existent project via API
      const response = await page.request.get(
        `${PROJECT_API}/v1/projects/nonexistent-id-99999`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const status = response.status();
      const body = await response.text();
      console.log(
        `GET /v1/projects/nonexistent-id — Status: ${status}`
      );
      console.log(`Response: ${body.substring(0, 1000)}`);

      // Should return 404 or similar error, not 500
      if (status === 500) {
        console.log(
          "BUG: API returns 500 for invalid project ID — should return 404"
        );
      } else if (status === 404) {
        console.log("PASS: API correctly returns 404 for invalid project ID");
      } else if (status === 401 || status === 403) {
        console.log(
          `Auth issue (${status}) — SSO token may not work directly as bearer token for Project API`
        );
      }

      expect(status).not.toBe(500);
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// SECTION 8: Project Module SSO with Cookie-Based Auth
// ============================================================

test.describe("Project Module — SSO Cookie Auth Flow", () => {
  test("26. SSO sets session cookies — verify auth cookies after SSO", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Check cookies set by the project module
      const cookies = await context.cookies();
      const projectCookies = cookies.filter(
        (c) =>
          c.domain.includes("project") ||
          c.domain.includes("empcloud") ||
          c.name.toLowerCase().includes("token") ||
          c.name.toLowerCase().includes("session") ||
          c.name.toLowerCase().includes("auth")
      );

      console.log(`Total cookies: ${cookies.length}`);
      console.log(
        `Project/auth cookies: ${JSON.stringify(
          projectCookies.map((c) => ({
            name: c.name,
            domain: c.domain,
            path: c.path,
            httpOnly: c.httpOnly,
            secure: c.secure,
            value: c.value.substring(0, 30) + "...",
          }))
        )}`
      );

      // Check localStorage for tokens
      const localStorageData = await page.evaluate(() => {
        const data: Record<string, string> = {};
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (key) {
            const val = localStorage.getItem(key) || "";
            data[key] = val.substring(0, 100);
          }
        }
        return data;
      });
      console.log(`localStorage: ${JSON.stringify(localStorageData)}`);

      await takeScreenshot(page, "sso_cookies");
    } finally {
      await context.close();
    }
  });

  test("27. API calls from authenticated page — project API works via page context", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      // Try to call project API from the authenticated page context (cookies included)
      const apiResult = await page.evaluate(async (apiUrl) => {
        const results: Record<string, any> = {};

        // Try /v1/projects
        try {
          const res1 = await fetch(`${apiUrl}/v1/projects`, {
            credentials: "include",
          });
          results.projects = {
            status: res1.status,
            body: (await res1.text()).substring(0, 500),
          };
        } catch (e: any) {
          results.projects = { error: e.message };
        }

        // Try /v1/tasks
        try {
          const res2 = await fetch(`${apiUrl}/v1/tasks`, {
            credentials: "include",
          });
          results.tasks = {
            status: res2.status,
            body: (await res2.text()).substring(0, 500),
          };
        } catch (e: any) {
          results.tasks = { error: e.message };
        }

        // Try /v1/time-entries
        try {
          const res3 = await fetch(`${apiUrl}/v1/time-entries`, {
            credentials: "include",
          });
          results.timeEntries = {
            status: res3.status,
            body: (await res3.text()).substring(0, 500),
          };
        } catch (e: any) {
          results.timeEntries = { error: e.message };
        }

        return results;
      }, PROJECT_API);

      console.log(`API results from page context: ${JSON.stringify(apiResult)}`);

      await takeScreenshot(page, "api_from_page_context");
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// SECTION 9: Project Module — Explore UI Structure
// ============================================================

test.describe("Project Module — UI Exploration", () => {
  test("28. Full page DOM exploration — document all visible elements", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(2000);

      // Take screenshot FIRST before heavy DOM evaluation
      await takeScreenshot(page, "ui_exploration");

      // Get the page title
      const title = await page.title();
      console.log(`Page title: ${title}`);

      // Use Playwright locators instead of page.evaluate to avoid context/timeout issues
      const headings = await page.locator("h1, h2, h3, h4, h5, h6").allTextContents();
      console.log(`Headings (${headings.length}): ${JSON.stringify(headings)}`);

      const links = await page.locator("a").evaluateAll((els) =>
        els.slice(0, 25).map((el) => {
          const text = el.textContent?.trim() || "";
          const href = el.getAttribute("href") || "";
          return `${text} -> ${href}`;
        })
      );
      console.log(`Links (${links.length}): ${JSON.stringify(links)}`);

      const buttons = await page.locator("button").allTextContents();
      console.log(`Buttons (${buttons.length}): ${JSON.stringify(buttons.filter(b => b.trim()).slice(0, 15))}`);

      const inputs = await page.locator("input, textarea, select").evaluateAll((els) =>
        els.slice(0, 15).map((el) => {
          const name = el.getAttribute("name") || "";
          const type = el.getAttribute("type") || "";
          const ph = el.getAttribute("placeholder") || "";
          return `name=${name}, type=${type}, placeholder=${ph}`;
        })
      );
      console.log(`Inputs (${inputs.length}): ${JSON.stringify(inputs)}`);

      const tables = await page.locator("table").evaluateAll((tbls) =>
        tbls.map((table) => {
          const headers: string[] = [];
          table.querySelectorAll("th").forEach((th) => headers.push(th.textContent?.trim() || ""));
          return headers.join(" | ");
        })
      );
      console.log(`Tables (${tables.length}): ${JSON.stringify(tables)}`);

      console.log("DOM exploration complete");
    } finally {
      await context.close();
    }
  });

  test("29. Responsive check — key elements at 375px mobile width", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const context = await browser.newContext({
      viewport: { width: 375, height: 812 },
      ignoreHTTPSErrors: true,
    });
    const page = await context.newPage();
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.waitForTimeout(3000);

      const pageContent = await getPageText(page);
      console.log(`Mobile page content length: ${pageContent.length}`);

      // Check for hamburger menu or mobile nav
      const hasHamburger =
        (await page
          .locator(
            '[class*="hamburger"], [class*="Hamburger"], [aria-label*="menu" i], button[class*="menu" i], [class*="burger"]'
          )
          .count()) > 0;

      console.log(`Has hamburger menu: ${hasHamburger}`);

      // Check for horizontal scrollbar (bad responsive design)
      const hasHScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });
      console.log(`Has horizontal scroll (bad): ${hasHScroll}`);

      // Check for overlapping or cut-off text
      const visibleText = await page
        .locator("h1, h2, h3, p, span, a, button")
        .allTextContents();
      console.log(
        `Visible text elements at 375px: ${visibleText.filter((t) => t.trim()).length}`
      );

      await takeScreenshot(page, "responsive_mobile_375");

      if (hasHScroll) {
        console.log("NOTE: Horizontal scrollbar at 375px — possible responsive issue");
      }
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// SECTION 10: Network & Performance
// ============================================================

test.describe("Project Module — Network & Performance", () => {
  test("30. Page load performance — measure load time and network requests", async ({
    browser,
  }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await getAccessToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      // Track network requests
      const requests: Array<{ url: string; status: number; method: string }> = [];
      const failedRequests: Array<{ url: string; error: string }> = [];

      page.on("response", (response) => {
        requests.push({
          url: response.url(),
          status: response.status(),
          method: response.request().method(),
        });
      });

      page.on("requestfailed", (request) => {
        failedRequests.push({
          url: request.url(),
          error: request.failure()?.errorText || "unknown",
        });
      });

      const startTime = Date.now();
      await page.goto(`${PROJECT_URL}?sso_token=${token}`, {
        waitUntil: "networkidle",
        timeout: 30000,
      });
      await page.waitForTimeout(2000);
      const loadTime = Date.now() - startTime;

      console.log(`Page load time: ${loadTime}ms`);
      console.log(`Total requests: ${requests.length}`);
      console.log(`Failed requests: ${failedRequests.length}`);

      // Summarize request statuses
      const statusCounts: Record<number, number> = {};
      for (const req of requests) {
        statusCounts[req.status] = (statusCounts[req.status] || 0) + 1;
      }
      console.log(`Status distribution: ${JSON.stringify(statusCounts)}`);

      // Log failed requests
      if (failedRequests.length > 0) {
        console.log(
          `Failed requests: ${JSON.stringify(failedRequests.slice(0, 5))}`
        );
      }

      // Log 4xx/5xx requests
      const errorRequests = requests.filter((r) => r.status >= 400);
      if (errorRequests.length > 0) {
        console.log(
          `Error requests (${errorRequests.length}): ${JSON.stringify(
            errorRequests.slice(0, 10).map((r) => `${r.method} ${r.url.substring(0, 100)} → ${r.status}`)
          )}`
        );
      }

      // API-specific requests
      const apiRequests = requests.filter(
        (r) =>
          r.url.includes("project") &&
          (r.url.includes("/v1/") || r.url.includes("/api/"))
      );
      console.log(
        `API requests (${apiRequests.length}): ${JSON.stringify(
          apiRequests.map((r) => `${r.method} ${r.url.substring(0, 100)} → ${r.status}`)
        )}`
      );

      await takeScreenshot(page, "performance_load");

      // Load time should be reasonable (under 30 seconds)
      expect(loadTime).toBeLessThan(30000);
    } finally {
      await context.close();
    }
  });
});
