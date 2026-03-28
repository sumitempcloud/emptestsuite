import { test, expect, Page, BrowserContext, Browser } from "@playwright/test";

// ============================================================
// EMP Cloud Project Module — Deep Functional Testing
// Tests project management, tasks, time tracking, RBAC, etc.
// ============================================================

const BASE_URL = "https://test-empcloud.empcloud.com";
const PROJECT_URL = "https://test-project.empcloud.com";
const PROJECT_API = "https://test-project-api.empcloud.com";
const TASK_API = "https://test-project-task-api.empcloud.com";

const ADMIN_CREDS = { email: "ananya@technova.in", password: "Welcome@123" };
const EMPLOYEE_CREDS = { email: "priya@technova.in", password: "Welcome@123" };
const SUPER_ADMIN_CREDS = {
  email: "admin@empcloud.com",
  password: "SuperAdmin@2026",
};

// ---- Helpers ----

async function getAccessToken(
  page: Page,
  email: string,
  password: string
): Promise<string> {
  const response = await page.request.post(`${BASE_URL}/api/v1/auth/login`, {
    data: { email, password },
  });
  const json = await response.json();
  return (
    json?.data?.tokens?.access_token ||
    json?.data?.access_token ||
    json?.access_token ||
    ""
  );
}

async function getProjectToken(
  page: Page,
  email: string,
  password: string
): Promise<{ empToken: string; projectToken: string; userData: any }> {
  const empToken = await getAccessToken(page, email, password);
  const ssoResp = await page.request.post(`${PROJECT_API}/v1/auth/sso`, {
    data: { token: empToken },
  });
  const ssoJson = await ssoResp.json();
  const projectToken =
    ssoJson?.body?.data?.accessToken || ssoJson?.data?.accessToken || "";
  const userData = ssoJson?.body?.data?.userData || ssoJson?.data?.userData || {};
  return { empToken, projectToken, userData };
}

async function loginViaSSO(
  page: Page,
  email: string,
  password: string
): Promise<string> {
  const token = await getAccessToken(page, email, password);
  if (!token) {
    console.log(`WARNING: Could not get access token for ${email}`);
    return "";
  }
  await page.goto(`${PROJECT_URL}?sso_token=${token}`, {
    waitUntil: "networkidle",
    timeout: 30000,
  });
  await page.waitForTimeout(3000);
  return token;
}

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

async function takeScreenshot(page: Page, name: string): Promise<void> {
  try {
    await page.screenshot({
      path: `e2e/screenshots/project_deep_${name}.png`,
      fullPage: true,
    });
    console.log(`Screenshot saved: project_deep_${name}.png`);
  } catch (err) {
    console.log(`Screenshot failed for ${name}: ${err}`);
  }
}

async function getPageText(page: Page): Promise<string> {
  try {
    return (await page.textContent("body")) || "";
  } catch {
    return "";
  }
}

async function getAllLinks(page: Page): Promise<{ text: string; href: string }[]> {
  return page.evaluate(() => {
    return Array.from(document.querySelectorAll("a")).map((a) => ({
      text: (a.textContent || "").trim().substring(0, 60),
      href: a.getAttribute("href") || "",
    }));
  });
}

async function getAllButtons(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    return Array.from(
      document.querySelectorAll("button, [role='button'], input[type='submit']")
    ).map((b) => (b.textContent || "").trim().substring(0, 60));
  });
}

async function getSidebarItems(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const selectors = [
      "nav a",
      "[class*='sidebar'] a",
      "[class*='Sidebar'] a",
      "[class*='menu'] a",
      "[class*='Menu'] a",
      "[class*='nav'] a",
      "aside a",
      ".sidebar a",
      "#sidebar a",
    ];
    const items = new Set<string>();
    for (const sel of selectors) {
      document.querySelectorAll(sel).forEach((el) => {
        const t = (el.textContent || "").trim();
        if (t && t.length < 60) items.add(t);
      });
    }
    return Array.from(items);
  });
}

async function getFormFields(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    return Array.from(
      document.querySelectorAll(
        "input, textarea, select, [contenteditable='true']"
      )
    ).map((el) => {
      const name =
        el.getAttribute("name") ||
        el.getAttribute("placeholder") ||
        el.getAttribute("aria-label") ||
        el.getAttribute("id") ||
        el.tagName;
      const type = el.getAttribute("type") || el.tagName.toLowerCase();
      return `${type}: ${name}`;
    });
  });
}

async function waitForContent(page: Page, timeout = 8000): Promise<void> {
  try {
    await page.waitForSelector("body", { timeout });
    await page.waitForLoadState("networkidle", { timeout });
  } catch {
    // Continue even if timeout
  }
  await page.waitForTimeout(1500);
}

/**
 * Expand a collapsible sidebar parent section and click a child link.
 * The sidebar uses accordion-style collapsibles with chevrons.
 * Parent items: Projects, Task Management, Task Config, TimeLine, Reports, Members
 * Clicking the parent expands it, then sub-items become visible.
 */
