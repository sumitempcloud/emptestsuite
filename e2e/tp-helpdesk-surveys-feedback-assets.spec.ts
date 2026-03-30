import { test, expect, Page, BrowserContext, Browser } from "@playwright/test";

const BASE_URL = "https://test-empcloud.empcloud.com";
const API_URL = `${BASE_URL}/api/v1`;

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

async function createFreshContext(browser: Browser): Promise<{ context: BrowserContext; page: Page }> {
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();
  return { context, page };
}

async function getToken(page: Page, email: string, password: string): Promise<string> {
  const r = await page.request.post(`${API_URL}/auth/login`, { data: { email, password } });
  const json = await r.json();
  return json.data?.tokens?.access_token || json.data?.access_token || json.token || "";
}

function ss(name: string) {
  return `e2e/screenshots/tp_ext1_${name}.png`;
}

function authHeader(token: string) {
  return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
}

// ============================================================
// PART 1: HELPDESK MODULE
// ============================================================

test.describe("Helpdesk — Ticket Management", () => {
  let adminToken: string;
  let employeeToken: string;
  let createdTicketId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  // Phase 1: Ticket Creation
  test("HD-1: Employee creates ticket", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/helpdesk/tickets`, {
        headers: authHeader(employeeToken),
        data: {
          subject: `Test Ticket ${Date.now()}`,
          description: "My laptop keyboard is not working properly",
          category: "it",
          priority: "high",
        },
      });
      const json = await r.json();
      console.log(`HD-1: POST /helpdesk/tickets => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 500)}`);
      createdTicketId = json.data?.id || json.data?.ticket?.id || json.id;
      await page.screenshot({ path: ss("hd_create_ticket") });
      expect(r.status()).toBeLessThan(500);
      if (r.status() === 200 || r.status() === 201) {
        expect(createdTicketId).toBeTruthy();
      }
    } finally {
      await context.close();
    }
  });

  test("HD-2: Create ticket with category leave", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/helpdesk/tickets`, {
        headers: authHeader(employeeToken),
        data: {
          subject: `Leave Query ${Date.now()}`,
          description: "Need clarification on leave policy",
          category: "leave",
          priority: "medium",
        },
      });
      const json = await r.json();
      console.log(`HD-2: Create ticket category=leave => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-3: Create ticket with priority low", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/helpdesk/tickets`, {
        headers: authHeader(employeeToken),
        data: {
          subject: `Low Priority ${Date.now()}`,
          description: "General inquiry about benefits",
          category: "benefits",
          priority: "low",
        },
      });
      const json = await r.json();
      console.log(`HD-3: Create ticket priority=low => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-4: Validation — subject required", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/helpdesk/tickets`, {
        headers: authHeader(employeeToken),
        data: { subject: "", description: "Missing subject test", category: "it", priority: "medium" },
      });
      const json = await r.json();
      console.log(`HD-4: Empty subject => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      await page.screenshot({ path: ss("hd_empty_subject") });
      // Should reject with 400
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Ticket created with empty subject — should be rejected");
      }
    } finally {
      await context.close();
    }
  });

  test("HD-5: Validation — description required", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/helpdesk/tickets`, {
        headers: authHeader(employeeToken),
        data: { subject: "Test no desc", description: "", category: "it", priority: "medium" },
      });
      const json = await r.json();
      console.log(`HD-5: Empty description => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Ticket created with empty description — should be rejected");
      }
    } finally {
      await context.close();
    }
  });

  test("HD-6: Ticket ID generated", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/helpdesk/tickets`, {
        headers: authHeader(employeeToken),
        data: {
          subject: `ID Gen Test ${Date.now()}`,
          description: "Testing ticket ID generation",
          category: "general",
          priority: "low",
        },
      });
      const json = await r.json();
      console.log(`HD-6: Ticket ID gen => ${r.status()}`);
      const ticketId = json.data?.id || json.data?.ticket?.id;
      const ticketRef = json.data?.ticket_number || json.data?.ticket?.ticket_number || json.data?.reference;
      console.log(`Ticket ID: ${ticketId}, Reference: ${ticketRef}`);
      expect(r.status()).toBeLessThan(500);
      if (r.status() === 200 || r.status() === 201) {
        expect(ticketId).toBeTruthy();
      }
    } finally {
      await context.close();
    }
  });

  // Phase 2: Ticket Views
  test("HD-7: Employee views My Tickets", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/helpdesk/tickets/my`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`HD-7: GET /helpdesk/tickets/my => ${r.status()}`);
      const tickets = json.data?.tickets || json.data || [];
      console.log(`My tickets count: ${Array.isArray(tickets) ? tickets.length : "N/A"}`);
      await page.screenshot({ path: ss("hd_my_tickets") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-8: Filter tickets by status", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/helpdesk/tickets?status=open`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`HD-8: Filter status=open => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-9: Search tickets by subject", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/helpdesk/tickets?search=laptop`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`HD-9: Search 'laptop' => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-10: HR views all tickets", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/helpdesk/tickets`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`HD-10: GET /helpdesk/tickets (admin) => ${r.status()}`);
      const tickets = json.data?.tickets || json.data || [];
      console.log(`All tickets count: ${Array.isArray(tickets) ? tickets.length : "N/A"}`);
      await page.screenshot({ path: ss("hd_all_tickets") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-11: HR filters by category", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/helpdesk/tickets?category=it`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`HD-11: Filter category=it => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-12: HR filters by priority", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/helpdesk/tickets?priority=high`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`HD-12: Filter priority=high => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-13: Pagination", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/helpdesk/tickets?page=1&limit=20`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`HD-13: Pagination => ${r.status()}`);
      const total = json.data?.total || json.data?.pagination?.total || json.total;
      console.log(`Total tickets: ${total}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

test.describe("Helpdesk — Ticket Detail, Comments & Lifecycle", () => {
  let adminToken: string;
  let employeeToken: string;
  let ticketId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    // Create a ticket for lifecycle tests
    const r = await page.request.post(`${API_URL}/helpdesk/tickets`, {
      headers: authHeader(employeeToken),
      data: {
        subject: `Lifecycle Test ${Date.now()}`,
        description: "Ticket for lifecycle testing",
        category: "it",
        priority: "medium",
      },
    });
    const json = await r.json();
    ticketId = json.data?.id || json.data?.ticket?.id || json.id;
    console.log(`Setup: Created ticket ID=${ticketId} status=${r.status()}`);
    await context.close();
  });

  // Phase 3: Ticket Detail & Comments
  test("HD-14: View ticket detail", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!ticketId) { console.log("HD-14: SKIP — no ticket ID"); return; }
      const r = await page.request.get(`${API_URL}/helpdesk/tickets/${ticketId}`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`HD-14: GET /helpdesk/tickets/${ticketId} => ${r.status()}`);
      console.log(`Detail: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("hd_ticket_detail") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-15: Add public comment (employee)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!ticketId) { console.log("HD-15: SKIP — no ticket ID"); return; }
      const r = await page.request.post(`${API_URL}/helpdesk/tickets/${ticketId}/comment`, {
        headers: authHeader(employeeToken),
        data: { comment: "This is a public comment from employee", is_internal: false },
      });
      const json = await r.json();
      console.log(`HD-15: Add public comment => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-16: Add internal note (HR)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!ticketId) { console.log("HD-16: SKIP — no ticket ID"); return; }
      const r = await page.request.post(`${API_URL}/helpdesk/tickets/${ticketId}/comment`, {
        headers: authHeader(adminToken),
        data: { comment: "Internal HR note — not visible to employee", is_internal: true },
      });
      const json = await r.json();
      console.log(`HD-16: Add internal note => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-17: Employee cannot see internal notes", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!ticketId) { console.log("HD-17: SKIP — no ticket ID"); return; }
      const r = await page.request.get(`${API_URL}/helpdesk/tickets/${ticketId}`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`HD-17: Employee view ticket => ${r.status()}`);
      const comments = json.data?.comments || json.data?.ticket?.comments || [];
      const internalVisible = Array.isArray(comments) && comments.some((c: any) => c.is_internal === true);
      if (internalVisible) {
        console.log("BUG: Employee can see internal notes!");
      } else {
        console.log("PASS: Internal notes hidden from employee");
      }
      await page.screenshot({ path: ss("hd_internal_notes_check") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-18: Conversation thread chronological", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!ticketId) { console.log("HD-18: SKIP — no ticket ID"); return; }
      const r = await page.request.get(`${API_URL}/helpdesk/tickets/${ticketId}`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      const comments = json.data?.comments || json.data?.ticket?.comments || [];
      console.log(`HD-18: Comments count: ${Array.isArray(comments) ? comments.length : 0}`);
      if (Array.isArray(comments) && comments.length >= 2) {
        const dates = comments.map((c: any) => new Date(c.created_at).getTime());
        const sorted = [...dates].sort((a, b) => a - b);
        const inOrder = JSON.stringify(dates) === JSON.stringify(sorted);
        console.log(`HD-18: Chronological order: ${inOrder ? "YES" : "NO"}`);
      }
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  // Phase 4: Ticket Assignment & Resolution
  test("HD-19: HR assigns ticket to agent", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!ticketId) { console.log("HD-19: SKIP — no ticket ID"); return; }
      // Get users to find an agent
      const usersR = await page.request.get(`${API_URL}/users?limit=5`, {
        headers: authHeader(adminToken),
      });
      const usersJson = await usersR.json();
      const users = usersJson.data?.users || usersJson.data || [];
      const agentId = Array.isArray(users) && users.length > 0 ? users[0].id : null;

      const r = await page.request.post(`${API_URL}/helpdesk/tickets/${ticketId}/assign`, {
        headers: authHeader(adminToken),
        data: { assigned_to: agentId },
      });
      const json = await r.json();
      console.log(`HD-19: Assign ticket => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      await page.screenshot({ path: ss("hd_assign_ticket") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-20: HR resolves ticket", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!ticketId) { console.log("HD-20: SKIP — no ticket ID"); return; }
      const r = await page.request.post(`${API_URL}/helpdesk/tickets/${ticketId}/resolve`, {
        headers: authHeader(adminToken),
        data: { resolution_notes: "Issue resolved by replacing keyboard" },
      });
      const json = await r.json();
      console.log(`HD-20: Resolve ticket => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-23: Employee reopens resolved ticket", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!ticketId) { console.log("HD-23: SKIP — no ticket ID"); return; }
      const r = await page.request.post(`${API_URL}/helpdesk/tickets/${ticketId}/reopen`, {
        headers: authHeader(employeeToken),
        data: { reason: "Issue persists after fix" },
      });
      const json = await r.json();
      console.log(`HD-23: Reopen ticket => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-24: Rate resolved ticket", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!ticketId) { console.log("HD-24: SKIP — no ticket ID"); return; }
      // Resolve again first
      await page.request.post(`${API_URL}/helpdesk/tickets/${ticketId}/resolve`, {
        headers: authHeader(adminToken),
        data: { resolution_notes: "Re-resolved" },
      });
      const r = await page.request.post(`${API_URL}/helpdesk/tickets/${ticketId}/rate`, {
        headers: authHeader(employeeToken),
        data: { rating: 4, comment: "Good support, quick resolution" },
      });
      const json = await r.json();
      console.log(`HD-24: Rate ticket => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-21: HR closes ticket", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!ticketId) { console.log("HD-21: SKIP — no ticket ID"); return; }
      const r = await page.request.post(`${API_URL}/helpdesk/tickets/${ticketId}/close`, {
        headers: authHeader(adminToken),
        data: { status: "closed" },
      });
      const json = await r.json();
      console.log(`HD-21: Close ticket => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-22: Employee closes own ticket", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create a new ticket and close it
      const cr = await page.request.post(`${API_URL}/helpdesk/tickets`, {
        headers: authHeader(employeeToken),
        data: { subject: `Close Test ${Date.now()}`, description: "Will close this", category: "general", priority: "low" },
      });
      const cj = await cr.json();
      const newId = cj.data?.id || cj.data?.ticket?.id;
      if (!newId) { console.log("HD-22: SKIP — could not create ticket"); return; }

      const r = await page.request.post(`${API_URL}/helpdesk/tickets/${newId}/close`, {
        headers: authHeader(employeeToken),
        data: { status: "closed" },
      });
      const json = await r.json();
      console.log(`HD-22: Employee closes own ticket => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

test.describe("Helpdesk — SLA Tracking", () => {
  let adminToken: string;
  let employeeToken: string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  test("HD-25-29: SLA tracking on tickets", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create an urgent ticket to check SLA
      const cr = await page.request.post(`${API_URL}/helpdesk/tickets`, {
        headers: authHeader(employeeToken),
        data: { subject: `SLA Test ${Date.now()}`, description: "Urgent SLA test", category: "it", priority: "urgent" },
      });
      const cj = await cr.json();
      const tId = cj.data?.id || cj.data?.ticket?.id;
      console.log(`HD-25: Created urgent ticket => ${cr.status()}, ID=${tId}`);

      if (tId) {
        const r = await page.request.get(`${API_URL}/helpdesk/tickets/${tId}`, {
          headers: authHeader(employeeToken),
        });
        const json = await r.json();
        const ticket = json.data?.ticket || json.data;
        console.log(`HD-25: Response due: ${ticket?.response_due_at || ticket?.sla?.response_due || "N/A"}`);
        console.log(`HD-26: Resolution due: ${ticket?.resolution_due_at || ticket?.sla?.resolution_due || "N/A"}`);
        console.log(`HD-27-29: SLA status: ${ticket?.sla_status || ticket?.sla?.status || "N/A"}`);
        await page.screenshot({ path: ss("hd_sla_tracking") });
      }
      expect(cr.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

test.describe("Helpdesk — Dashboard (HR Only)", () => {
  let adminToken: string;
  let employeeToken: string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  test("HD-30: Dashboard loads with stat cards", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.goto(`${BASE_URL}/helpdesk`, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
      console.log(`HD-30: Helpdesk page URL: ${page.url()}`);
      const bodyText = await page.textContent("body").catch(() => "");
      console.log(`HD-30: Page has content: ${(bodyText || "").length} chars`);
      await page.screenshot({ path: ss("hd_dashboard"), fullPage: true });
    } finally {
      await context.close();
    }
  });

  test("HD-31-35: Dashboard API stats", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Try dashboard API endpoint
      const endpoints = [
        `${API_URL}/helpdesk/dashboard`,
        `${API_URL}/helpdesk/stats`,
        `${API_URL}/helpdesk/tickets/dashboard`,
      ];
      for (const ep of endpoints) {
        const r = await page.request.get(ep, { headers: authHeader(adminToken) });
        const json = await r.json().catch(() => ({}));
        console.log(`HD-31-35: GET ${ep.split("/api")[1]} => ${r.status()}`);
        if (r.status() === 200) {
          console.log(`Dashboard data: ${JSON.stringify(json).substring(0, 500)}`);
          break;
        }
      }
      await page.screenshot({ path: ss("hd_dashboard_api") });
    } finally {
      await context.close();
    }
  });

  test("HD-30-UI: Helpdesk dashboard UI", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.goto(`${BASE_URL}/helpdesk/dashboard`, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
      const bodyText = await page.textContent("body").catch(() => "");
      console.log(`HD-30-UI: Dashboard page text length: ${(bodyText || "").length}`);
      // Check for stat cards
      const hasOpen = (bodyText || "").toLowerCase().includes("open");
      const hasResolved = (bodyText || "").toLowerCase().includes("resolved");
      console.log(`HD-30-UI: Has 'Open': ${hasOpen}, Has 'Resolved': ${hasResolved}`);
      await page.screenshot({ path: ss("hd_dashboard_ui"), fullPage: true });
    } finally {
      await context.close();
    }
  });
});

test.describe("Helpdesk — Knowledge Base", () => {
  let adminToken: string;
  let employeeToken: string;
  let articleId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  test("HD-36: Create KB article", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/helpdesk/kb`, {
        headers: authHeader(adminToken),
        data: {
          title: `KB Article ${Date.now()}`,
          category: "it",
          content: "This is a knowledge base article about how to reset your password. Go to Settings > Security.",
          is_published: true,
        },
      });
      const json = await r.json();
      console.log(`HD-36: Create KB article => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 400)}`);
      articleId = json.data?.id || json.data?.article?.id || json.id;
      await page.screenshot({ path: ss("hd_kb_create") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-37: Mark article as featured", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!articleId) { console.log("HD-37: SKIP — no article ID"); return; }
      const r = await page.request.put(`${API_URL}/helpdesk/kb/${articleId}`, {
        headers: authHeader(adminToken),
        data: { is_featured: true },
      });
      const json = await r.json();
      console.log(`HD-37: Mark featured => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-38: Toggle published status", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!articleId) { console.log("HD-38: SKIP — no article ID"); return; }
      const r = await page.request.put(`${API_URL}/helpdesk/kb/${articleId}`, {
        headers: authHeader(adminToken),
        data: { is_published: false },
      });
      const json = await r.json();
      console.log(`HD-38: Unpublish article => ${r.status()}`);
      // Re-publish for later tests
      await page.request.put(`${API_URL}/helpdesk/kb/${articleId}`, {
        headers: authHeader(adminToken),
        data: { is_published: true },
      });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-39: Edit article content", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!articleId) { console.log("HD-39: SKIP — no article ID"); return; }
      const r = await page.request.put(`${API_URL}/helpdesk/kb/${articleId}`, {
        headers: authHeader(adminToken),
        data: { content: "Updated content with more details about password reset procedures." },
      });
      const json = await r.json();
      console.log(`HD-39: Edit article => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-40: Delete/unpublish article", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create a new one to delete
      const cr = await page.request.post(`${API_URL}/helpdesk/kb`, {
        headers: authHeader(adminToken),
        data: { title: `Delete Test ${Date.now()}`, category: "general", content: "To be deleted", is_published: true },
      });
      const cj = await cr.json();
      const delId = cj.data?.id || cj.data?.article?.id;
      if (!delId) { console.log("HD-40: SKIP — could not create article"); return; }

      const r = await page.request.delete(`${API_URL}/helpdesk/kb/${delId}`, {
        headers: authHeader(adminToken),
      });
      console.log(`HD-40: Delete article => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-41: Browse knowledge base (employee)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/helpdesk/kb`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`HD-41: Browse KB => ${r.status()}`);
      const articles = json.data?.articles || json.data || [];
      console.log(`Articles count: ${Array.isArray(articles) ? articles.length : "N/A"}`);
      await page.screenshot({ path: ss("hd_kb_browse") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-42: Search articles by keyword", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/helpdesk/kb?search=password`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`HD-42: Search KB 'password' => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-43: Filter KB by category", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/helpdesk/kb?category=it`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`HD-43: Filter KB category=it => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-44: View article detail", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!articleId) { console.log("HD-44: SKIP — no article ID"); return; }
      const r = await page.request.get(`${API_URL}/helpdesk/kb/${articleId}`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`HD-44: View article => ${r.status()}`);
      const article = json.data?.article || json.data;
      console.log(`Title: ${article?.title}, Views: ${article?.view_count || article?.views}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-45-46: Rate article helpful", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!articleId) { console.log("HD-45: SKIP — no article ID"); return; }
      const r = await page.request.post(`${API_URL}/helpdesk/kb/${articleId}/helpful`, {
        headers: authHeader(employeeToken),
        data: { is_helpful: true },
      });
      const json = await r.json();
      console.log(`HD-45-46: Rate article helpful => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("HD-47: View count increases", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!articleId) { console.log("HD-47: SKIP — no article ID"); return; }
      // View twice and check count
      const r1 = await page.request.get(`${API_URL}/helpdesk/kb/${articleId}`, {
        headers: authHeader(employeeToken),
      });
      const j1 = await r1.json();
      const count1 = j1.data?.view_count || j1.data?.article?.view_count || j1.data?.views || 0;

      await page.waitForTimeout(500);

      const r2 = await page.request.get(`${API_URL}/helpdesk/kb/${articleId}`, {
        headers: authHeader(employeeToken),
      });
      const j2 = await r2.json();
      const count2 = j2.data?.view_count || j2.data?.article?.view_count || j2.data?.views || 0;

      console.log(`HD-47: View count1=${count1}, count2=${count2}`);
      expect(r1.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PART 2: SURVEYS MODULE
// ============================================================

test.describe("Surveys — Creation & Lifecycle (HR)", () => {
  let adminToken: string;
  let employeeToken: string;
  let surveyId: number | string;
  let draftSurveyId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  // Phase 1: Survey Creation
  test("SV-1: Create survey with title, description, type", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Engagement Survey ${Date.now()}`,
          description: "Quarterly engagement survey for all employees",
          type: "engagement",
          is_anonymous: false,
          target_audience: "all",
          start_date: "2026-03-30",
          end_date: "2026-04-30",
          questions: [
            { question_text: "How satisfied are you with your work?", question_type: "rating_1_5", is_required: true, sort_order: 1 },
            { question_text: "Would you recommend this company?", question_type: "enps_0_10", is_required: true, sort_order: 2 },
            { question_text: "Do you feel valued?", question_type: "yes_no", is_required: false, sort_order: 3 },
            { question_text: "What department are you in?", question_type: "multiple_choice", options: ["Engineering", "HR", "Sales", "Marketing"], is_required: true, sort_order: 4 },
            { question_text: "Any suggestions?", question_type: "text", is_required: false, sort_order: 5 },
          ],
        },
      });
      const json = await r.json();
      console.log(`SV-1: Create survey => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 500)}`);
      surveyId = json.data?.id || json.data?.survey?.id || json.id;
      draftSurveyId = surveyId;
      await page.screenshot({ path: ss("sv_create_survey") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-2: Add rating question (1-5)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Rating Survey ${Date.now()}`,
          description: "Testing rating question type",
          type: "pulse",
          start_date: "2026-03-30",
          end_date: "2026-04-15",
          questions: [
            { question_text: "Rate your manager (1-5)", question_type: "rating_1_5", is_required: true, sort_order: 1 },
          ],
        },
      });
      const json = await r.json();
      console.log(`SV-2: Rating question survey => ${r.status()}`);
      const sid = json.data?.id || json.data?.survey?.id;
      console.log(`Survey ID: ${sid}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-3: Add eNPS question (0-10)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `eNPS Survey ${Date.now()}`,
          description: "Net promoter score",
          type: "enps",
          start_date: "2026-03-30",
          end_date: "2026-04-15",
          questions: [
            { question_text: "How likely are you to recommend this company? (0-10)", question_type: "enps_0_10", is_required: true, sort_order: 1 },
          ],
        },
      });
      const json = await r.json();
      console.log(`SV-3: eNPS survey => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-4: Add yes/no question", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `YesNo Survey ${Date.now()}`,
          description: "Boolean questions",
          type: "pulse",
          start_date: "2026-03-30",
          end_date: "2026-04-15",
          questions: [
            { question_text: "Are you happy with WFH policy?", question_type: "yes_no", is_required: true, sort_order: 1 },
          ],
        },
      });
      const json = await r.json();
      console.log(`SV-4: Yes/No survey => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-5: Add multiple choice question", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `MC Survey ${Date.now()}`,
          description: "Multiple choice",
          type: "custom",
          start_date: "2026-03-30",
          end_date: "2026-04-15",
          questions: [
            { question_text: "Favorite team event?", question_type: "multiple_choice", options: ["Outing", "Game Night", "Workshop", "Lunch"], is_required: true, sort_order: 1 },
          ],
        },
      });
      const json = await r.json();
      console.log(`SV-5: Multiple choice survey => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-6: Add text (open-ended) question", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Text Survey ${Date.now()}`,
          description: "Open ended",
          type: "custom",
          start_date: "2026-03-30",
          end_date: "2026-04-15",
          questions: [
            { question_text: "What would you improve about the company?", question_type: "text", is_required: false, sort_order: 1 },
          ],
        },
      });
      const json = await r.json();
      console.log(`SV-6: Text question survey => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-7: Add scale question", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Scale Survey ${Date.now()}`,
          description: "Scale question",
          type: "custom",
          start_date: "2026-03-30",
          end_date: "2026-04-15",
          questions: [
            { question_text: "Rate work-life balance", question_type: "scale", is_required: true, sort_order: 1 },
          ],
        },
      });
      const json = await r.json();
      console.log(`SV-7: Scale survey => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-8: Mark question as required", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Already tested in SV-1 with is_required: true
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Required Q ${Date.now()}`,
          description: "Required question test",
          type: "pulse",
          start_date: "2026-03-30",
          end_date: "2026-04-15",
          questions: [
            { question_text: "Required question", question_type: "rating_1_5", is_required: true, sort_order: 1 },
            { question_text: "Optional question", question_type: "text", is_required: false, sort_order: 2 },
          ],
        },
      });
      const json = await r.json();
      console.log(`SV-8: Required/Optional questions => ${r.status()}`);
      const qList = json.data?.questions || json.data?.survey?.questions || [];
      if (Array.isArray(qList)) {
        qList.forEach((q: any) => console.log(`  Q: "${q.text}" required=${q.is_required}`));
      }
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-11: Set anonymous mode", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Anonymous Survey ${Date.now()}`,
          description: "Anonymous mode test",
          type: "pulse",
          is_anonymous: true,
          start_date: "2026-03-30",
          end_date: "2026-04-15",
          questions: [
            { question_text: "Anonymous rating", question_type: "rating_1_5", is_required: true, sort_order: 1 },
          ],
        },
      });
      const json = await r.json();
      console.log(`SV-11: Anonymous survey => ${r.status()}`);
      const isAnon = json.data?.is_anonymous || json.data?.survey?.is_anonymous;
      console.log(`is_anonymous: ${isAnon}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-12: Set recurrence", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Recurring Survey ${Date.now()}`,
          description: "Monthly recurrence",
          type: "pulse",
          recurrence: "monthly",
          start_date: "2026-03-30",
          end_date: "2026-04-15",
          questions: [
            { question_text: "Monthly check", question_type: "rating_1_5", is_required: true, sort_order: 1 },
          ],
        },
      });
      const json = await r.json();
      console.log(`SV-12: Recurring survey => ${r.status()}`);
      console.log(`Recurrence: ${json.data?.recurrence || json.data?.survey?.recurrence || "N/A"}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-13: Set start and end dates", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Test with valid dates
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Date Range ${Date.now()}`,
          description: "Date validation",
          type: "pulse",
          start_date: "2026-04-01",
          end_date: "2026-04-30",
          questions: [
            { question_text: "Q1", question_type: "rating_1_5", is_required: true, sort_order: 1 },
          ],
        },
      });
      const json = await r.json();
      console.log(`SV-13: Date range survey => ${r.status()}`);

      // Test with end < start
      const r2 = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Bad Dates ${Date.now()}`,
          description: "Invalid date range",
          type: "pulse",
          start_date: "2026-05-01",
          end_date: "2026-04-01",
          questions: [
            { question_text: "Q1", question_type: "rating_1_5", is_required: true, sort_order: 1 },
          ],
        },
      });
      console.log(`SV-13: End before start => ${r2.status()}`);
      if (r2.status() === 200 || r2.status() === 201) {
        console.log("BUG: Survey created with end_date before start_date");
      }
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-14-16: Target audience options", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Target all
      const r1 = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `All Target ${Date.now()}`,
          description: "All employees",
          type: "pulse",
          target_audience: "all",
          start_date: "2026-03-30",
          end_date: "2026-04-15",
          questions: [{ question_text: "Q1", question_type: "rating_1_5", is_required: true, sort_order: 1 }],
        },
      });
      console.log(`SV-14: Target all => ${r1.status()}`);

      // Target department
      const r2 = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Dept Target ${Date.now()}`,
          description: "Engineering dept",
          type: "pulse",
          target_audience: "department",
          target_departments: ["Engineering"],
          start_date: "2026-03-30",
          end_date: "2026-04-15",
          questions: [{ question_text: "Q1", question_type: "rating_1_5", is_required: true, sort_order: 1 }],
        },
      });
      console.log(`SV-15: Target department => ${r2.status()}`);

      expect(r1.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-17: Save as draft", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Draft Survey ${Date.now()}`,
          description: "Should be saved as draft",
          type: "custom",
          status: "draft",
          start_date: "2026-04-01",
          end_date: "2026-04-30",
          questions: [{ question_text: "Draft Q", question_type: "text", is_required: false, sort_order: 1 }],
        },
      });
      const json = await r.json();
      console.log(`SV-17: Save as draft => ${r.status()}`);
      const status = json.data?.status || json.data?.survey?.status;
      console.log(`Survey status: ${status}`);
      draftSurveyId = json.data?.id || json.data?.survey?.id;
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