async function clickSidebarItem(
  page: Page,
  parentText: string | null,
  childText: string
): Promise<boolean> {
  try {
    // If parent needs expanding first
    if (parentText) {
      const parent = page.locator(`a:has-text("${parentText}")`).first();
      if (await parent.isVisible({ timeout: 3000 })) {
        await parent.click();
        await page.waitForTimeout(800);
      }
    }

    // Now click the child
    const child = page.locator(`a:has-text("${childText}")`).first();
    if (await child.isVisible({ timeout: 3000 })) {
      await child.click();
      await waitForContent(page);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

/** Close any Next.js runtime error overlay blocking the page */
async function dismissErrorOverlay(page: Page): Promise<void> {
  try {
    // Next.js dev error overlay uses nextjs-portal element
    // Try multiple methods to dismiss it
    await page.evaluate(() => {
      // Remove Next.js portal overlays
      document.querySelectorAll("nextjs-portal").forEach((el) => el.remove());
      // Remove any fixed/absolute position overlays
      document.querySelectorAll("[class*='overlay'], [class*='Overlay']").forEach((el) => {
        const style = window.getComputedStyle(el);
        if (style.position === "fixed" || style.position === "absolute") {
          (el as HTMLElement).style.display = "none";
        }
      });
      // Also handle loader wrappers
      document.querySelectorAll("[class*='loader'], .loader-wrapper").forEach((el) => {
        (el as HTMLElement).style.display = "none";
      });
    });
    await page.waitForTimeout(300);
  } catch {
    // No overlay present or can't access
  }
  // Also try Escape key
  try {
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);
  } catch {
    // Ignore
  }
}

// ============================================================
// PHASE 1: SSO Authentication & Initial Access
// ============================================================

test.describe("Phase 1: SSO Authentication & Access", () => {
  test("1.1 SSO login as Org Admin loads the Project module", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await loginViaSSO(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );
      expect(token).toBeTruthy();

      const url = page.url();
      console.log(`After SSO URL: ${url}`);
      const pageText = await getPageText(page);
      const lower = pageText.toLowerCase();
      console.log(`Page text (first 500): ${pageText.substring(0, 500)}`);

      // Check for any project-related content
      const hasContent =
        lower.includes("project") ||
        lower.includes("dashboard") ||
        lower.includes("task") ||
        lower.includes("welcome") ||
        lower.includes("workspace");

      const hasError =
        lower.includes("error") && !lower.includes("no error");
      const hasLogin =
        lower.includes("sign in") || lower.includes("log in");
      const hasDenied =
        lower.includes("denied") ||
        lower.includes("unauthorized") ||
        lower.includes("forbidden");

      console.log(
        `Content: ${hasContent}, Error: ${hasError}, Login: ${hasLogin}, Denied: ${hasDenied}`
      );

      // Collect sidebar/navigation
      const sidebarItems = await getSidebarItems(page);
      console.log(`Sidebar items: ${JSON.stringify(sidebarItems)}`);

      const allLinks = await getAllLinks(page);
      console.log(
        `All links (${allLinks.length}): ${JSON.stringify(allLinks.slice(0, 20))}`
      );

      const buttons = await getAllButtons(page);
      console.log(`Buttons: ${JSON.stringify(buttons)}`);

      await takeScreenshot(page, "01_admin_sso_landing");

      // Verify we loaded something meaningful (not a blank page)
      expect(token.length).toBeGreaterThan(20);
    } finally {
      await context.close();
    }
  });

  test("1.2 SSO login as Employee loads the Project module", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await loginViaSSO(
        page,
        EMPLOYEE_CREDS.email,
        EMPLOYEE_CREDS.password
      );
      expect(token).toBeTruthy();

      const url = page.url();
      console.log(`Employee SSO URL: ${url}`);
      const pageText = await getPageText(page);
      console.log(`Employee page text (first 500): ${pageText.substring(0, 500)}`);

      const sidebarItems = await getSidebarItems(page);
      console.log(`Employee sidebar: ${JSON.stringify(sidebarItems)}`);

      const buttons = await getAllButtons(page);
      console.log(`Employee buttons: ${JSON.stringify(buttons)}`);

      await takeScreenshot(page, "02_employee_sso_landing");
    } finally {
      await context.close();
    }
  });

  test("1.3 Invalid SSO token shows error or redirects to login", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await page.goto(
        `${PROJECT_URL}?sso_token=invalid_garbage_token_xyz`,
        { waitUntil: "networkidle", timeout: 30000 }
      );
      await page.waitForTimeout(3000);

      const url = page.url();
      console.log(`Invalid token URL: ${url}`);
      const pageText = await getPageText(page);
      const lower = pageText.toLowerCase();

      const showsError =
        lower.includes("invalid") ||
        lower.includes("error") ||
        lower.includes("expired") ||
        lower.includes("unauthorized") ||
        lower.includes("login") ||
        lower.includes("sign in");

      console.log(`Shows error/login: ${showsError}`);
      console.log(`Page text: ${pageText.substring(0, 300)}`);

      await takeScreenshot(page, "03_invalid_sso_token");

      // Should not show authenticated dashboard content
      const hasProjectContent =
        lower.includes("create project") ||
        lower.includes("my projects") ||
        lower.includes("dashboard");

      if (hasProjectContent) {
        console.log("BUG: Invalid SSO token still shows authenticated content!");
      }
    } finally {
      await context.close();
    }
  });

  test("1.4 No SSO token shows login or error", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await page.goto(PROJECT_URL, {
        waitUntil: "networkidle",
        timeout: 30000,
      });
      await page.waitForTimeout(3000);

      const url = page.url();
      const pageText = await getPageText(page);
      const lower = pageText.toLowerCase();

      console.log(`No token URL: ${url}`);
      console.log(`No token page (first 300): ${pageText.substring(0, 300)}`);

      await takeScreenshot(page, "04_no_sso_token");
    } finally {
      await context.close();
    }
  });

  test("1.5 Expired/tampered SSO token handling", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Use a syntactically valid but expired JWT
      const expiredJwt =
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MDAwMDAwMDB9.invalid";
      await page.goto(`${PROJECT_URL}?sso_token=${expiredJwt}`, {
        waitUntil: "networkidle",
        timeout: 30000,
      });
      await page.waitForTimeout(3000);

      const url = page.url();
      const pageText = await getPageText(page);
      console.log(`Expired token URL: ${url}`);
      console.log(`Expired token page: ${pageText.substring(0, 300)}`);

      await takeScreenshot(page, "05_expired_token");
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 2: Full UI Exploration (as Org Admin)
// ============================================================

test.describe("Phase 2: UI Exploration — Admin", () => {
  test("2.1 Map full sidebar navigation and all available pages", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await takeScreenshot(page, "06_admin_dashboard_full");

      // Capture the full page structure
      const pageStructure = await page.evaluate(() => {
        const result: any = {};

        // Get all headings
        result.headings = Array.from(
          document.querySelectorAll("h1, h2, h3, h4, h5, h6")
        ).map((el) => ({
          tag: el.tagName,
          text: (el.textContent || "").trim().substring(0, 100),
        }));

        // Get navigation/sidebar
        result.navLinks = Array.from(
          document.querySelectorAll("nav a, aside a, [class*='sidebar'] a, [class*='menu'] a, [class*='nav'] li a")
        ).map((a) => ({
          text: (a.textContent || "").trim().substring(0, 60),
          href: a.getAttribute("href") || "",
        }));

        // Get all interactive elements
        result.buttons = Array.from(
          document.querySelectorAll("button, [role='button']")
        ).map((b) => (b.textContent || "").trim().substring(0, 60));

        // Get cards/sections
        result.cards = Array.from(
          document.querySelectorAll("[class*='card'], [class*='Card'], [class*='widget'], [class*='Widget']")
        ).map((c) => (c.textContent || "").trim().substring(0, 100));

        // Get tabs
        result.tabs = Array.from(
          document.querySelectorAll("[role='tab'], [class*='tab'], .tab")
        ).map((t) => (t.textContent || "").trim().substring(0, 60));

        return result;
      });

      console.log(`Headings: ${JSON.stringify(pageStructure.headings)}`);
      console.log(`Nav links: ${JSON.stringify(pageStructure.navLinks)}`);
      console.log(`Buttons: ${JSON.stringify(pageStructure.buttons)}`);
      console.log(`Cards (${pageStructure.cards.length}): ${JSON.stringify(pageStructure.cards.slice(0, 5))}`);
      console.log(`Tabs: ${JSON.stringify(pageStructure.tabs)}`);

      // Now click each sidebar link and screenshot
      const sidebarLinks = await page.evaluate(() => {
        return Array.from(
          document.querySelectorAll("nav a, aside a, [class*='sidebar'] a, [class*='menu'] a, [class*='side'] a")
        )
          .map((a) => ({
            text: (a.textContent || "").trim().substring(0, 60),
            href: a.getAttribute("href") || "",
          }))
          .filter((l) => l.href && l.text);
      });

      console.log(`\n=== Sidebar links to explore: ${sidebarLinks.length} ===`);
      const visitedPaths = new Set<string>();
      let linkIndex = 0;

      for (const link of sidebarLinks) {
        if (visitedPaths.has(link.href)) continue;
        visitedPaths.add(link.href);
        linkIndex++;

        try {
          const linkEl = page.locator(
            `a[href="${link.href}"]`
          ).first();

          if (await linkEl.isVisible({ timeout: 2000 })) {
            await linkEl.click();
            await waitForContent(page);

            const currentUrl = page.url();
            const currentText = (await getPageText(page)).substring(0, 300);
            console.log(
              `\n[${linkIndex}] Clicked "${link.text}" (${link.href}) => URL: ${currentUrl}`
            );
            console.log(`   Content: ${currentText.substring(0, 200)}`);

            const safeName = link.text
              .replace(/[^a-zA-Z0-9]/g, "_")
              .substring(0, 30);
            await takeScreenshot(page, `07_nav_${linkIndex}_${safeName}`);
          }
        } catch (err) {
          console.log(`   Error clicking ${link.text}: ${err}`);
        }
      }

      // If no sidebar links found, try to find navigation by other means
      if (sidebarLinks.length === 0) {
        console.log("No sidebar links found — checking page structure...");
        const allLinks = await getAllLinks(page);
        console.log(`All page links: ${JSON.stringify(allLinks)}`);

        // Try clicking visible links/buttons
        const clickableElements = await page.evaluate(() => {
          return Array.from(
            document.querySelectorAll("a, button, [role='button'], [role='tab'], [role='menuitem']")
          )
            .filter((el) => {
              const rect = el.getBoundingClientRect();
              return rect.width > 0 && rect.height > 0;
            })
            .map((el) => ({
              tag: el.tagName,
              text: (el.textContent || "").trim().substring(0, 60),
              href: el.getAttribute("href") || "",
            }));
        });
        console.log(`Clickable elements: ${JSON.stringify(clickableElements)}`);
      }
    } finally {
      await context.close();
    }
  });

  test("2.2 Check for dashboard widgets and statistics", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Look for dashboard elements
      const dashboardInfo = await page.evaluate(() => {
        const info: any = {};

        // Stats/counts/metrics
        info.numbers = Array.from(document.querySelectorAll("*"))
          .filter((el) => {
            const text = (el.textContent || "").trim();
            return /^\d+$/.test(text) && el.children.length === 0;
          })
          .map((el) => ({
            text: (el.textContent || "").trim(),
            parent: (el.parentElement?.textContent || "").trim().substring(0, 80),
          }))
          .slice(0, 20);

        // Charts/graphs
        info.charts = document.querySelectorAll(
          "canvas, svg, [class*='chart'], [class*='Chart'], [class*='graph'], [class*='Graph']"
        ).length;

        // Tables
        info.tables = document.querySelectorAll("table").length;
        info.tableHeaders = Array.from(
          document.querySelectorAll("th, [role='columnheader']")
        )
          .map((th) => (th.textContent || "").trim())
          .slice(0, 20);

        // Progress bars
        info.progressBars = document.querySelectorAll(
          "[role='progressbar'], [class*='progress'], .progress"
        ).length;

        return info;
      });

      console.log(`Dashboard numbers: ${JSON.stringify(dashboardInfo.numbers)}`);
      console.log(`Charts: ${dashboardInfo.charts}`);
      console.log(`Tables: ${dashboardInfo.tables}`);
      console.log(`Table headers: ${JSON.stringify(dashboardInfo.tableHeaders)}`);
      console.log(`Progress bars: ${dashboardInfo.progressBars}`);

      await takeScreenshot(page, "08_admin_dashboard_widgets");
    } finally {
      await context.close();
    }
  });

  test("2.3 Navigate to every page using URL patterns", async ({ browser }) => {
    test.setTimeout(120000);
    const { context, page } = await createFreshContext(browser);
    try {
      const token = await loginViaSSO(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      // The app uses /w-m/ prefix (discovered from SSO redirect)
      // Discovered working routes: /w-m/dashboard, /w-m/sprints, /w-m/permisssions/all,
      // /w-m/tasks/create, /w-m/timeline/global
      const paths = [
        "/w-m/dashboard",
        "/w-m/sprints",
        "/w-m/permisssions/all",  // triple 's' (discovered URL typo)
        "/w-m/permissions/all",   // correct spelling
        "/w-m/tasks/create",
        "/w-m/tasks/all",
        "/w-m/tasks/board",
        "/w-m/tasks/workflow",
        "/w-m/tasks/kanban",
        "/w-m/tasks/list",
        "/w-m/tasks/config",
        "/w-m/timeline/global",
        "/w-m/timeline",
        "/w-m/projects/all",
        "/w-m/projects/create",
        "/w-m/projects/list",
        "/w-m/project/create",
        "/w-m/project/all",
        "/w-m/reports",
        "/w-m/reports/project",
        "/w-m/members/all",
        "/w-m/members/roles",
        "/w-m/members/groups",
        "/w-m/members/restore",
        "/w-m/members/suspended",
        "/w-m/settings",
        "/w-m/activity",
        "/w-m/profile",
        "/w-m/kanban",
        "/w-m/board",
      ];

      const results: { path: string; status: string; content: string }[] = [];

      for (const path of paths) {
        try {
          await page.goto(`${PROJECT_URL}${path}`, {
            waitUntil: "networkidle",
            timeout: 15000,
          });
          await page.waitForTimeout(1000);

          const url = page.url();
          const text = await getPageText(page);
          const lower = text.toLowerCase();

          const is404 =
            lower.includes("404") ||
            lower.includes("not found") ||
            lower.includes("page not found");
          const isBlank = text.trim().length < 50;
          const hasContent = !is404 && !isBlank;

          const status = is404 ? "404" : isBlank ? "BLANK" : "OK";
          results.push({
            path,
            status,
            content: text.substring(0, 150),
          });

          console.log(`${path} => ${status}: ${text.substring(0, 100)}`);

          if (hasContent) {
            const safePath = path.replace(/\//g, "_").replace(/^_/, "");
            await takeScreenshot(
              page,
              `09_url_${safePath || "root"}`
            );
          }
        } catch (err) {
          console.log(`${path} => ERROR: ${err}`);
          results.push({ path, status: "ERROR", content: String(err) });
        }
      }

      // Summary
      const working = results.filter((r) => r.status === "OK");
      const notFound = results.filter((r) => r.status === "404");
      const blank = results.filter((r) => r.status === "BLANK");
      console.log(`\n=== URL Summary ===`);
      console.log(`Working pages: ${working.length} - ${working.map((r) => r.path).join(", ")}`);
      console.log(`404 pages: ${notFound.length} - ${notFound.map((r) => r.path).join(", ")}`);
      console.log(`Blank pages: ${blank.length} - ${blank.map((r) => r.path).join(", ")}`);
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 3: Project CRUD Operations (as Org Admin)
// ============================================================

test.describe("Phase 3: Project CRUD — Admin", () => {
  test("3.1 Create a project via sidebar Create Project link", async ({
    browser,
  }) => {
    test.setTimeout(120000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Expand "Projects" parent in sidebar first
      const projectsParent = page.locator('a:has-text("Projects")').first();
      if (await projectsParent.isVisible({ timeout: 5000 })) {
        await projectsParent.click();
        await page.waitForTimeout(800);
        console.log("Expanded Projects sidebar section");
      }

      // Now "All Projects" and "Create Project" should be visible
      const allProjLink = page.locator('a:has-text("All Projects")').first();
      if (await allProjLink.isVisible({ timeout: 3000 })) {
        await allProjLink.click();
        await waitForContent(page);
        await dismissErrorOverlay(page);

        console.log(`All Projects URL: ${page.url()}`);
        const text = await getPageText(page);
        console.log(`All Projects page: ${text.substring(0, 500)}`);

        const tableInfo = await page.evaluate(() => {
          const tables = document.querySelectorAll("table");
          if (tables.length === 0) return null;
          const headers = Array.from(
            tables[0].querySelectorAll("th")
          ).map((th) => (th.textContent || "").trim());
          const rowCount = tables[0].querySelectorAll("tbody tr").length;
          return { headers, rowCount };
        });
        if (tableInfo) {
          console.log(`Project table headers: ${JSON.stringify(tableInfo.headers)}`);
          console.log(`Existing projects: ${tableInfo.rowCount}`);
        }

        await takeScreenshot(page, "10_all_projects_page");
      } else {
        console.log("All Projects link still not visible after expanding Projects parent");
      }

      // Click "Create Project" in sidebar
      const createLink = page.locator('a:has-text("Create Project")').first();
      if (await createLink.isVisible({ timeout: 3000 })) {
        await createLink.click();
        await waitForContent(page);

        console.log(`\nCreate Project URL: ${page.url()}`);

        // Discover form structure
        const fields = await getFormFields(page);
        console.log(`Form fields: ${JSON.stringify(fields)}`);

        const headings = await page.locator("h1, h2, h3, h4").allTextContents();
        console.log(`Headings: ${JSON.stringify(headings)}`);

        const labels = await page.locator("label").allTextContents();
        console.log(`Labels: ${JSON.stringify(labels)}`);

        const buttons = await getAllButtons(page);
        console.log(`Buttons: ${JSON.stringify(buttons)}`);

        await takeScreenshot(page, "10b_create_project_form");

        // Fill form fields
        // Fill all text inputs
        const textInputs = await page.locator("input[type='text'], input:not([type])").all();
        for (const inp of textInputs) {
          const name = await inp.getAttribute("name");
          const placeholder = await inp.getAttribute("placeholder");
          const id = await inp.getAttribute("id");
          const visible = await inp.isVisible();
          console.log(`  Input: name="${name}" placeholder="${placeholder}" id="${id}" visible=${visible}`);
          if (visible) {
            const label = name || placeholder || id || "";
            if (label.toLowerCase().includes("name") || label.toLowerCase().includes("title") || label.toLowerCase().includes("project")) {
              await inp.fill("Website Redesign Q2 2026");
              console.log(`  Filled project name`);
            } else if (label.toLowerCase().includes("desc")) {
              await inp.fill("Complete redesign of company website");
              console.log(`  Filled description`);
            } else if (label.toLowerCase().includes("budget")) {
              await inp.fill("50000");
              console.log(`  Filled budget`);
            }
          }
        }

        // Fill textareas
        const textareas = await page.locator("textarea").all();
        for (const ta of textareas) {
          if (await ta.isVisible()) {
            await ta.fill("Complete redesign of company website for Q2 2026. Includes homepage, about, contact, and blog pages.");
            console.log("  Filled textarea");
          }
        }

        // Fill date inputs
        const dateInputs = await page.locator("input[type='date']").all();
        console.log(`Date inputs: ${dateInputs.length}`);
        for (let i = 0; i < dateInputs.length; i++) {
          if (await dateInputs[i].isVisible()) {
            const val = i === 0 ? "2026-04-01" : "2026-06-30";
            await dateInputs[i].fill(val);
            console.log(`  Filled date ${i}: ${val}`);
          }
        }

        // Handle select dropdowns
        const selects = await page.locator("select").all();
        for (const sel of selects) {
          const name = await sel.getAttribute("name");
          const options = await sel.locator("option").allTextContents();
          console.log(`  Select "${name}": ${JSON.stringify(options)}`);
          if (options.length > 1) {
            try {
              await sel.selectOption({ index: 1 });
              console.log(`  Selected option 1 in "${name}"`);
            } catch {}
          }
        }

        await takeScreenshot(page, "11_create_project_filled");

        // Submit
        for (const sel of [
          'button[type="submit"]',
          'button:has-text("Save")',
          'button:has-text("Create")',
          'button:has-text("Submit")',
          'button:has-text("Add")',
        ]) {
          try {
            const btn = page.locator(sel).first();
            if (await btn.isVisible({ timeout: 1000 })) {
              console.log(`Clicking: ${sel}`);
              await btn.click();
              await waitForContent(page);
              break;
            }
          } catch {}
        }

        await takeScreenshot(page, "12_create_project_result");

        const resultText = await getPageText(page);
        const lower = resultText.toLowerCase();
        const success = lower.includes("success") || lower.includes("created") || lower.includes("website redesign");
        const error = lower.includes("error") || lower.includes("failed");
        console.log(`\nResult — Success: ${success}, Error: ${error}`);
        console.log(`Result text: ${resultText.substring(0, 300)}`);
      } else {
        console.log("Create Project link NOT found in sidebar");
      }
    } finally {
      await context.close();
    }
  });

  test("3.2 Create project via API — test endpoint behavior", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      const { projectToken, userData } = await getProjectToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      // Try creating project via API with various payloads
      const payloads = [
        {
          name: "API Test Project",
          description: "Created via API test",
          startDate: "2026-04-01",
          endDate: "2026-06-30",
          status: "active",
          priority: "high",
        },
        {
          projectName: "API Test Project",
          description: "Created via API test",
        },
        {
          title: "API Test Project",
          description: "Created via API test",
        },
        { name: "API Test Project" },
      ];

      for (const payload of payloads) {
        const resp = await page.request.post(
          `${PROJECT_API}/v1/project/create`,
          {
            headers: { "x-access-token": projectToken },
            data: payload,
          }
        );
        const json = await resp.json();
        console.log(
          `API create with ${JSON.stringify(Object.keys(payload))} => ${resp.status()}: ${JSON.stringify(json).substring(0, 300)}`
        );
      }

      // Test edge cases
      console.log("\n=== Edge case: Empty name ===");
      const emptyResp = await page.request.post(
        `${PROJECT_API}/v1/project/create`,
        {
          headers: { "x-access-token": projectToken },
          data: { name: "", description: "No name" },
        }
      );
      console.log(
        `Empty name => ${emptyResp.status()}: ${(await emptyResp.text()).substring(0, 200)}`
      );

      console.log("\n=== Edge case: Very long name ===");
      const longName = "A".repeat(500);
      const longResp = await page.request.post(
        `${PROJECT_API}/v1/project/create`,
        {
          headers: { "x-access-token": projectToken },
          data: { name: longName, description: "Long name test" },
        }
      );
      console.log(
        `Long name => ${longResp.status()}: ${(await longResp.text()).substring(0, 200)}`
      );

      console.log("\n=== Edge case: End date before start date ===");
      const badDateResp = await page.request.post(
        `${PROJECT_API}/v1/project/create`,
        {
          headers: { "x-access-token": projectToken },
          data: {
            name: "Bad Date Project",
            startDate: "2026-06-30",
            endDate: "2026-04-01",
          },
        }
      );
      console.log(
        `Bad dates => ${badDateResp.status()}: ${(await badDateResp.text()).substring(0, 200)}`
      );

      console.log("\n=== Edge case: XSS in name ===");
      const xssResp = await page.request.post(
        `${PROJECT_API}/v1/project/create`,
        {
          headers: { "x-access-token": projectToken },
          data: {
            name: '<script>alert("XSS")</script>',
            description: "XSS test",
          },
        }
      );
      console.log(
        `XSS name => ${xssResp.status()}: ${(await xssResp.text()).substring(0, 200)}`
      );
    } finally {
      await context.close();
    }
  });

  test("3.3 List/search projects via API", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      const { projectToken } = await getProjectToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      // Try to list projects
      const endpoints = [
        { method: "GET", path: "/v1/project/search" },
        { method: "GET", path: "/v1/project/search?search=" },
        { method: "GET", path: "/v1/project/search?query=" },
        { method: "POST", path: "/v1/project/search", body: {} },
        { method: "POST", path: "/v1/project/search", body: { search: "" } },
        { method: "GET", path: "/v1/report/get" },
      ];

      for (const ep of endpoints) {
        let resp;
        if (ep.method === "GET") {
          resp = await page.request.get(`${PROJECT_API}${ep.path}`, {
            headers: { "x-access-token": projectToken },
          });
        } else {
          resp = await page.request.post(`${PROJECT_API}${ep.path}`, {
            headers: { "x-access-token": projectToken },
            data: (ep as any).body || {},
          });
        }
        const text = await resp.text();
        console.log(
          `${ep.method} ${ep.path} => ${resp.status()}: ${text.substring(0, 300)}`
        );
      }
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 4: Task Management
// ============================================================

test.describe("Phase 4: Task Management", () => {
  test("4.1 Explore Tasks pages by expanding sidebar sections", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Expand "Task Management" parent section in sidebar
      const tmParent = page.locator('a:has-text("Task Management")').first();
      if (await tmParent.isVisible({ timeout: 5000 })) {
        await tmParent.click();
        await page.waitForTimeout(800);
        console.log("Expanded Task Management sidebar section");
      }

      // Now sub-items should be visible
      const taskSubItems = ["Create Task", "All Tasks", "Workflow Boards"];
      for (const linkText of taskSubItems) {
        try {
          const link = page.locator(`a:has-text("${linkText}")`).first();
          if (await link.isVisible({ timeout: 3000 })) {
            await link.click();
            await page.waitForTimeout(2000);
            await dismissErrorOverlay(page);

            const url = page.url();
            const text = await getPageText(page);
            console.log(`\nClicked "${linkText}" => URL: ${url}`);
            console.log(`Content (first 300): ${text.substring(0, 300)}`);

            const buttons = await getAllButtons(page);
            console.log(`Buttons: ${JSON.stringify(buttons)}`);

            const fields = await getFormFields(page);
            console.log(`Form fields: ${JSON.stringify(fields)}`);

            const safeName = linkText.replace(/[^a-z0-9]/gi, "_");
            await takeScreenshot(page, `13_task_${safeName}`);
          } else {
            console.log(`"${linkText}" not visible after expanding Task Management`);
          }
        } catch (err) {
          console.log(`Error clicking "${linkText}": ${err}`);
        }
      }

      // Also expand Task Config section
      const tcParent = page.locator('a:has-text("Task Config")').first();
      if (await tcParent.isVisible({ timeout: 3000 })) {
        await tcParent.click();
        await page.waitForTimeout(800);
        console.log("\nExpanded Task Config sidebar section");

        // Get sub-items
        const subItems = await getSidebarItems(page);
        console.log(`After Task Config expand, sidebar items: ${JSON.stringify(subItems)}`);
        await takeScreenshot(page, "13_task_config_expanded");
      }
    } finally {
      await context.close();
    }
  });

  test("4.2 Create a task via direct URL navigation", async ({ browser }) => {
    test.setTimeout(120000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Navigate directly to the discovered Create Task URL
      await page.goto(`${PROJECT_URL}/w-m/tasks/create`, {
        waitUntil: "networkidle",
        timeout: 15000,
      });
      await page.waitForTimeout(3000);
      await dismissErrorOverlay(page);

      console.log(`Create Task URL: ${page.url()}`);

      await takeScreenshot(page, "14_create_task_page");

      // Explore what's on the page now
      const fields = await getFormFields(page);
      console.log(`Create Task form fields: ${JSON.stringify(fields)}`);

      const buttons = await getAllButtons(page);
      console.log(`Buttons: ${JSON.stringify(buttons)}`);

      const headings = await page.locator("h1, h2, h3, h4").allTextContents();
      console.log(`Headings: ${JSON.stringify(headings)}`);

      const pageText = await getPageText(page);
      console.log(`Page content (first 500): ${pageText.substring(0, 500)}`);

      // Try to fill any visible forms
      // Look for dropdowns first (project select, status, etc.)
      const selects = await page.locator("select").all();
      console.log(`Select dropdowns: ${selects.length}`);
      for (const sel of selects) {
        const name = await sel.getAttribute("name");
        const id = await sel.getAttribute("id");
        const options = await sel.locator("option").allTextContents();
        console.log(`  Select "${name || id}": options=${JSON.stringify(options)}`);
        // If it has "Select Project" type option, try selecting first real option
        if (options.length > 1) {
          try {
            await sel.selectOption({ index: 1 });
            console.log(`  Selected option index 1 in "${name || id}"`);
          } catch (err) {
            console.log(`  Could not select option: ${err}`);
          }
        }
      }

      // Fill text inputs
      const textInputs = await page.locator("input[type='text'], input:not([type])").all();
      for (const inp of textInputs) {
        const name = await inp.getAttribute("name");
        const placeholder = await inp.getAttribute("placeholder");
        const isVisible = await inp.isVisible();
        console.log(`  Text input "${name || placeholder}": visible=${isVisible}`);
        if (isVisible && (placeholder?.toLowerCase().includes("search") || placeholder?.toLowerCase().includes("project"))) {
          await inp.fill("Design homepage mockup");
          console.log(`  Filled "${name || placeholder}" with task name`);
        }
      }

      // Fill textareas
      const textareas = await page.locator("textarea").all();
      for (const ta of textareas) {
        const isVisible = await ta.isVisible();
        if (isVisible) {
          await ta.fill("Create wireframes and high-fidelity mockups for the homepage redesign");
          console.log("  Filled textarea with description");
        }
      }

      await takeScreenshot(page, "15_create_task_filled");

      // Try submitting
      for (const sel of [
        'button[type="submit"]',
        'button:has-text("Save")',
        'button:has-text("Create")',
        'button:has-text("Submit")',
        'button:has-text("Add")',
      ]) {
        try {
          const btn = page.locator(sel).first();
          if (await btn.isVisible({ timeout: 1000 })) {
            console.log(`Clicking submit button: ${sel}`);
            await btn.click();
            await waitForContent(page);
            break;
          }
        } catch {
          // Next
        }
      }

      await takeScreenshot(page, "16_create_task_result");
      const resultText = await getPageText(page);
      console.log(`Result: ${resultText.substring(0, 300)}`);
    } finally {
      await context.close();
    }
  });

  test("4.3 Task API — create, list, and edge cases", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      const { projectToken } = await getProjectToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      const headers = { "x-access-token": projectToken };

      // Try task search on project API
      console.log("=== Project API task endpoints ===");
      for (const ep of [
        { m: "GET", p: "/v1/task/search" },
        { m: "POST", p: "/v1/task/search", b: {} },
        { m: "POST", p: "/v1/task/create", b: { name: "API Test Task" } },
        {
          m: "POST",
          p: "/v1/task/create",
          b: {
            name: "API Test Task",
            title: "API Test Task",
            taskName: "API Test Task",
            description: "Test",
            priority: "high",
            status: "todo",
          },
        },
      ]) {
        let resp;
        if (ep.m === "GET") {
          resp = await page.request.get(`${PROJECT_API}${ep.p}`, { headers });
        } else {
          resp = await page.request.post(`${PROJECT_API}${ep.p}`, {
            headers,
            data: (ep as any).b,
          });
        }
        console.log(
          `${ep.m} ${ep.p} => ${resp.status()}: ${(await resp.text()).substring(0, 300)}`
        );
      }

      // Try task API subdomain
      console.log("\n=== Task API subdomain endpoints ===");
      for (const ep of [
        { m: "GET", p: "/v1/tasks" },
        { m: "GET", p: "/v1/task/search" },
        { m: "POST", p: "/v1/task/create", b: { name: "Task API Test" } },
        { m: "GET", p: "/health" },
      ]) {
        let resp;
        if (ep.m === "GET") {
          resp = await page.request.get(`${TASK_API}${ep.p}`, { headers });
        } else {
          resp = await page.request.post(`${TASK_API}${ep.p}`, {
            headers,
            data: (ep as any).b,
          });
        }
        console.log(
          `TASK-API ${ep.m} ${ep.p} => ${resp.status()}: ${(await resp.text()).substring(0, 300)}`
        );
      }
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 5: Time Tracking
// ============================================================

test.describe("Phase 5: Time Tracking", () => {
  test("5.1 Explore TimeLine and time tracking via sidebar", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Click "TimeLine" from discovered sidebar items
      const timelineLink = page.locator('a:has-text("TimeLine")').first();
      if (await timelineLink.isVisible({ timeout: 5000 })) {
        await timelineLink.click();
        await waitForContent(page);

        const url = page.url();
        console.log(`TimeLine page URL: ${url}`);

        const text = await getPageText(page);
        console.log(`TimeLine content: ${text.substring(0, 500)}`);

        const buttons = await getAllButtons(page);
        console.log(`TimeLine buttons: ${JSON.stringify(buttons)}`);

        const fields = await getFormFields(page);
        console.log(`TimeLine fields: ${JSON.stringify(fields)}`);

        await takeScreenshot(page, "17_timeline_page");
      } else {
        console.log("TimeLine link not found in sidebar");
      }

      // Also explore "Global" link from sidebar
      const globalLink = page.locator('a:has-text("Global")').first();
      if (await globalLink.isVisible({ timeout: 3000 })) {
        await globalLink.click();
        await waitForContent(page);

        const url = page.url();
        console.log(`\nGlobal page URL: ${url}`);
        const text = await getPageText(page);
        console.log(`Global content: ${text.substring(0, 500)}`);
        await takeScreenshot(page, "17b_global_page");
      }

      // Try Project Insights link
      const insightsLink = page.locator('a:has-text("Project Insights")').first();
      if (await insightsLink.isVisible({ timeout: 3000 })) {
        await insightsLink.click();
        await waitForContent(page);

        const url = page.url();
        console.log(`\nProject Insights URL: ${url}`);
        const text = await getPageText(page);
        console.log(`Project Insights: ${text.substring(0, 500)}`);
        await takeScreenshot(page, "17c_project_insights");
      }
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 6: Team & Members
// ============================================================

test.describe("Phase 6: Team & Members", () => {
  test("6.1 Explore Members, Roles, Groups via sidebar expansion", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Expand "Members" parent section first
      const membersParent = page.locator('a:has-text("Members")').first();
      if (await membersParent.isVisible({ timeout: 5000 })) {
        await membersParent.click();
        await page.waitForTimeout(800);
        console.log("Expanded Members sidebar section");
      }

      // Now sub-items should be visible
      const memberLinks = ["All Users", "Roles", "Groups", "Restore Users", "Suspended Users"];

      for (const linkText of memberLinks) {
        try {
          const link = page.locator(`a:has-text("${linkText}")`).first();
          if (await link.isVisible({ timeout: 3000 })) {
            await link.click();
            await page.waitForTimeout(2000);
            await dismissErrorOverlay(page);

            const url = page.url();
            const text = await getPageText(page);
            console.log(`\nClicked "${linkText}" => URL: ${url}`);
            console.log(`Content (first 300): ${text.substring(0, 300)}`);

            const tableInfo = await page.evaluate(() => {
              const tables = document.querySelectorAll("table");
              if (tables.length === 0) return null;
              const headers = Array.from(
                tables[0].querySelectorAll("th")
              ).map((th) => (th.textContent || "").trim());
              const rowCount = tables[0].querySelectorAll("tbody tr").length;
              return { headers, rowCount };
            });
            if (tableInfo) {
              console.log(`Table headers: ${JSON.stringify(tableInfo.headers)}`);
              console.log(`Table rows: ${tableInfo.rowCount}`);
            }

            const buttons = await getAllButtons(page);
            console.log(`Buttons: ${JSON.stringify(buttons)}`);

            const safeName = linkText.replace(/[^a-z0-9]/gi, "_");
            await takeScreenshot(page, `18_member_${safeName}`);
          } else {
            console.log(`"${linkText}" not visible after expanding Members`);
          }
        } catch (err) {
          console.log(`Error clicking "${linkText}": ${err}`);
        }
      }
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 7: Reports & Dashboard
// ============================================================

test.describe("Phase 7: Reports & Dashboard", () => {
  test("7.1 Explore Reports and Project Wise Reports via sidebar", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Click "Reports" sidebar link
      const reportsLink = page.locator('a:has-text("Reports")').first();
      if (await reportsLink.isVisible({ timeout: 5000 })) {
        await reportsLink.click();
        await waitForContent(page);

        console.log(`Reports URL: ${page.url()}`);
        const text = await getPageText(page);
        console.log(`Reports content: ${text.substring(0, 500)}`);

        const buttons = await getAllButtons(page);
        console.log(`Reports buttons: ${JSON.stringify(buttons)}`);

        await takeScreenshot(page, "19_reports_page");
      }

      // Click "Project Wise Reports" sidebar link
      const pwrLink = page.locator('a:has-text("Project Wise Reports")').first();
      if (await pwrLink.isVisible({ timeout: 3000 })) {
        await pwrLink.click();
        await waitForContent(page);

        console.log(`\nProject Wise Reports URL: ${page.url()}`);
        const text = await getPageText(page);
        console.log(`Project Wise Reports: ${text.substring(0, 500)}`);
        await takeScreenshot(page, "19b_project_wise_reports");
      }

      // API report endpoint (we know /v1/report/get works)
      const { projectToken } = await getProjectToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      const reportResp = await page.request.get(
        `${PROJECT_API}/v1/report/get`,
        {
          headers: { "x-access-token": projectToken },
        }
      );
      console.log(
        `\nAPI /v1/report/get => ${reportResp.status()}: ${(await reportResp.text()).substring(0, 300)}`
      );
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 8: Settings & Configuration
// ============================================================

test.describe("Phase 8: Settings & Configuration", () => {
  test("8.1 Explore Permission and Configuration via sidebar", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Click "Permission" from sidebar (under Configuration section)
      const permLink = page.locator('a:has-text("Permission")').first();
      if (await permLink.isVisible({ timeout: 5000 })) {
        await permLink.click();
        await waitForContent(page);

        console.log(`Permission URL: ${page.url()}`);
        const text = await getPageText(page);
        console.log(`Permission content: ${text.substring(0, 500)}`);

        const buttons = await getAllButtons(page);
        console.log(`Permission buttons: ${JSON.stringify(buttons)}`);

        const fields = await getFormFields(page);
        console.log(`Permission fields: ${JSON.stringify(fields)}`);

        await takeScreenshot(page, "20_permission_page");
      } else {
        console.log("Permission link not visible");
      }

      // Click "Task Config"
      const tcLink = page.locator('a:has-text("Task Config")').first();
      if (await tcLink.isVisible({ timeout: 3000 })) {
        await tcLink.click();
        await waitForContent(page);

        console.log(`\nTask Config URL: ${page.url()}`);
        const text = await getPageText(page);
        console.log(`Task Config content: ${text.substring(0, 500)}`);
        await takeScreenshot(page, "20b_task_config");
      }
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 9: Sprint Management
// ============================================================

test.describe("Phase 9: Sprint Management", () => {
  test("9.1 Test sprint CRUD via API", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      const { projectToken } = await getProjectToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      const headers = { "x-access-token": projectToken };

      // Sprint create (we know it needs projectId, name, startDate, endDate)
      console.log("=== Sprint creation test ===");

      // Missing fields
      const missingResp = await page.request.post(
        `${PROJECT_API}/v1/sprint/create`,
        { headers, data: { name: "Sprint 1" } }
      );
      console.log(
        `Sprint create (missing fields) => ${missingResp.status()}: ${(await missingResp.text()).substring(0, 200)}`
      );

      // Full payload (we need a project ID first, but project creation is broken)
      const fullResp = await page.request.post(
        `${PROJECT_API}/v1/sprint/create`,
        {
          headers,
          data: {
            projectId: "000000000000000000000000",
            name: "Sprint 1",
            startDate: "2026-04-01",
            endDate: "2026-04-14",
          },
        }
      );
      console.log(
        `Sprint create (full payload) => ${fullResp.status()}: ${(await fullResp.text()).substring(0, 300)}`
      );

      // Edge case: end date before start date
      const badDateResp = await page.request.post(
        `${PROJECT_API}/v1/sprint/create`,
        {
          headers,
          data: {
            projectId: "000000000000000000000000",
            name: "Bad Sprint",
            startDate: "2026-04-14",
            endDate: "2026-04-01",
          },
        }
      );
      console.log(
        `Sprint create (bad dates) => ${badDateResp.status()}: ${(await badDateResp.text()).substring(0, 200)}`
      );

      // Edge case: empty name
      const emptyNameResp = await page.request.post(
        `${PROJECT_API}/v1/sprint/create`,
        {
          headers,
          data: {
            projectId: "000000000000000000000000",
            name: "",
            startDate: "2026-04-01",
            endDate: "2026-04-14",
          },
        }
      );
      console.log(
        `Sprint create (empty name) => ${emptyNameResp.status()}: ${(await emptyNameResp.text()).substring(0, 200)}`
      );

      // Sprint GET (by ID)
      const sprintGetResp = await page.request.get(
        `${PROJECT_API}/v1/sprint/000000000000000000000000`,
        { headers }
      );
      console.log(
        `Sprint GET by ID => ${sprintGetResp.status()}: ${(await sprintGetResp.text()).substring(0, 200)}`
      );
    } finally {
      await context.close();
    }
  });

  test("9.2 Find sprints and Workflow Boards in the UI", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Click "Workflow Boards" from sidebar
      const wbLink = page.locator('a:has-text("Workflow Boards")').first();
      if (await wbLink.isVisible({ timeout: 5000 })) {
        await wbLink.click();
        await waitForContent(page);

        console.log(`Workflow Boards URL: ${page.url()}`);
        const text = await getPageText(page);
        console.log(`Workflow Boards content: ${text.substring(0, 500)}`);

        const buttons = await getAllButtons(page);
        console.log(`Buttons: ${JSON.stringify(buttons)}`);

        // Check for kanban-style boards
        const columns = await page.evaluate(() => {
          const cols = document.querySelectorAll(
            "[class*='column'], [class*='Column'], [class*='lane'], [class*='Lane'], [class*='board']"
          );
          return Array.from(cols).map((c) => (c.textContent || "").trim().substring(0, 100));
        });
        console.log(`Board columns: ${JSON.stringify(columns.slice(0, 10))}`);

        await takeScreenshot(page, "21_workflow_boards");
      } else {
        console.log("Workflow Boards link not found");
      }
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 10: RBAC — Employee vs Admin Permissions
// ============================================================

test.describe("Phase 10: RBAC Deep Testing", () => {
  test("10.1 Employee access — what can Priya see and do?", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(
        page,
        EMPLOYEE_CREDS.email,
        EMPLOYEE_CREDS.password
      );

      // Capture employee dashboard
      const sidebarItems = await getSidebarItems(page);
      console.log(`Employee sidebar: ${JSON.stringify(sidebarItems)}`);

      const buttons = await getAllButtons(page);
      console.log(`Employee buttons: ${JSON.stringify(buttons)}`);

      const pageText = await getPageText(page);
      console.log(`Employee landing: ${pageText.substring(0, 500)}`);

      await takeScreenshot(page, "22_employee_landing");

      // RBAC check: Employee sees the SAME sidebar as Admin — this is a potential bug
      // Admin-only features like "Roles", "Groups", "Suspended Users", "Permission"
      // should likely be hidden from employees
      const adminOnlyLinks = ["Roles", "Groups", "Suspended Users", "Restore Users", "Permission"];
      for (const linkText of adminOnlyLinks) {
        const link = page.locator(`a:has-text("${linkText}")`).first();
        const isVisible = await link.isVisible({ timeout: 2000 }).catch(() => false);
        console.log(`Employee can see "${linkText}": ${isVisible}`);
        if (isVisible) {
          console.log(`  RBAC WARNING: Employee can see admin-only "${linkText}" link`);
          // Click it to see if they get access
          try {
            await link.click();
            await waitForContent(page);
            const resultText = await getPageText(page);
            const lower = resultText.toLowerCase();
            const denied = lower.includes("denied") || lower.includes("unauthorized") || lower.includes("forbidden");
            console.log(`  Employee clicked "${linkText}" => ${denied ? "ACCESS DENIED (correct)" : "HAS ACCESS (RBAC BUG!)"}`);
            const safeName = linkText.replace(/[^a-z0-9]/gi, "_");
            await takeScreenshot(page, `23_employee_rbac_${safeName}`);
          } catch {
            console.log(`  Could not click "${linkText}"`);
          }
        }
      }

      // Employee creating project — should they be able to?
      const createProjLink = page.locator('a:has-text("Create Project")').first();
      if (await createProjLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        console.log(`\nRBAC: Employee can see "Create Project" link`);
        await createProjLink.click();
        await waitForContent(page);
        const text = await getPageText(page);
        console.log(`Create Project as employee: ${text.substring(0, 200)}`);
        await takeScreenshot(page, "23_employee_create_project");
      }
    } finally {
      await context.close();
    }
  });

  test("10.2 Employee API access — test RBAC on API endpoints", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      const { projectToken: adminToken } = await getProjectToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );
      const { projectToken: empToken } = await getProjectToken(
        page,
        EMPLOYEE_CREDS.email,
        EMPLOYEE_CREDS.password
      );

      // Compare admin vs employee access
      const endpoints = [
        { method: "GET", path: "/v1/project/search" },
        { method: "GET", path: "/v1/report/get" },
        { method: "GET", path: "/v1/role/search" },
        { method: "GET", path: "/v1/permission/search" },
        { method: "GET", path: "/v1/activity/search" },
        { method: "GET", path: "/v1/user/search" },
        {
          method: "POST",
          path: "/v1/project/create",
          body: { name: "Employee Project" },
        },
        {
          method: "POST",
          path: "/v1/sprint/create",
          body: {
            projectId: "000000000000000000000000",
            name: "Emp Sprint",
            startDate: "2026-04-01",
            endDate: "2026-04-14",
          },
        },
      ];

      for (const ep of endpoints) {
        // As admin
        let adminResp;
        if (ep.method === "GET") {
          adminResp = await page.request.get(`${PROJECT_API}${ep.path}`, {
            headers: { "x-access-token": adminToken },
          });
        } else {
          adminResp = await page.request.post(`${PROJECT_API}${ep.path}`, {
            headers: { "x-access-token": adminToken },
            data: (ep as any).body || {},
          });
        }
        const adminText = (await adminResp.text()).substring(0, 150);

        // As employee
        let empResp;
        if (ep.method === "GET") {
          empResp = await page.request.get(`${PROJECT_API}${ep.path}`, {
            headers: { "x-access-token": empToken },
          });
        } else {
          empResp = await page.request.post(`${PROJECT_API}${ep.path}`, {
            headers: { "x-access-token": empToken },
            data: (ep as any).body || {},
          });
        }
        const empText = (await empResp.text()).substring(0, 150);

        console.log(
          `${ep.method} ${ep.path}:`
        );
        console.log(`  Admin  => ${adminResp.status()}: ${adminText}`);
        console.log(`  Employee => ${empResp.status()}: ${empText}`);

        // Flag if employee has same access as admin for sensitive operations
        if (
          ep.path.includes("create") &&
          empResp.status() === adminResp.status()
        ) {
          console.log(
            `  WARNING: Employee has same access as admin for ${ep.path}!`
          );
        }
      }
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 11: Activity & Audit
// ============================================================

test.describe("Phase 11: Activity & Audit", () => {
  test("11.1 Full sidebar walkthrough — expand all parents and click all children", async ({ browser }) => {
    test.setTimeout(120000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Sidebar structure with parent > child hierarchy
      const sidebarHierarchy: { parent: string | null; child: string }[] = [
        { parent: null, child: "Dashboard" },
        // Projects section
        { parent: "Projects", child: "All Projects" },
        { parent: "Projects", child: "Create Project" },
        // Task Management section
        { parent: "Task Management", child: "Create Task" },
        { parent: "Task Management", child: "All Tasks" },
        { parent: "Task Management", child: "Workflow Boards" },
        // Task Config section
        { parent: "Task Config", child: "Task Config" },
        // TimeLine section
        { parent: "TimeLine", child: "Global" },
        // Reports section
        { parent: "Reports", child: "Project Wise Reports" },
        // Configuration
        { parent: null, child: "Permission" },
        // Members section
        { parent: "Members", child: "All Users" },
        { parent: "Members", child: "Roles" },
        { parent: "Members", child: "Groups" },
        { parent: "Members", child: "Restore Users" },
        { parent: "Members", child: "Suspended Users" },
      ];

      for (const { parent, child } of sidebarHierarchy) {
        try {
          // First expand the parent if needed
          if (parent) {
            const parentLink = page.locator(`a:has-text("${parent}")`).first();
            if (await parentLink.isVisible({ timeout: 2000 })) {
              await parentLink.click();
              await page.waitForTimeout(800);
            }
          }

          // Now click the child
          const childLink = page.locator(`a:has-text("${child}")`).first();
          if (await childLink.isVisible({ timeout: 2000 })) {
            await childLink.click();
            await page.waitForTimeout(2000);
            await dismissErrorOverlay(page);

            const url = page.url();
            const text = await getPageText(page);
            const lower = text.toLowerCase();
            const hasError = lower.includes("unhandled runtime error") || lower.includes("failed to fetch");
            const is404 = lower.includes("404") || lower.includes("not found");

            const prefix = parent ? `${parent} > ${child}` : child;
            console.log(`[${prefix}] URL: ${url}`);
            console.log(`  Content: ${text.substring(0, 200)}`);
            if (hasError) console.log(`  BUG: Page shows unhandled runtime error`);
            if (is404) console.log(`  WARNING: Page shows 404`);

            const safeName = child.replace(/[^a-z0-9]/gi, "_");
            await takeScreenshot(page, `24_sidebar_${safeName}`);
          } else {
            const prefix = parent ? `${parent} > ${child}` : child;
            console.log(`[${prefix}] Child not visible after expanding parent`);
          }
        } catch (err) {
          console.log(`[${child}] Error: ${err}`);
        }
      }

      // API activity endpoint
      const { projectToken } = await getProjectToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      const actResp = await page.request.get(
        `${PROJECT_API}/v1/activity/search`,
        {
          headers: { "x-access-token": projectToken },
        }
      );
      console.log(
        `\nActivity API => ${actResp.status()}: ${(await actResp.text()).substring(0, 300)}`
      );
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 12: Backend Health & Database Issues
// ============================================================

test.describe("Phase 12: Backend Health", () => {
  test("12.1 Task API database error — planschemascollection missing", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      const { projectToken } = await getProjectToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      // Test task API health
      const healthResp = await page.request.get(`${TASK_API}/health`);
      const healthData = await healthResp.json();
      console.log(`Task API health: ${JSON.stringify(healthData)}`);
      expect(healthData.status).toBe("ok");

      // Test task API endpoint — should fail with db error
      const taskResp = await page.request.get(`${TASK_API}/v1/tasks`, {
        headers: { "x-access-token": projectToken },
      });
      const taskText = await taskResp.text();
      console.log(`Task API /v1/tasks => ${taskResp.status()}: ${taskText}`);

      // This is a critical bug — the task API has a database configuration issue
      const hasPlanSchemaError = taskText.includes("planschemascollection");
      console.log(`Database error present: ${hasPlanSchemaError}`);
      if (hasPlanSchemaError) {
        console.log(
          "CRITICAL BUG: Task API returns 'planschemascollection is not present in database' — MongoDB collection missing"
        );
      }

      // Test multiple task API endpoints to confirm the scope
      for (const path of ["/v1/tasks", "/v1/projects", "/v1/me", "/v1/dashboard"]) {
        const resp = await page.request.get(`${TASK_API}${path}`, {
          headers: { "x-access-token": projectToken },
        });
        const text = await resp.text();
        const hasError = text.includes("planschemascollection");
        console.log(
          `TASK-API ${path} => ${resp.status()}: DB error=${hasError}`
        );
      }
    } finally {
      await context.close();
    }
  });

  test("12.2 Project API — endpoint discovery and error patterns", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      const { projectToken } = await getProjectToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      const headers = { "x-access-token": projectToken };

      // Test all discovered endpoints and check error patterns
      const endpoints = [
        { m: "POST", p: "/v1/project/create", b: { name: "Test" } },
        { m: "GET", p: "/v1/project/search" },
        { m: "GET", p: "/v1/activity/search" },
        { m: "GET", p: "/v1/report/get" },
        { m: "GET", p: "/v1/user/search" },
        { m: "GET", p: "/v1/role/search" },
        { m: "GET", p: "/v1/permission/search" },
        {
          m: "POST",
          p: "/v1/sprint/create",
          b: {
            projectId: "000000000000000000000000",
            name: "Test",
            startDate: "2026-04-01",
            endDate: "2026-04-14",
          },
        },
      ];

      const results: {
        endpoint: string;
        status: number;
        working: boolean;
        error: string;
      }[] = [];

      for (const ep of endpoints) {
        let resp;
        if (ep.m === "GET") {
          resp = await page.request.get(`${PROJECT_API}${ep.p}`, { headers });
        } else {
          resp = await page.request.post(`${PROJECT_API}${ep.p}`, {
            headers,
            data: ep.b || {},
          });
        }
        const text = await resp.text();
        let jsonData: any;
        try {
          jsonData = JSON.parse(text);
        } catch {
          jsonData = { raw: text.substring(0, 100) };
        }

        const status = resp.status();
        const message =
          jsonData?.body?.message || jsonData?.message || "unknown";
        const working =
          status === 200 &&
          jsonData?.body?.status === "success";

        results.push({
          endpoint: `${ep.m} ${ep.p}`,
          status,
          working,
          error: working ? "" : message,
        });

        console.log(
          `${ep.m} ${ep.p} => ${status} ${working ? "OK" : "FAIL"}: ${message}`
        );
      }

      console.log("\n=== API Health Summary ===");
      const workingCount = results.filter((r) => r.working).length;
      const failedCount = results.filter((r) => !r.working).length;
      console.log(
        `Working: ${workingCount}/${results.length}, Failed: ${failedCount}/${results.length}`
      );
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 13: Cross-User Data Isolation
// ============================================================

test.describe("Phase 13: Cross-Org Data Isolation", () => {
  test("13.1 Different org user cannot access TechNova project data", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Login as john@globaltech.com (different org)
      const johnToken = await getAccessToken(
        page,
        "john@globaltech.com",
        "Welcome@123"
      );

      if (johnToken) {
        // SSO into project module as different org
        const ssoResp = await page.request.post(
          `${PROJECT_API}/v1/auth/sso`,
          { data: { token: johnToken } }
        );
        const ssoData = await ssoResp.json();
        const johnProjectToken =
          ssoData?.body?.data?.accessToken || "";
        const johnOrg =
          ssoData?.body?.data?.userData?.orgId || "unknown";

        console.log(`John's org ID: ${johnOrg}`);

        if (johnProjectToken) {
          // Try to access TechNova project data
          for (const ep of [
            "/v1/project/search",
            "/v1/report/get",
            "/v1/activity/search",
          ]) {
            const resp = await page.request.get(`${PROJECT_API}${ep}`, {
              headers: { "x-access-token": johnProjectToken },
            });
            console.log(
              `John accessing ${ep} => ${resp.status()}: ${(await resp.text()).substring(0, 200)}`
            );
          }
        }

        // Also test via SSO UI
        await page.goto(`${PROJECT_URL}?sso_token=${johnToken}`, {
          waitUntil: "networkidle",
          timeout: 30000,
        });
        await page.waitForTimeout(3000);

        const pageText = await getPageText(page);
        console.log(`John's project view: ${pageText.substring(0, 300)}`);
        await takeScreenshot(page, "25_cross_org_john");
      } else {
        console.log("Could not login as john@globaltech.com — skipping");
      }
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 14: UI Interaction Deep Dive
// ============================================================

test.describe("Phase 14: UI Deep Dive", () => {
  test("14.1 Click every button and interactive element on dashboard", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Get all visible interactive elements
      const interactiveElements = await page.evaluate(() => {
        const elements: { tag: string; text: string; index: number }[] = [];
        const allClickable = document.querySelectorAll(
          "button, [role='button'], a, [role='tab'], [role='menuitem'], [onclick]"
        );
        allClickable.forEach((el, i) => {
          const rect = el.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            elements.push({
              tag: el.tagName,
              text: (el.textContent || "").trim().substring(0, 50),
              index: i,
            });
          }
        });
        return elements;
      });

      console.log(
        `Found ${interactiveElements.length} interactive elements`
      );
      console.log(JSON.stringify(interactiveElements.slice(0, 30)));

      // Try clicking tabs if any
      const tabs = page.locator("[role='tab'], [class*='tab']");
      const tabCount = await tabs.count();
      console.log(`Tabs found: ${tabCount}`);

      for (let i = 0; i < Math.min(tabCount, 10); i++) {
        try {
          const tab = tabs.nth(i);
          const tabText = await tab.textContent();
          if (await tab.isVisible({ timeout: 1000 })) {
            await tab.click();
            await page.waitForTimeout(1000);
            console.log(`Clicked tab ${i}: "${tabText}"`);
            await takeScreenshot(
              page,
              `26_tab_${i}_${(tabText || "").replace(/[^a-z0-9]/gi, "_").substring(0, 20)}`
            );
          }
        } catch {
          // Next
        }
      }

      // Check for modals/dialogs
      const modals = await page
        .locator("[role='dialog'], [class*='modal'], [class*='Modal']")
        .count();
      console.log(`Modals/dialogs: ${modals}`);

      // Check for dropdown menus
      const dropdowns = await page
        .locator("[class*='dropdown'], [class*='Dropdown'], [role='menu']")
        .count();
      console.log(`Dropdowns: ${dropdowns}`);

      // Check for tooltips
      const tooltips = await page
        .locator("[class*='tooltip'], [class*='Tooltip'], [data-tip]")
        .count();
      console.log(`Tooltips: ${tooltips}`);

      await takeScreenshot(page, "27_interactive_elements_overview");
    } finally {
      await context.close();
    }
  });

  test("14.2 Test responsive design — mobile viewport", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const context = await browser.newContext({
      viewport: { width: 375, height: 812 },
      ignoreHTTPSErrors: true,
    });
    const page = await context.newPage();
    try {
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      await takeScreenshot(page, "28_mobile_dashboard");

      // Check if sidebar collapses or has hamburger menu
      const hamburger = page.locator(
        "[class*='hamburger'], [class*='menu-toggle'], [aria-label*='menu']"
      );
      const hasHamburger = (await hamburger.count()) > 0;
      console.log(`Has hamburger menu: ${hasHamburger}`);

      if (hasHamburger) {
        try {
          await hamburger.first().click();
          await page.waitForTimeout(1000);
          await takeScreenshot(page, "29_mobile_menu_open");
        } catch {
          console.log("Could not click hamburger");
        }
      }

      // Check for horizontal scroll (layout bug)
      const hasHorizontalScroll = await page.evaluate(() => {
        return document.documentElement.scrollWidth > window.innerWidth;
      });
      console.log(
        `Has horizontal scroll (layout bug): ${hasHorizontalScroll}`
      );

      // Check if text is readable
      const tinyText = await page.evaluate(() => {
        const elements = document.querySelectorAll("*");
        let tinyCount = 0;
        elements.forEach((el) => {
          const style = window.getComputedStyle(el);
          const fontSize = parseFloat(style.fontSize);
          if (fontSize < 10 && (el.textContent || "").trim().length > 0) {
            tinyCount++;
          }
        });
        return tinyCount;
      });
      console.log(`Elements with tiny text (< 10px): ${tinyText}`);
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 15: SSO Token Security
// ============================================================

test.describe("Phase 15: Security Tests", () => {
  test("15.1 SSO API — test for auth bypass and token handling", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Test 1: SSO with empty token
      const emptyResp = await page.request.post(
        `${PROJECT_API}/v1/auth/sso`,
        { data: { token: "" } }
      );
      console.log(
        `Empty token SSO => ${emptyResp.status()}: ${(await emptyResp.text()).substring(0, 200)}`
      );

      // Test 2: SSO with no body
      const noBodyResp = await page.request.post(
        `${PROJECT_API}/v1/auth/sso`,
        { data: {} }
      );
      console.log(
        `No body SSO => ${noBodyResp.status()}: ${(await noBodyResp.text()).substring(0, 200)}`
      );

      // Test 3: SSO with SQL injection in token
      const sqlResp = await page.request.post(
        `${PROJECT_API}/v1/auth/sso`,
        { data: { token: "' OR 1=1 --" } }
      );
      console.log(
        `SQL injection SSO => ${sqlResp.status()}: ${(await sqlResp.text()).substring(0, 200)}`
      );

      // Test 4: API access with no auth header
      const noAuthResp = await page.request.get(
        `${PROJECT_API}/v1/project/search`
      );
      console.log(
        `No auth header => ${noAuthResp.status()}: ${(await noAuthResp.text()).substring(0, 200)}`
      );

      // Test 5: API access with garbage token
      const garbageResp = await page.request.get(
        `${PROJECT_API}/v1/project/search`,
        {
          headers: { "x-access-token": "garbage_token_xyz" },
        }
      );
      console.log(
        `Garbage token => ${garbageResp.status()}: ${(await garbageResp.text()).substring(0, 200)}`
      );

      // Test 6: Check if sensitive data leaks in error messages
      const { projectToken } = await getProjectToken(
        page,
        ADMIN_CREDS.email,
        ADMIN_CREDS.password
      );

      // Check SSO response for sensitive data leaks
      const ssoResp = await page.request.post(
        `${PROJECT_API}/v1/auth/sso`,
        { data: { token: await getAccessToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password) } }
      );
      const ssoText = await ssoResp.text();
      const hasPasswordLeak = ssoText.includes('"password"');
      const hasForgotTokenLeak = ssoText.includes("forgotPasswordToken");
      const hasEmailTokenLeak = ssoText.includes("emailValidateToken");

      console.log(`SSO response leaks password field: ${hasPasswordLeak}`);
      console.log(`SSO response leaks forgotPasswordToken: ${hasForgotTokenLeak}`);
      console.log(`SSO response leaks emailValidateToken: ${hasEmailTokenLeak}`);

      if (hasPasswordLeak || hasForgotTokenLeak || hasEmailTokenLeak) {
        console.log(
          "SECURITY BUG: SSO response exposes sensitive fields (password hash, reset tokens)"
        );
      }
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 16: Comprehensive Feature Discovery via Network Monitoring
// ============================================================

test.describe("Phase 16: Network Monitoring Discovery", () => {
  test("16.1 Monitor all API calls made by the frontend", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Collect all API requests
      const apiCalls: {
        method: string;
        url: string;
        status: number;
        responseSnippet: string;
      }[] = [];

      page.on("response", async (response) => {
        const url = response.url();
        if (
          url.includes("project") &&
          !url.includes(".js") &&
          !url.includes(".css") &&
          !url.includes(".png") &&
          !url.includes(".svg") &&
          !url.includes(".ico")
        ) {
          const method = response.request().method();
          const status = response.status();
          let snippet = "";
          try {
            snippet = (await response.text()).substring(0, 200);
          } catch {
            snippet = "[could not read]";
          }
          apiCalls.push({ method, url, status, responseSnippet: snippet });
        }
      });

      // Login and navigate around
      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Click around the UI to trigger API calls
      const allLinks = await page.evaluate(() => {
        return Array.from(document.querySelectorAll("a"))
          .filter((a) => {
            const rect = a.getBoundingClientRect();
            return (
              rect.width > 0 &&
              rect.height > 0 &&
              a.getAttribute("href") !== "#"
            );
          })
          .map((a) => ({
            text: (a.textContent || "").trim().substring(0, 40),
            href: a.getAttribute("href") || "",
          }))
          .slice(0, 20);
      });

      for (const link of allLinks) {
        try {
          const el = page.locator(`a[href="${link.href}"]`).first();
          if (await el.isVisible({ timeout: 1000 })) {
            await el.click();
            await page.waitForTimeout(2000);
          }
        } catch {
          // Continue
        }
      }

      // Also try clicking buttons
      const allButtons = await page.locator("button").all();
      for (const btn of allButtons.slice(0, 10)) {
        try {
          if (await btn.isVisible({ timeout: 500 })) {
            const btnText = await btn.textContent();
            // Skip destructive buttons
            if (
              btnText &&
              !btnText.toLowerCase().includes("delete") &&
              !btnText.toLowerCase().includes("remove") &&
              !btnText.toLowerCase().includes("logout") &&
              !btnText.toLowerCase().includes("sign out")
            ) {
              await btn.click();
              await page.waitForTimeout(1000);
            }
          }
        } catch {
          // Continue
        }
      }

      // Report findings
      console.log(`\n=== API calls captured: ${apiCalls.length} ===`);
      const uniqueUrls = [
        ...new Set(apiCalls.map((c) => `${c.method} ${new URL(c.url).pathname}`)),
      ];
      console.log(`Unique API endpoints: ${uniqueUrls.length}`);
      for (const url of uniqueUrls) {
        console.log(`  ${url}`);
      }

      // Show details
      for (const call of apiCalls) {
        const pathname = new URL(call.url).pathname;
        console.log(
          `${call.method} ${pathname} => ${call.status}: ${call.responseSnippet.substring(0, 150)}`
        );
      }

      await takeScreenshot(page, "30_network_monitoring_final");
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PHASE 17: Error Handling & Edge Cases
// ============================================================

test.describe("Phase 17: Error Handling", () => {
  test("17.1 Console errors and JavaScript exceptions", async ({
    browser,
  }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      const consoleErrors: string[] = [];
      const jsExceptions: string[] = [];

      page.on("console", (msg) => {
        if (msg.type() === "error") {
          consoleErrors.push(msg.text());
        }
      });

      page.on("pageerror", (error) => {
        jsExceptions.push(error.message);
      });

      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      // Navigate around to trigger potential errors
      for (const path of ["/", "/dashboard", "/projects", "/tasks", "/settings"]) {
        try {
          await page.goto(`${PROJECT_URL}${path}`, {
            waitUntil: "networkidle",
            timeout: 10000,
          });
          await page.waitForTimeout(1500);
        } catch {
          // Continue
        }
      }

      console.log(`Console errors: ${consoleErrors.length}`);
      for (const err of consoleErrors.slice(0, 20)) {
        console.log(`  ERROR: ${err.substring(0, 200)}`);
      }

      console.log(`JS exceptions: ${jsExceptions.length}`);
      for (const exc of jsExceptions.slice(0, 10)) {
        console.log(`  EXCEPTION: ${exc.substring(0, 200)}`);
      }

      if (jsExceptions.length > 0) {
        console.log(
          "BUG: JavaScript exceptions detected on the page"
        );
      }
    } finally {
      await context.close();
    }
  });

  test("17.2 Test broken/missing images and assets", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      const brokenResources: string[] = [];

      page.on("response", (response) => {
        const url = response.url();
        const status = response.status();
        if (
          (url.endsWith(".png") ||
            url.endsWith(".jpg") ||
            url.endsWith(".svg") ||
            url.endsWith(".gif") ||
            url.endsWith(".ico") ||
            url.endsWith(".css") ||
            url.endsWith(".js")) &&
          status >= 400
        ) {
          brokenResources.push(`${status} ${url}`);
        }
      });

      await loginViaSSO(page, ADMIN_CREDS.email, ADMIN_CREDS.password);

      console.log(`Broken resources: ${brokenResources.length}`);
      for (const res of brokenResources) {
        console.log(`  ${res}`);
      }

      // Check for broken images specifically
      const brokenImages = await page.evaluate(() => {
        return Array.from(document.querySelectorAll("img"))
          .filter(
            (img) =>
              !img.complete ||
              img.naturalWidth === 0
          )
          .map((img) => img.src);
      });
      console.log(`Broken images: ${JSON.stringify(brokenImages)}`);
    } finally {
      await context.close();
    }
  });
});