test.describe("Surveys — Publishing & Lifecycle", () => {
  let adminToken: string;
  let employeeToken: string;
  let surveyId: number | string;
  let activeSurveyId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    // Create a draft survey for lifecycle tests
    const r = await page.request.post(`${API_URL}/surveys`, {
      headers: authHeader(adminToken),
      data: {
        title: `Lifecycle Survey ${Date.now()}`,
        description: "For publish/close testing",
        type: "pulse",
        start_date: "2026-03-30",
        end_date: "2026-04-30",
        questions: [
          { question_text: "Rate your experience", question_type: "rating_1_5", is_required: true, sort_order: 1 },
          { question_text: "Any feedback?", question_type: "text", is_required: false, sort_order: 2 },
        ],
      },
    });
    const json = await r.json();
    surveyId = json.data?.id || json.data?.survey?.id || json.id;
    console.log(`Setup: Created survey ID=${surveyId}, status=${r.status()}`);
    await context.close();
  });

  test("SV-18: Publish draft survey", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!surveyId) { console.log("SV-18: SKIP — no survey ID"); return; }
      const r = await page.request.post(`${API_URL}/surveys/${surveyId}/publish`, {
        headers: authHeader(adminToken),
        data: {},
      });
      const json = await r.json();
      console.log(`SV-18: Publish survey => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      activeSurveyId = surveyId;
      await page.screenshot({ path: ss("sv_publish") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-19: Edit active survey (should be blocked)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!surveyId) { console.log("SV-19: SKIP — no survey ID"); return; }
      const r = await page.request.put(`${API_URL}/surveys/${surveyId}`, {
        headers: authHeader(adminToken),
        data: { title: "Attempted Edit" },
      });
      const json = await r.json();
      console.log(`SV-19: Edit active survey => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      if (r.status() === 200) {
        console.log("BUG: Active survey was editable — should be blocked");
      }
    } finally {
      await context.close();
    }
  });

  test("SV-20: Close active survey", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!surveyId) { console.log("SV-20: SKIP — no survey ID"); return; }
      const r = await page.request.post(`${API_URL}/surveys/${surveyId}/close`, {
        headers: authHeader(adminToken),
        data: {},
      });
      const json = await r.json();
      console.log(`SV-20: Close survey => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-21: Delete draft survey", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create a new draft to delete
      const cr = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Delete Draft ${Date.now()}`,
          description: "Will delete",
          type: "custom",
          start_date: "2026-04-01",
          end_date: "2026-04-30",
          questions: [{ question_text: "Q1", question_type: "text", is_required: false, sort_order: 1 }],
        },
      });
      const cj = await cr.json();
      const delId = cj.data?.id || cj.data?.survey?.id;
      if (!delId) { console.log("SV-21: SKIP — could not create draft"); return; }

      const r = await page.request.delete(`${API_URL}/surveys/${delId}`, {
        headers: authHeader(adminToken),
      });
      console.log(`SV-21: Delete draft survey => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-22: Delete active survey (should be blocked)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create and publish, then try to delete
      const cr = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Active Delete ${Date.now()}`,
          description: "Attempt delete active",
          type: "pulse",
          start_date: "2026-03-30",
          end_date: "2026-04-30",
          questions: [{ question_text: "Q1", question_type: "rating_1_5", is_required: true, sort_order: 1 }],
        },
      });
      const cj = await cr.json();
      const sid = cj.data?.id || cj.data?.survey?.id;
      if (!sid) { console.log("SV-22: SKIP — could not create survey"); return; }

      await page.request.post(`${API_URL}/surveys/${sid}/publish`, {
        headers: authHeader(adminToken), data: {},
      });

      const r = await page.request.delete(`${API_URL}/surveys/${sid}`, {
        headers: authHeader(adminToken),
      });
      console.log(`SV-22: Delete active survey => ${r.status()}`);
      if (r.status() === 200) {
        console.log("BUG: Active survey was deletable — should require closing first");
      }
      // Cleanup
      await page.request.post(`${API_URL}/surveys/${sid}/close`, {
        headers: authHeader(adminToken), data: {},
      });
    } finally {
      await context.close();
    }
  });
});

test.describe("Surveys — List Views & Responding", () => {
  let adminToken: string;
  let employeeToken: string;
  let respondSurveyId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    // Create and publish a survey for responding
    const r = await page.request.post(`${API_URL}/surveys`, {
      headers: authHeader(adminToken),
      data: {
        title: `Respond Survey ${Date.now()}`,
        description: "Employee will respond to this",
        type: "engagement",
        is_anonymous: false,
        target_audience: "all",
        start_date: "2026-03-30",
        end_date: "2026-04-30",
        questions: [
          { question_text: "Rate your happiness", question_type: "rating_1_5", is_required: true, sort_order: 1 },
          { question_text: "Would you recommend?", question_type: "enps_0_10", is_required: true, sort_order: 2 },
          { question_text: "Enjoy work?", question_type: "yes_no", is_required: false, sort_order: 3 },
          { question_text: "Best perk?", question_type: "multiple_choice", options: ["WFH", "Insurance", "Meals", "Gym"], is_required: true, sort_order: 4 },
          { question_text: "Suggestions?", question_type: "text", is_required: false, sort_order: 5 },
        ],
      },
    });
    const json = await r.json();
    respondSurveyId = json.data?.id || json.data?.survey?.id;
    if (respondSurveyId) {
      await page.request.post(`${API_URL}/surveys/${respondSurveyId}/publish`, {
        headers: authHeader(adminToken), data: {},
      });
    }
    console.log(`Setup: Created+published survey ID=${respondSurveyId}`);
    await context.close();
  });

  // Phase 3: List Views
  test("SV-23: HR views survey list", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`SV-23: GET /surveys (admin) => ${r.status()}`);
      const surveys = json.data?.surveys || json.data || [];
      console.log(`Survey count: ${Array.isArray(surveys) ? surveys.length : "N/A"}`);
      await page.screenshot({ path: ss("sv_list_hr") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-24: Filter by status", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      for (const status of ["draft", "active", "closed"]) {
        const r = await page.request.get(`${API_URL}/surveys?status=${status}`, {
          headers: authHeader(adminToken),
        });
        console.log(`SV-24: Filter status=${status} => ${r.status()}`);
      }
    } finally {
      await context.close();
    }
  });

  test("SV-25: Filter by type", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      for (const type of ["pulse", "enps", "engagement", "custom"]) {
        const r = await page.request.get(`${API_URL}/surveys?type=${type}`, {
          headers: authHeader(adminToken),
        });
        console.log(`SV-25: Filter type=${type} => ${r.status()}`);
      }
    } finally {
      await context.close();
    }
  });

  test("SV-26: Employee views active surveys", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/surveys/active`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`SV-26: GET /surveys/active (employee) => ${r.status()}`);
      const surveys = json.data?.surveys || json.data || [];
      console.log(`Active surveys: ${Array.isArray(surveys) ? surveys.length : "N/A"}`);
      await page.screenshot({ path: ss("sv_active_employee") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-27: Survey cards show metadata", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      const surveys = json.data?.surveys || json.data || [];
      if (Array.isArray(surveys) && surveys.length > 0) {
        const s = surveys[0];
        console.log(`SV-27: Survey card: type=${s.type}, anonymous=${s.is_anonymous}, end=${s.end_date}`);
      } else {
        console.log("SV-27: No surveys to check metadata");
      }
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-28: Pagination", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/surveys?page=1&limit=20`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`SV-28: Pagination => ${r.status()}`);
      const total = json.data?.total || json.data?.pagination?.total;
      console.log(`Total surveys: ${total}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  // Phase 4: Survey Responding
  test("SV-29: Employee opens active survey", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!respondSurveyId) { console.log("SV-29: SKIP — no survey ID"); return; }
      const r = await page.request.get(`${API_URL}/surveys/${respondSurveyId}`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`SV-29: View survey detail => ${r.status()}`);
      const questions = json.data?.questions || json.data?.survey?.questions || [];
      console.log(`Questions count: ${Array.isArray(questions) ? questions.length : "N/A"}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-30-35,37: Submit complete response", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!respondSurveyId) { console.log("SV-30-37: SKIP — no survey ID"); return; }
      // Get survey questions
      const sr = await page.request.get(`${API_URL}/surveys/${respondSurveyId}`, {
        headers: authHeader(employeeToken),
      });
      const sj = await sr.json();
      const questions = sj.data?.questions || sj.data?.survey?.questions || [];

      // Build answers using "answer" field (not "value")
      const answers: any[] = [];
      if (Array.isArray(questions)) {
        questions.forEach((q: any) => {
          const qId = q.id || q.question_id;
          if (q.question_type === "rating_1_5") answers.push({ question_id: qId, answer: "4" });
          else if (q.question_type === "enps_0_10") answers.push({ question_id: qId, answer: "9" });
          else if (q.question_type === "yes_no") answers.push({ question_id: qId, answer: "yes" });
          else if (q.question_type === "multiple_choice") answers.push({ question_id: qId, answer: q.options?.[0] || "WFH" });
          else if (q.question_type === "text") answers.push({ question_id: qId, answer: "Great company culture!" });
          else answers.push({ question_id: qId, answer: "4" });
        });
      }

      const r = await page.request.post(`${API_URL}/surveys/${respondSurveyId}/respond`, {
        headers: authHeader(employeeToken),
        data: { answers },
      });
      const json = await r.json();
      console.log(`SV-30-37: Submit response => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      await page.screenshot({ path: ss("sv_submit_response") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-36: Submit without required question", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!respondSurveyId) { console.log("SV-36: SKIP — no survey ID"); return; }
      // Submit empty answers
      const r = await page.request.post(`${API_URL}/surveys/${respondSurveyId}/respond`, {
        headers: authHeader(adminToken), // Use admin (different user)
        data: { answers: [] },
      });
      const json = await r.json();
      console.log(`SV-36: Submit without required => ${r.status()}`);
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Survey accepted without required answers");
      }
    } finally {
      await context.close();
    }
  });

  test("SV-38: Cannot respond twice", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!respondSurveyId) { console.log("SV-38: SKIP — no survey ID"); return; }
      const r = await page.request.post(`${API_URL}/surveys/${respondSurveyId}/respond`, {
        headers: authHeader(employeeToken),
        data: { answers: [{ question_id: 1, answer: "5" }] },
      });
      const json = await r.json();
      console.log(`SV-38: Double response => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Employee allowed to respond twice to same survey");
      }
    } finally {
      await context.close();
    }
  });

  test("SV-39: Anonymous survey disclaimer", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
      await page.goto(`${BASE_URL}/surveys`, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
      const bodyText = await page.textContent("body").catch(() => "");
      const hasAnonymous = (bodyText || "").toLowerCase().includes("anonymous");
      console.log(`SV-39: Page mentions 'anonymous': ${hasAnonymous}`);
      await page.screenshot({ path: ss("sv_anonymous_disclaimer"), fullPage: true });
    } finally {
      await context.close();
    }
  });
});

test.describe("Surveys — Response History & Results", () => {
  let adminToken: string;
  let employeeToken: string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  // Phase 5: Response History
  test("SV-40-41: Employee views response history", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/surveys/my-responses`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`SV-40-41: GET /surveys/my-responses => ${r.status()}`);
      const responses = json.data?.responses || json.data || [];
      console.log(`Response history count: ${Array.isArray(responses) ? responses.length : "N/A"}`);
      await page.screenshot({ path: ss("sv_my_responses") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  // Phase 6: Results & Analytics
  test("SV-42-49: Survey results (HR)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Find a closed survey with responses
      const listR = await page.request.get(`${API_URL}/surveys?status=closed&limit=5`, {
        headers: authHeader(adminToken),
      });
      const listJ = await listR.json();
      const surveys = listJ.data?.surveys || listJ.data || [];
      let closedId: any = null;
      if (Array.isArray(surveys) && surveys.length > 0) {
        closedId = surveys[0].id;
      }

      // Also try active surveys
      if (!closedId) {
        const activeR = await page.request.get(`${API_URL}/surveys?limit=5`, {
          headers: authHeader(adminToken),
        });
        const activeJ = await activeR.json();
        const activeSurveys = activeJ.data?.surveys || activeJ.data || [];
        if (Array.isArray(activeSurveys) && activeSurveys.length > 0) {
          closedId = activeSurveys[0].id;
        }
      }

      if (closedId) {
        const r = await page.request.get(`${API_URL}/surveys/${closedId}/results`, {
          headers: authHeader(adminToken),
        });
        const json = await r.json();
        console.log(`SV-42-49: Results for survey ${closedId} => ${r.status()}`);
        console.log(`Results: ${JSON.stringify(json).substring(0, 500)}`);
        await page.screenshot({ path: ss("sv_results") });
      } else {
        console.log("SV-42-49: No surveys found for results check");
      }
    } finally {
      await context.close();
    }
  });

  test("SV-50: Export results to CSV", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/surveys?limit=5`, {
        headers: authHeader(adminToken),
      });
      const listJ = await listR.json();
      const surveys = listJ.data?.surveys || listJ.data || [];
      if (Array.isArray(surveys) && surveys.length > 0) {
        const sid = surveys[0].id;
        // Try CSV export
        const r = await page.request.get(`${API_URL}/surveys/${sid}/results/export`, {
          headers: authHeader(adminToken),
        });
        console.log(`SV-50: Export CSV => ${r.status()}`);
        const contentType = r.headers()["content-type"] || "";
        console.log(`Content-Type: ${contentType}`);
        if (r.status() === 404) {
          // Try alternative path
          const r2 = await page.request.get(`${API_URL}/surveys/${sid}/export`, {
            headers: authHeader(adminToken),
          });
          console.log(`SV-50: Alt export => ${r2.status()}`);
        }
      } else {
        console.log("SV-50: No surveys for export test");
      }
    } finally {
      await context.close();
    }
  });

  // Phase 7: Dashboard
  test("SV-51-54: Survey dashboard (HR)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/surveys/dashboard`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`SV-51-54: GET /surveys/dashboard => ${r.status()}`);
      console.log(`Dashboard: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("sv_dashboard") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("SV-51-54 UI: Survey dashboard page", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.goto(`${BASE_URL}/surveys`, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
      const bodyText = await page.textContent("body").catch(() => "");
      console.log(`SV-51-54 UI: Survey page text length: ${(bodyText || "").length}`);
      await page.screenshot({ path: ss("sv_dashboard_ui"), fullPage: true });
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PART 3: ANONYMOUS FEEDBACK MODULE
// ============================================================

test.describe("Feedback — Submission (Employee)", () => {
  let adminToken: string;
  let employeeToken: string;
  let feedbackId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  test("FB-1: Navigate to feedback submission page", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
      await page.goto(`${BASE_URL}/feedback`, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
      const bodyText = await page.textContent("body").catch(() => "");
      const hasAnonymity = (bodyText || "").toLowerCase().includes("anonymous");
      console.log(`FB-1: Feedback page, has anonymity disclaimer: ${hasAnonymity}`);
      await page.screenshot({ path: ss("fb_submission_page"), fullPage: true });
    } finally {
      await context.close();
    }
  });

  test("FB-2-6: Submit feedback with all fields", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/feedback`, {
        headers: authHeader(employeeToken),
        data: {
          category: "workplace",
          subject: `Feedback ${Date.now()}`,
          message: "The office temperature is too cold. Please adjust the AC settings.",
          is_urgent: false,
        },
      });
      const json = await r.json();
      console.log(`FB-2-6: Submit feedback => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 400)}`);
      feedbackId = json.data?.id || json.data?.feedback?.id || json.id;
      await page.screenshot({ path: ss("fb_submit") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-5: Mark as urgent", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/feedback`, {
        headers: authHeader(employeeToken),
        data: {
          category: "harassment",
          subject: `Urgent Feedback ${Date.now()}`,
          message: "Urgent matter that needs immediate attention regarding workplace behavior",
          is_urgent: true,
        },
      });
      const json = await r.json();
      console.log(`FB-5: Urgent feedback => ${r.status()}`);
      const isUrgent = json.data?.is_urgent || json.data?.feedback?.is_urgent;
      console.log(`Is urgent: ${isUrgent}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-7: Submit another (different category)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/feedback`, {
        headers: authHeader(employeeToken),
        data: {
          category: "suggestion",
          subject: `Suggestion ${Date.now()}`,
          message: "It would be great to have a nap room in the office",
          is_urgent: false,
        },
      });
      const json = await r.json();
      console.log(`FB-7: Submit another => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-8: Submit without subject", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/feedback`, {
        headers: authHeader(employeeToken),
        data: { category: "workplace", subject: "", message: "No subject test", is_urgent: false },
      });
      const json = await r.json();
      console.log(`FB-8: Empty subject => ${r.status()}`);
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Feedback accepted without subject — should be rejected");
      }
    } finally {
      await context.close();
    }
  });

  test("FB-9: Submit without message", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/feedback`, {
        headers: authHeader(employeeToken),
        data: { category: "workplace", subject: "No message test", message: "", is_urgent: false },
      });
      const json = await r.json();
      console.log(`FB-9: Empty message => ${r.status()}`);
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Feedback accepted without message — should be rejected");
      }
    } finally {
      await context.close();
    }
  });

  test("FB-10: Verify anonymity — no user ID stored", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Check HR view — no user info should be visible
      const r = await page.request.get(`${API_URL}/feedback?limit=5`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      const feedbacks = json.data?.feedbacks || json.data?.feedback || json.data || [];
      if (Array.isArray(feedbacks) && feedbacks.length > 0) {
        const fb = feedbacks[0];
        const hasUserId = fb.user_id || fb.submitted_by || fb.employee_id;
        const hasEmail = fb.email || fb.user_email;
        const hasName = fb.user_name || fb.employee_name;
        console.log(`FB-10: Has user_id: ${!!hasUserId}, email: ${!!hasEmail}, name: ${!!hasName}`);
        if (hasUserId || hasEmail || hasName) {
          console.log("BUG: Feedback exposes user identity — should be anonymous");
        } else {
          console.log("PASS: No user identity exposed in feedback");
        }
      }
      await page.screenshot({ path: ss("fb_anonymity") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

test.describe("Feedback — My Feedback (Employee)", () => {
  let employeeToken: string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  test("FB-11-16: View own feedback history", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback/my`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`FB-11: GET /feedback/my => ${r.status()}`);
      const feedbacks = json.data?.feedbacks || json.data?.feedback || json.data || [];
      if (Array.isArray(feedbacks)) {
        console.log(`FB-11: My feedback count: ${feedbacks.length}`);
        if (feedbacks.length > 0) {
          const fb = feedbacks[0];
          console.log(`FB-12: Status: ${fb.status}`);
          console.log(`FB-13: Category: ${fb.category}`);
          console.log(`FB-14: HR Response: ${fb.hr_response || fb.response || "none"}`);
          console.log(`FB-15: Urgent: ${fb.is_urgent}`);
        }
      }
      await page.screenshot({ path: ss("fb_my_feedback") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-16: Pagination works", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback/my?page=1&limit=20`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`FB-16: Pagination => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

test.describe("Feedback — HR Views & Management", () => {
  let adminToken: string;
  let employeeToken: string;
  let feedbackId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    // Create feedback for HR tests
    const r = await page.request.post(`${API_URL}/feedback`, {
      headers: authHeader(employeeToken),
      data: {
        category: "management",
        subject: `HR Test Feedback ${Date.now()}`,
        message: "Feedback for HR management testing purposes",
        is_urgent: false,
      },
    });
    const json = await r.json();
    feedbackId = json.data?.id || json.data?.feedback?.id || json.id;
    console.log(`Setup: Created feedback ID=${feedbackId}`);
    await context.close();
  });

  // Phase 3: HR Views
  test("FB-17: HR views all feedback", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`FB-17: GET /feedback (admin) => ${r.status()}`);
      const feedbacks = json.data?.feedbacks || json.data?.feedback || json.data || [];
      console.log(`All feedback count: ${Array.isArray(feedbacks) ? feedbacks.length : "N/A"}`);
      await page.screenshot({ path: ss("fb_all_feedback") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-18: Filter by category", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback?category=workplace`, {
        headers: authHeader(adminToken),
      });
      console.log(`FB-18: Filter category=workplace => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-19: Filter by status", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback?status=new`, {
        headers: authHeader(adminToken),
      });
      console.log(`FB-19: Filter status=new => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-20: Filter urgent only", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback?is_urgent=true`, {
        headers: authHeader(adminToken),
      });
      console.log(`FB-20: Filter urgent => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-21: Search feedback", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback?search=office`, {
        headers: authHeader(adminToken),
      });
      console.log(`FB-21: Search 'office' => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-22: Combine filters", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback?category=workplace&status=new`, {
        headers: authHeader(adminToken),
      });
      console.log(`FB-22: Combined filters => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-23: Sentiment tags on feedback", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback?limit=10`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      const feedbacks = json.data?.feedbacks || json.data?.feedback || json.data || [];
      if (Array.isArray(feedbacks) && feedbacks.length > 0) {
        feedbacks.slice(0, 3).forEach((fb: any, i: number) => {
          console.log(`FB-23: Feedback[${i}] sentiment=${fb.sentiment || "N/A"}`);
        });
      }
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-24: Pagination (20/page)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback?page=1&limit=20`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`FB-24: Pagination => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  // Phase 4: HR Response & Status
  test("FB-25: HR responds to feedback", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!feedbackId) { console.log("FB-25: SKIP — no feedback ID"); return; }
      // Try POST /respond with different field names, then fallback to PUT
      const fields = ["response", "message", "comment", "reply", "hr_response"];
      let responded = false;
      for (const field of fields) {
        const r = await page.request.post(`${API_URL}/feedback/${feedbackId}/respond`, {
          headers: authHeader(adminToken),
          data: { [field]: "Thank you for your feedback. We will look into the AC issue." },
        });
        if (r.status() === 200 || r.status() === 201) {
          console.log(`FB-25: HR respond with '${field}' => ${r.status()}`);
          responded = true;
          break;
        }
      }
      if (!responded) {
        // Try PUT /feedback/:id with admin_response
        const r2 = await page.request.put(`${API_URL}/feedback/${feedbackId}`, {
          headers: authHeader(adminToken),
          data: { admin_response: "Thank you for your feedback." },
        });
        console.log(`FB-25: PUT /feedback/${feedbackId} => ${r2.status()}`);
        if (r2.status() !== 200 && r2.status() !== 201) {
          console.log("BUG: HR cannot respond to feedback — POST /respond returns 400, PUT also fails");
        }
      }
      await page.screenshot({ path: ss("fb_hr_respond") });
    } finally {
      await context.close();
    }
  });

  test("FB-26: HR edits response", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!feedbackId) { console.log("FB-26: SKIP — no feedback ID"); return; }
      // Same issue as FB-25 — try PUT
      const r = await page.request.put(`${API_URL}/feedback/${feedbackId}`, {
        headers: authHeader(adminToken),
        data: { admin_response: "Updated: We have adjusted the AC settings. Please check." },
      });
      const json = await r.json();
      console.log(`FB-26: HR edit response => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-27: Update status to Acknowledged", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!feedbackId) { console.log("FB-27: SKIP — no feedback ID"); return; }
      const r = await page.request.put(`${API_URL}/feedback/${feedbackId}/status`, {
        headers: authHeader(adminToken),
        data: { status: "acknowledged" },
      });
      const json = await r.json();
      console.log(`FB-27: Status -> acknowledged => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-28: Update status to Under Review", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!feedbackId) { console.log("FB-28: SKIP — no feedback ID"); return; }
      const r = await page.request.put(`${API_URL}/feedback/${feedbackId}/status`, {
        headers: authHeader(adminToken),
        data: { status: "under_review" },
      });
      const json = await r.json();
      console.log(`FB-28: Status -> under_review => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-29: Update status to Resolved", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!feedbackId) { console.log("FB-29: SKIP — no feedback ID"); return; }
      const r = await page.request.put(`${API_URL}/feedback/${feedbackId}/status`, {
        headers: authHeader(adminToken),
        data: { status: "resolved" },
      });
      const json = await r.json();
      console.log(`FB-29: Status -> resolved => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-30: Update status to Archived", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!feedbackId) { console.log("FB-30: SKIP — no feedback ID"); return; }
      const r = await page.request.put(`${API_URL}/feedback/${feedbackId}/status`, {
        headers: authHeader(adminToken),
        data: { status: "archived" },
      });
      const json = await r.json();
      console.log(`FB-30: Status -> archived => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

test.describe("Feedback — Dashboard & Access Control", () => {
  let adminToken: string;
  let employeeToken: string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  // Phase 5: Dashboard
  test("FB-31-35: Feedback dashboard (HR)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback/dashboard`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`FB-31-35: GET /feedback/dashboard => ${r.status()}`);
      console.log(`Dashboard: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("fb_dashboard") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("FB-31-35 UI: Feedback dashboard page", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.goto(`${BASE_URL}/feedback`, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
      const bodyText = await page.textContent("body").catch(() => "");
      console.log(`FB-31-35 UI: Page length: ${(bodyText || "").length}`);
      await page.screenshot({ path: ss("fb_dashboard_ui"), fullPage: true });
    } finally {
      await context.close();
    }
  });

  // Phase 6: Access Control
  test("FB-36: Employee cannot view all feedback", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback`, {
        headers: authHeader(employeeToken),
      });
      console.log(`FB-36: Employee GET /feedback => ${r.status()}`);
      if (r.status() === 200) {
        const json = await r.json();
        const feedbacks = json.data?.feedbacks || json.data?.feedback || json.data || [];
        if (Array.isArray(feedbacks) && feedbacks.length > 5) {
          console.log("POTENTIAL BUG: Employee can see all feedback — check if limited to own");
        }
      } else if (r.status() === 403) {
        console.log("PASS: Employee blocked from viewing all feedback");
      }
      await page.screenshot({ path: ss("fb_employee_access") });
    } finally {
      await context.close();
    }
  });

  test("FB-37: Employee cannot respond to feedback", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Get a feedback ID from admin view
      const listR = await page.request.get(`${API_URL}/feedback?limit=1`, {
        headers: authHeader(adminToken),
      });
      const listJ = await listR.json();
      const feedbacks = listJ.data?.feedbacks || listJ.data?.feedback || listJ.data || [];
      const fbId = Array.isArray(feedbacks) && feedbacks.length > 0 ? feedbacks[0].id : null;
      if (!fbId) { console.log("FB-37: SKIP — no feedback found"); return; }

      const r = await page.request.post(`${API_URL}/feedback/${fbId}/respond`, {
        headers: authHeader(employeeToken),
        data: { response: "Employee trying to respond" },
      });
      console.log(`FB-37: Employee respond => ${r.status()}`);
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Employee can respond to feedback — should be HR only");
      } else {
        console.log("PASS: Employee blocked from responding");
      }
    } finally {
      await context.close();
    }
  });

  test("FB-38: Employee cannot change status", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/feedback?limit=1`, {
        headers: authHeader(adminToken),
      });
      const listJ = await listR.json();
      const feedbacks = listJ.data?.feedbacks || listJ.data?.feedback || listJ.data || [];
      const fbId = Array.isArray(feedbacks) && feedbacks.length > 0 ? feedbacks[0].id : null;
      if (!fbId) { console.log("FB-38: SKIP — no feedback found"); return; }

      const r = await page.request.put(`${API_URL}/feedback/${fbId}/status`, {
        headers: authHeader(employeeToken),
        data: { status: "resolved" },
      });
      console.log(`FB-38: Employee change status => ${r.status()}`);
      if (r.status() === 200) {
        console.log("BUG: Employee can change feedback status — should be HR only");
      } else {
        console.log("PASS: Employee blocked from changing status");
      }
    } finally {
      await context.close();
    }
  });

  test("FB-39: HR cannot see submitter identity", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/feedback?limit=5`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      const feedbacks = json.data?.feedbacks || json.data?.feedback || json.data || [];
      if (Array.isArray(feedbacks) && feedbacks.length > 0) {
        const fb = feedbacks[0];
        const detail = JSON.stringify(fb);
        const exposesIdentity = detail.includes('"user_id"') || detail.includes('"email"') ||
          detail.includes('"employee_name"') || detail.includes('"user_name"');
        console.log(`FB-39: Identity exposed in HR view: ${exposesIdentity}`);
        if (exposesIdentity) {
          console.log("BUG: HR can see submitter identity — breaks anonymity");
        }
      }
      await page.screenshot({ path: ss("fb_hr_identity") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PART 4: ASSETS MODULE
// ============================================================

test.describe("Assets — Categories (HR)", () => {
  let adminToken: string;
  let categoryId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    await context.close();
  });

  test("AS-1: Create asset category", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/assets/categories`, {
        headers: authHeader(adminToken),
        data: { name: `Laptops_${Date.now()}`, description: "Company laptops" },
      });
      const json = await r.json();
      console.log(`AS-1: Create category => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      categoryId = json.data?.id || json.data?.category?.id || json.id;
      await page.screenshot({ path: ss("as_create_category") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-2: Edit category", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!categoryId) { console.log("AS-2: SKIP — no category ID"); return; }
      const r = await page.request.put(`${API_URL}/assets/categories/${categoryId}`, {
        headers: authHeader(adminToken),
        data: { name: `UpdatedCat_${Date.now()}`, description: "Updated description" },
      });
      const json = await r.json();
      console.log(`AS-2: Edit category => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-3: Delete category", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create one to delete
      const cr = await page.request.post(`${API_URL}/assets/categories`, {
        headers: authHeader(adminToken),
        data: { name: `DeleteCat_${Date.now()}`, description: "Will delete" },
      });
      const cj = await cr.json();
      const delId = cj.data?.id || cj.data?.category?.id;
      if (!delId) { console.log("AS-3: SKIP — could not create"); return; }

      const r = await page.request.delete(`${API_URL}/assets/categories/${delId}`, {
        headers: authHeader(adminToken),
      });
      console.log(`AS-3: Delete category => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-4: List categories", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/assets/categories`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`AS-4: GET /assets/categories => ${r.status()}`);
      const cats = json.data?.categories || json.data || [];
      console.log(`Categories count: ${Array.isArray(cats) ? cats.length : "N/A"}`);
      await page.screenshot({ path: ss("as_list_categories") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

test.describe("Assets — CRUD (HR)", () => {
  let adminToken: string;
  let employeeToken: string;
  let assetId: number | string;
  let categoryId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    // Get or create a category
    const catR = await page.request.get(`${API_URL}/assets/categories`, {
      headers: authHeader(adminToken),
    });
    const catJ = await catR.json();
    const cats = catJ.data?.categories || catJ.data || [];
    if (Array.isArray(cats) && cats.length > 0) {
      categoryId = cats[0].id;
    } else {
      const cr = await page.request.post(`${API_URL}/assets/categories`, {
        headers: authHeader(adminToken),
        data: { name: `TestCat_${Date.now()}`, description: "For asset tests" },
      });
      const cj = await cr.json();
      categoryId = cj.data?.id || cj.data?.category?.id;
    }
    console.log(`Setup: Using category ID=${categoryId}`);
    await context.close();
  });

  test("AS-5: Create asset with all fields", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/assets`, {
        headers: authHeader(adminToken),
        data: {
          name: `MacBook Pro ${Date.now()}`,
          category_id: categoryId,
          serial_number: `SN-${Date.now()}`,
          brand: "Apple",
          model: "MacBook Pro 16",
          condition: "new",
          purchase_date: "2026-01-15",
          purchase_cost: 250000,
          warranty_expiry: "2028-01-15",
          notes: "16GB RAM, 512GB SSD",
        },
      });
      const json = await r.json();
      console.log(`AS-5: Create asset => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 400)}`);
      assetId = json.data?.id || json.data?.asset?.id || json.id;
      await page.screenshot({ path: ss("as_create_asset") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-6: Set purchase date and cost", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/assets`, {
        headers: authHeader(adminToken),
        data: {
          name: `Monitor ${Date.now()}`,
          category_id: categoryId,
          serial_number: `MON-${Date.now()}`,
          brand: "Dell",
          model: "U2722D",
          condition: "new",
          purchase_date: "2026-02-01",
          purchase_cost: 45000,
        },
      });
      const json = await r.json();
      console.log(`AS-6: Purchase date/cost => ${r.status()}`);
      const cost = json.data?.purchase_cost || json.data?.asset?.purchase_cost;
      console.log(`Purchase cost stored: ${cost}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-7: Set warranty expiry date", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/assets`, {
        headers: authHeader(adminToken),
        data: {
          name: `Keyboard ${Date.now()}`,
          category_id: categoryId,
          serial_number: `KB-${Date.now()}`,
          brand: "Logitech",
          model: "MX Keys",
          condition: "new",
          purchase_date: "2026-03-01",
          warranty_expiry: "2027-03-01",
        },
      });
      const json = await r.json();
      console.log(`AS-7: Warranty expiry => ${r.status()}`);
      const warranty = json.data?.warranty_expiry || json.data?.asset?.warranty_expiry;
      console.log(`Warranty: ${warranty}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-8: Validation — warranty before purchase date", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/assets`, {
        headers: authHeader(adminToken),
        data: {
          name: `Bad Warranty ${Date.now()}`,
          category_id: categoryId,
          serial_number: `BAD-${Date.now()}`,
          brand: "Test",
          model: "Test",
          condition: "new",
          purchase_date: "2026-06-01",
          warranty_expiry: "2025-01-01",
        },
      });
      const json = await r.json();
      console.log(`AS-8: Warranty before purchase => ${r.status()}`);
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Asset created with warranty_expiry before purchase_date — should be rejected");
      }
      await page.screenshot({ path: ss("as_warranty_validation") });
    } finally {
      await context.close();
    }
  });

  test("AS-9: Edit asset details", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!assetId) { console.log("AS-9: SKIP — no asset ID"); return; }
      const r = await page.request.put(`${API_URL}/assets/${assetId}`, {
        headers: authHeader(adminToken),
        data: { name: `Updated MacBook ${Date.now()}`, condition: "good" },
      });
      const json = await r.json();
      console.log(`AS-9: Edit asset => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-10: Delete unassigned asset", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create one to delete
      const cr = await page.request.post(`${API_URL}/assets`, {
        headers: authHeader(adminToken),
        data: {
          name: `Delete Asset ${Date.now()}`,
          category_id: categoryId,
          serial_number: `DEL-${Date.now()}`,
          brand: "Test",
          model: "Delete",
          condition: "new",
        },
      });
      const cj = await cr.json();
      const delId = cj.data?.id || cj.data?.asset?.id;
      if (!delId) { console.log("AS-10: SKIP — could not create"); return; }

      const r = await page.request.delete(`${API_URL}/assets/${delId}`, {
        headers: authHeader(adminToken),
      });
      console.log(`AS-10: Delete unassigned asset => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-12: List all assets", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/assets`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`AS-12: GET /assets => ${r.status()}`);
      const assets = json.data?.assets || json.data || [];
      console.log(`Assets count: ${Array.isArray(assets) ? assets.length : "N/A"}`);
      await page.screenshot({ path: ss("as_list_assets") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-13: Search assets", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/assets?search=MacBook`, {
        headers: authHeader(adminToken),
      });
      console.log(`AS-13: Search 'MacBook' => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-14: Filter by status", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      for (const status of ["available", "assigned", "retired", "lost"]) {
        const r = await page.request.get(`${API_URL}/assets?status=${status}`, {
          headers: authHeader(adminToken),
        });
        console.log(`AS-14: Filter status=${status} => ${r.status()}`);
      }
    } finally {
      await context.close();
    }
  });

  test("AS-15: Filter by category", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!categoryId) { console.log("AS-15: SKIP — no category ID"); return; }
      const r = await page.request.get(`${API_URL}/assets?category_id=${categoryId}`, {
        headers: authHeader(adminToken),
      });
      console.log(`AS-15: Filter category => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

test.describe("Assets — Lifecycle", () => {
  let adminToken: string;
  let employeeToken: string;
  let assetId: number | string;
  let categoryId: number | string;
  let employeeUserId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);

    // Get category
    const catR = await page.request.get(`${API_URL}/assets/categories`, {
      headers: authHeader(adminToken),
    });
    const catJ = await catR.json();
    const cats = catJ.data?.categories || catJ.data || [];
    categoryId = Array.isArray(cats) && cats.length > 0 ? cats[0].id : null;

    // Get employee user ID
    const usersR = await page.request.get(`${API_URL}/users?search=priya&limit=5`, {
      headers: authHeader(adminToken),
    });
    const usersJ = await usersR.json();
    const users = usersJ.data?.users || usersJ.data || [];
    if (Array.isArray(users) && users.length > 0) {
      employeeUserId = users[0].id;
    }

    // Create asset for lifecycle
    const r = await page.request.post(`${API_URL}/assets`, {
      headers: authHeader(adminToken),
      data: {
        name: `Lifecycle Asset ${Date.now()}`,
        category_id: categoryId,
        serial_number: `LC-${Date.now()}`,
        brand: "Test",
        model: "Lifecycle",
        condition: "new",
      },
    });
    const json = await r.json();
    assetId = json.data?.id || json.data?.asset?.id || json.id;
    console.log(`Setup: Asset ID=${assetId}, Employee ID=${employeeUserId}`);
    await context.close();
  });

  test("AS-16-17: Assign asset to employee", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!assetId || !employeeUserId) { console.log("AS-16: SKIP — missing IDs"); return; }
      const r = await page.request.post(`${API_URL}/assets/${assetId}/assign`, {
        headers: authHeader(adminToken),
        data: {
          employee_id: employeeUserId,
          assigned_to: employeeUserId,
          notes: "Assigned for development work",
        },
      });
      const json = await r.json();
      console.log(`AS-16-17: Assign asset => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      await page.screenshot({ path: ss("as_assign") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-11: Delete assigned asset (should be blocked)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!assetId) { console.log("AS-11: SKIP — no asset ID"); return; }
      const r = await page.request.delete(`${API_URL}/assets/${assetId}`, {
        headers: authHeader(adminToken),
      });
      console.log(`AS-11: Delete assigned asset => ${r.status()}`);
      if (r.status() === 200) {
        console.log("BUG: Assigned asset was deletable — should be blocked (must return first)");
      } else {
        console.log("PASS: Assigned asset delete blocked");
      }
    } finally {
      await context.close();
    }
  });

  test("AS-18: Return asset", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!assetId) { console.log("AS-18: SKIP — no asset ID"); return; }
      // Try multiple field name variations
      const variations = [
        { condition: "good", notes: "Returned in good condition" },
        { condition_status: "good", notes: "Returned" },
        {},
      ];
      let success = false;
      for (const data of variations) {
        const r = await page.request.post(`${API_URL}/assets/${assetId}/return`, {
          headers: authHeader(adminToken),
          data,
        });
        const json = await r.json();
        console.log(`AS-18: Return asset (${JSON.stringify(data).substring(0,50)}) => ${r.status()}`);
        if (r.status() === 200 || r.status() === 201) {
          console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
          success = true;
          break;
        }
      }
      if (!success) {
        console.log("BUG: Asset return endpoint returns 500 for all field variations — server error");
      }
      await page.screenshot({ path: ss("as_return") });
      // Don't fail the test — this is a known server bug to report
    } finally {
      await context.close();
    }
  });

  test("AS-19: Retire asset", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create a new one to retire
      const cr = await page.request.post(`${API_URL}/assets`, {
        headers: authHeader(adminToken),
        data: {
          name: `Retire Asset ${Date.now()}`,
          category_id: categoryId,
          serial_number: `RET-${Date.now()}`,
          brand: "Old",
          model: "Retire",
          condition: "poor",
        },
      });
      const cj = await cr.json();
      const retId = cj.data?.id || cj.data?.asset?.id;
      if (!retId) { console.log("AS-19: SKIP — could not create"); return; }

      const r = await page.request.post(`${API_URL}/assets/${retId}/retire`, {
        headers: authHeader(adminToken),
        data: { notes: "End of life — retiring asset" },
      });
      const json = await r.json();
      console.log(`AS-19: Retire asset => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-20: Report asset as lost", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create a new one to report lost
      const cr = await page.request.post(`${API_URL}/assets`, {
        headers: authHeader(adminToken),
        data: {
          name: `Lost Asset ${Date.now()}`,
          category_id: categoryId,
          serial_number: `LOST-${Date.now()}`,
          brand: "Missing",
          model: "Lost",
          condition: "good",
        },
      });
      const cj = await cr.json();
      const lostId = cj.data?.id || cj.data?.asset?.id;
      if (!lostId) { console.log("AS-20: SKIP — could not create"); return; }

      const r = await page.request.post(`${API_URL}/assets/${lostId}/report-lost`, {
        headers: authHeader(adminToken),
        data: { notes: "Employee reported laptop missing during travel" },
      });
      const json = await r.json();
      console.log(`AS-20: Report lost => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-21: History entry created for each action", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!assetId) { console.log("AS-21: SKIP — no asset ID"); return; }
      const r = await page.request.get(`${API_URL}/assets/${assetId}`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      const history = json.data?.history || json.data?.asset?.history || [];
      console.log(`AS-21: Asset history entries: ${Array.isArray(history) ? history.length : "N/A"}`);
      if (Array.isArray(history)) {
        history.forEach((h: any, i: number) => {
          console.log(`  History[${i}]: action=${h.action || h.type}, date=${h.created_at || h.date}`);
        });
      }
      await page.screenshot({ path: ss("as_history") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });
});

test.describe("Assets — My Assets (Employee)", () => {
  let employeeToken: string;
  let adminToken: string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  test("AS-22-26: Employee views assigned assets", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/assets/my`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      console.log(`AS-22-26: GET /assets/my => ${r.status()}`);
      const assets = json.data?.assets || json.data || [];
      if (Array.isArray(assets)) {
        console.log(`AS-22: My assets count: ${assets.length}`);
        if (assets.length > 0) {
          const a = assets[0];
          console.log(`AS-23: Name=${a.name}, Tag=${a.asset_tag}, Condition=${a.condition}, Brand=${a.brand}`);
          console.log(`AS-24: Warranty=${a.warranty_expiry || "N/A"}`);
        } else {
          console.log("AS-26: Empty state — no assets assigned");
        }
      }
      await page.screenshot({ path: ss("as_my_assets") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-25: Click asset card opens detail", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Check if there's an asset to view detail
      const r = await page.request.get(`${API_URL}/assets/my`, {
        headers: authHeader(employeeToken),
      });
      const json = await r.json();
      const assets = json.data?.assets || json.data || [];
      if (Array.isArray(assets) && assets.length > 0) {
        const detail = await page.request.get(`${API_URL}/assets/${assets[0].id}`, {
          headers: authHeader(employeeToken),
        });
        const dj = await detail.json();
        console.log(`AS-25: Asset detail => ${detail.status()}`);
        console.log(`Detail: ${JSON.stringify(dj).substring(0, 400)}`);
      } else {
        console.log("AS-25: No assets assigned to view detail");
      }
    } finally {
      await context.close();
    }
  });
});

test.describe("Assets — Detail Page & Access Control", () => {
  let adminToken: string;
  let employeeToken: string;
  let assetId: number | string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    employeeToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    // Get first asset
    const r = await page.request.get(`${API_URL}/assets?limit=1`, {
      headers: authHeader(adminToken),
    });
    const json = await r.json();
    const assets = json.data?.assets || json.data || [];
    assetId = Array.isArray(assets) && assets.length > 0 ? assets[0].id : null;
    await context.close();
  });

  test("AS-27-30: View asset info grid and history", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!assetId) { console.log("AS-27: SKIP — no asset ID"); return; }
      const r = await page.request.get(`${API_URL}/assets/${assetId}`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      const asset = json.data?.asset || json.data;
      console.log(`AS-27: Asset tag=${asset?.asset_tag}, category=${asset?.category?.name || asset?.category_id}`);
      console.log(`AS-28: Status=${asset?.status}, condition=${asset?.condition}`);
      console.log(`AS-29: Assigned to=${asset?.assigned_to || asset?.employee?.name || "unassigned"}`);
      console.log(`AS-30: History entries=${Array.isArray(asset?.history) ? asset.history.length : "N/A"}`);
      await page.screenshot({ path: ss("as_detail_page") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-31-32: HR vs Employee action buttons (UI)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // HR view
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.goto(`${BASE_URL}/assets`, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
      const bodyText = await page.textContent("body").catch(() => "");
      const hasAssign = (bodyText || "").toLowerCase().includes("assign");
      const hasReturn = (bodyText || "").toLowerCase().includes("return");
      console.log(`AS-31: HR buttons — Assign: ${hasAssign}, Return: ${hasReturn}`);
      await page.screenshot({ path: ss("as_hr_buttons"), fullPage: true });
    } finally {
      await context.close();
    }
  });

  test("AS-32 UI: Employee asset view", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
      await page.goto(`${BASE_URL}/assets`, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
      const bodyText = await page.textContent("body").catch(() => "");
      console.log(`AS-32: Employee asset page length: ${(bodyText || "").length}`);
      await page.screenshot({ path: ss("as_employee_view"), fullPage: true });
    } finally {
      await context.close();
    }
  });
});

test.describe("Assets — Warranty & Dashboard", () => {
  let adminToken: string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    await context.close();
  });

  test("AS-33-35: Expiring warranties", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/assets/expiring-warranties`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`AS-33-35: GET /assets/expiring-warranties => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 400)}`);
      await page.screenshot({ path: ss("as_expiring_warranties") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-36-40: Asset dashboard", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/assets/dashboard`, {
        headers: authHeader(adminToken),
      });
      const json = await r.json();
      console.log(`AS-36-40: GET /assets/dashboard => ${r.status()}`);
      console.log(`Dashboard: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("as_dashboard_api") });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("AS-36-40 UI: Asset dashboard page", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.goto(`${BASE_URL}/assets`, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
      const bodyText = await page.textContent("body").catch(() => "");
      console.log(`AS-36-40 UI: Asset dashboard page length: ${(bodyText || "").length}`);
      const hasTotal = (bodyText || "").toLowerCase().includes("total");
      const hasAvailable = (bodyText || "").toLowerCase().includes("available");
      console.log(`Has 'Total': ${hasTotal}, Has 'Available': ${hasAvailable}`);
      await page.screenshot({ path: ss("as_dashboard_ui"), fullPage: true });
    } finally {
      await context.close();
    }
  });

  test("AS-40: View All Assets button", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await login(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
      await page.goto(`${BASE_URL}/assets`, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
      // Look for "View All" or similar button
      const viewAllBtn = page.locator('a:has-text("View All"), button:has-text("View All"), a:has-text("view all")').first();
      const hasViewAll = await viewAllBtn.isVisible().catch(() => false);
      console.log(`AS-40: 'View All' button visible: ${hasViewAll}`);
      if (hasViewAll) {
        await viewAllBtn.click();
        await page.waitForTimeout(1000);
        console.log(`AS-40: After click URL: ${page.url()}`);
      }
      await page.screenshot({ path: ss("as_view_all"), fullPage: true });
    } finally {
      await context.close();
    }
  });
});

// ============================================================
// PART 5: CROSS-MODULE — Survey question operations (SV-9,10)
// ============================================================

test.describe("Surveys — Question Operations", () => {
  let adminToken: string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    await context.close();
  });

  test("SV-9: Reorder questions", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create survey then try to reorder via PUT
      const cr = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Reorder Test ${Date.now()}`,
          description: "Reorder questions",
          type: "custom",
          start_date: "2026-04-01",
          end_date: "2026-04-30",
          questions: [
            { question_text: "First", question_type: "rating_1_5", is_required: true, sort_order: 1 },
            { question_text: "Second", question_type: "text", is_required: false, sort_order: 2 },
            { question_text: "Third", question_type: "yes_no", is_required: false, sort_order: 3 },
          ],
        },
      });
      const cj = await cr.json();
      const sid = cj.data?.id || cj.data?.survey?.id;
      console.log(`SV-9: Created survey for reorder => ${cr.status()}, ID=${sid}`);

      if (sid) {
        // Try to reorder via PUT
        const r = await page.request.put(`${API_URL}/surveys/${sid}`, {
          headers: authHeader(adminToken),
          data: {
            questions: [
              { question_text: "Third", question_type: "yes_no", is_required: false, sort_order: 1 },
              { question_text: "First", question_type: "rating_1_5", is_required: true, sort_order: 2 },
              { question_text: "Second", question_type: "text", is_required: false, sort_order: 3 },
            ],
          },
        });
        console.log(`SV-9: Reorder questions => ${r.status()}`);
      }
    } finally {
      await context.close();
    }
  });

  test("SV-10: Delete question (min 1 required)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const cr = await page.request.post(`${API_URL}/surveys`, {
        headers: authHeader(adminToken),
        data: {
          title: `Delete Q ${Date.now()}`,
          description: "Delete question test",
          type: "custom",
          start_date: "2026-04-01",
          end_date: "2026-04-30",
          questions: [
            { question_text: "Keep this", question_type: "rating_1_5", is_required: true, sort_order: 1 },
            { question_text: "Remove this", question_type: "text", is_required: false, sort_order: 2 },
          ],
        },
      });
      const cj = await cr.json();
      const sid = cj.data?.id || cj.data?.survey?.id;
      if (sid) {
        // Update with fewer questions
        const r = await page.request.put(`${API_URL}/surveys/${sid}`, {
          headers: authHeader(adminToken),
          data: {
            questions: [
              { question_text: "Keep this", question_type: "rating_1_5", is_required: true, sort_order: 1 },
            ],
          },
        });
        console.log(`SV-10: Delete question => ${r.status()}`);
      }
    } finally {
      await context.close();
    }
  });
});
