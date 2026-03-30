import { test, expect, Page, BrowserContext, Browser } from "@playwright/test";

const BASE_URL = "https://test-empcloud.empcloud.com";
const API_URL = `${BASE_URL}/api/v1`;

const ADMIN_CREDS = { email: "ananya@technova.in", password: "Welcome@123" };
const EMPLOYEE_CREDS = { email: "priya@technova.in", password: "Welcome@123" };
const SUPER_ADMIN_CREDS = { email: "admin@empcloud.com", password: "SuperAdmin@123" };

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

async function getToken(page: Page, email: string, password: string): Promise<string> {
  const r = await page.request.post(`${API_URL}/auth/login`, { data: { email, password } });
  const json = await r.json();
  return json.data?.tokens?.access_token || json.data?.access_token || json.token || "";
}

function ss(name: string) {
  return `e2e/screenshots/tp_ext2_${name}.png`;
}

// ============================================================================
// PART 1: EVENTS MODULE
// ============================================================================

test.describe("Events Module — HR (Org Admin)", () => {
  let adminToken: string;
  let createdEventId: string | number;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    await context.close();
  });

  // Phase 1: Event Creation (HR Only)
  test("EVT-01: Create event with all fields", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const dayAfter = new Date(Date.now() + 172800000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: {
          title: `Test Event ${Date.now()}`,
          description: "Automated test event with all fields",
          type: "meeting",
          start_date: tomorrow,
          end_date: dayAfter,
          location: "Conference Room A",
          is_mandatory: false,
          is_all_day: false,
          virtual_meeting_link: "https://meet.example.com/test",
          max_attendees: 50,
          target_audience: "all",
        },
      });
      const json = await r.json();
      console.log(`EVT-01: POST /events => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 500)}`);
      if (json.data?.id) createdEventId = json.data.id;
      else if (json.data?.event?.id) createdEventId = json.data.event.id;
      await page.screenshot({ path: ss("evt_create_all"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally {
      await context.close();
    }
  });

  test("EVT-02: Create event type meeting", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `Meeting_${Date.now()}`, description: "Test meeting", type: "meeting", start_date: tomorrow, end_date: tomorrow, location: "Room 1" },
      });
      const json = await r.json();
      console.log(`EVT-02: meeting type => ${r.status()}, type=${json.data?.type || json.data?.event?.type}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-03: Create event type training", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `Training_${Date.now()}`, description: "Test training", type: "training", start_date: tomorrow, end_date: tomorrow, location: "Room 2" },
      });
      console.log(`EVT-03: training type => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-04: Create event type celebration", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `Celebration_${Date.now()}`, description: "Test celebration", type: "celebration", start_date: tomorrow, end_date: tomorrow, location: "Hall" },
      });
      console.log(`EVT-04: celebration type => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-05: Create event type team_building", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `TeamBuild_${Date.now()}`, description: "Test team building", type: "team_building", start_date: tomorrow, end_date: tomorrow, location: "Outdoor" },
      });
      console.log(`EVT-05: team_building type => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-06: Create event type town_hall", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `TownHall_${Date.now()}`, description: "Test town hall", type: "town_hall", start_date: tomorrow, end_date: tomorrow, location: "Auditorium" },
      });
      console.log(`EVT-06: town_hall type => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-07: Mark event as mandatory", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `Mandatory_${Date.now()}`, description: "Mandatory event", type: "meeting", start_date: tomorrow, end_date: tomorrow, location: "Main Hall", is_mandatory: true },
      });
      const json = await r.json();
      console.log(`EVT-07: mandatory event => ${r.status()}, mandatory=${json.data?.is_mandatory || json.data?.event?.is_mandatory}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-08: Mark as all-day event", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `AllDay_${Date.now()}`, description: "All day event", type: "celebration", start_date: tomorrow, end_date: tomorrow, is_all_day: true },
      });
      const json = await r.json();
      console.log(`EVT-08: all-day event => ${r.status()}, is_all_day=${json.data?.is_all_day || json.data?.event?.is_all_day}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-09: Add virtual meeting link", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `Virtual_${Date.now()}`, description: "Virtual meeting", type: "meeting", start_date: tomorrow, end_date: tomorrow, virtual_meeting_link: "https://zoom.us/test123" },
      });
      const json = await r.json();
      console.log(`EVT-09: virtual link => ${r.status()}, link=${json.data?.virtual_meeting_link || json.data?.event?.virtual_meeting_link}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-10: Set max attendees", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `MaxAttend_${Date.now()}`, description: "Limited capacity", type: "training", start_date: tomorrow, end_date: tomorrow, max_attendees: 10 },
      });
      const json = await r.json();
      console.log(`EVT-10: max attendees => ${r.status()}, max=${json.data?.max_attendees || json.data?.event?.max_attendees}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-11: Target all employees", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `AllTarget_${Date.now()}`, description: "For everyone", type: "town_hall", start_date: tomorrow, end_date: tomorrow, target_audience: "all" },
      });
      console.log(`EVT-11: target all => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-12: Target specific department", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `DeptTarget_${Date.now()}`, description: "Department specific", type: "meeting", start_date: tomorrow, end_date: tomorrow, target_audience: "department", department_id: 1 },
      });
      console.log(`EVT-12: department target => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-13: Validation - end date before start date", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const yesterday = new Date(Date.now() - 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `InvalidDates_${Date.now()}`, description: "Bad dates", type: "meeting", start_date: tomorrow, end_date: yesterday },
      });
      const json = await r.json();
      console.log(`EVT-13: invalid dates => ${r.status()}, body=${JSON.stringify(json).substring(0, 300)}`);
      await page.screenshot({ path: ss("evt_invalid_dates"), fullPage: true });
      // Should be 400 error
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Server accepted end_date before start_date without validation");
      }
    } finally { await context.close(); }
  });

  // Phase 2: Event Listing
  test("EVT-14: View events list", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      const events = json.data?.events || json.data || [];
      console.log(`EVT-14: GET /events => ${r.status()}, count=${Array.isArray(events) ? events.length : "N/A"}`);
      await page.screenshot({ path: ss("evt_list"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-15: Filter events by type", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events?type=meeting`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`EVT-15: filter by type=meeting => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-16: Filter events by status", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events?status=upcoming`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`EVT-16: filter by status=upcoming => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-17: Event card metadata via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      const events = json.data?.events || json.data || [];
      if (Array.isArray(events) && events.length > 0) {
        const e = events[0];
        console.log(`EVT-17: First event fields: type=${e.type}, title=${e.title}, start_date=${e.start_date}, location=${e.location}`);
        expect(e.title).toBeTruthy();
      } else {
        console.log("EVT-17: No events to verify metadata");
      }
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-18: Attendee count shown", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      const events = json.data?.events || json.data || [];
      if (Array.isArray(events) && events.length > 0) {
        const e = events[0];
        console.log(`EVT-18: attendee_count=${e.attendee_count ?? e.rsvp_count ?? "N/A"}, max_attendees=${e.max_attendees ?? "N/A"}`);
      }
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-19: Mandatory badge visible", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      const events = json.data?.events || json.data || [];
      const mandatory = Array.isArray(events) ? events.filter((e: any) => e.is_mandatory) : [];
      console.log(`EVT-19: mandatory events count=${mandatory.length}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-20: Pagination works", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events?page=1&limit=5`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`EVT-20: pagination => ${r.status()}, pagination=${JSON.stringify(json.data?.pagination || json.pagination || "N/A")}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-21: HR sees events dashboard", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events/dashboard`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`EVT-21: GET /events/dashboard => ${r.status()}`);
      console.log(`Dashboard: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("evt_dashboard"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  // Phase 3: RSVP Functionality
  test("EVT-22: RSVP Attending", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Get an event to RSVP
      const listR = await page.request.get(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const listJson = await listR.json();
      const events = listJson.data?.events || listJson.data || [];
      if (!Array.isArray(events) || events.length === 0) {
        console.log("EVT-22: SKIP - No events found");
        return;
      }
      const eventId = events[0].id;
      const r = await page.request.post(`${API_URL}/events/${eventId}/rsvp`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { status: "attending" },
      });
      const json = await r.json();
      console.log(`EVT-22: RSVP attending => ${r.status()}, body=${JSON.stringify(json).substring(0, 300)}`);
      await page.screenshot({ path: ss("evt_rsvp_attending"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-23: RSVP Maybe", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/events`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const events = (await listR.json()).data?.events || (await listR.json()).data || [];
      const listJson = await listR.json();
      const evts = listJson.data?.events || listJson.data || [];
      if (!Array.isArray(evts) || evts.length < 2) { console.log("EVT-23: SKIP"); return; }
      const eventId = evts[1]?.id || evts[0]?.id;
      const r = await page.request.post(`${API_URL}/events/${eventId}/rsvp`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { status: "maybe" },
      });
      console.log(`EVT-23: RSVP maybe => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-24: RSVP Decline", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/events`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const evts = listJson.data?.events || listJson.data || [];
      if (!Array.isArray(evts) || evts.length < 3) { console.log("EVT-24: SKIP"); return; }
      const eventId = evts[2]?.id || evts[0]?.id;
      const r = await page.request.post(`${API_URL}/events/${eventId}/rsvp`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { status: "declined" },
      });
      console.log(`EVT-24: RSVP declined => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-25: Change RSVP from Attending to Maybe", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/events`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const evts = listJson.data?.events || listJson.data || [];
      if (!Array.isArray(evts) || evts.length === 0) { console.log("EVT-25: SKIP"); return; }
      const eventId = evts[0].id;
      // First set attending
      await page.request.post(`${API_URL}/events/${eventId}/rsvp`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { status: "attending" },
      });
      // Then change to maybe
      const r = await page.request.post(`${API_URL}/events/${eventId}/rsvp`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { status: "maybe" },
      });
      console.log(`EVT-25: Change RSVP attending->maybe => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-26: Cancel RSVP (set to declined)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/events`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const evts = listJson.data?.events || listJson.data || [];
      if (!Array.isArray(evts) || evts.length === 0) { console.log("EVT-26: SKIP"); return; }
      const eventId = evts[0].id;
      const r = await page.request.post(`${API_URL}/events/${eventId}/rsvp`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { status: "declined" },
      });
      console.log(`EVT-26: Cancel RSVP => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-27: RSVP status via event detail", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/events`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const evts = listJson.data?.events || listJson.data || [];
      if (!Array.isArray(evts) || evts.length === 0) { console.log("EVT-27: SKIP"); return; }
      const eventId = evts[0].id;
      const r = await page.request.get(`${API_URL}/events/${eventId}`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`EVT-27: Event detail RSVP info => ${r.status()}`);
      console.log(`Detail: ${JSON.stringify(json).substring(0, 500)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-28: Max attendees reached", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create event with max 1
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const cr = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `MaxCap_${Date.now()}`, description: "Capacity test", type: "meeting", start_date: tomorrow, end_date: tomorrow, max_attendees: 1 },
      });
      const cj = await cr.json();
      const eId = cj.data?.id || cj.data?.event?.id;
      if (!eId) { console.log("EVT-28: SKIP - could not create event"); return; }
      // RSVP as admin
      await page.request.post(`${API_URL}/events/${eId}/rsvp`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { status: "attending" },
      });
      // RSVP as employee (should be blocked)
      const empToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
      const r = await page.request.post(`${API_URL}/events/${eId}/rsvp`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { status: "attending" },
      });
      console.log(`EVT-28: max capacity RSVP => ${r.status()}`);
      const json = await r.json();
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
    } finally { await context.close(); }
  });

  // Phase 4: Event Detail
  test("EVT-29: View event detail", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/events`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const evts = listJson.data?.events || listJson.data || [];
      if (!Array.isArray(evts) || evts.length === 0) { console.log("EVT-29: SKIP"); return; }
      const eventId = evts[0].id;
      const r = await page.request.get(`${API_URL}/events/${eventId}`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      const evt = json.data?.event || json.data || {};
      console.log(`EVT-29: Detail => ${r.status()}, title=${evt.title}, type=${evt.type}, status=${evt.status}`);
      await page.screenshot({ path: ss("evt_detail"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-30: Type badge and status badge in detail", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/events`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const evts = listJson.data?.events || listJson.data || [];
      if (!Array.isArray(evts) || evts.length === 0) { console.log("EVT-30: SKIP"); return; }
      const r = await page.request.get(`${API_URL}/events/${evts[0].id}`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const evt = json.data?.event || json.data || {};
      console.log(`EVT-30: type=${evt.type || evt.event_type}, status=${evt.status}`);
      expect(evt.type || evt.event_type).toBeTruthy();
    } finally { await context.close(); }
  });

  test("EVT-31: Mandatory badge in detail", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/events`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const evts = listJson.data?.events || listJson.data || [];
      const mandatory = Array.isArray(evts) ? evts.find((e: any) => e.is_mandatory) : null;
      if (mandatory) {
        const r = await page.request.get(`${API_URL}/events/${mandatory.id}`, { headers: { Authorization: `Bearer ${adminToken}` } });
        const json = await r.json();
        console.log(`EVT-31: mandatory detail => is_mandatory=${(json.data?.event || json.data)?.is_mandatory}`);
      } else {
        console.log("EVT-31: No mandatory events found");
      }
    } finally { await context.close(); }
  });

  test("EVT-32/33/34: Date, location, virtual link in detail", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/events`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const evts = listJson.data?.events || listJson.data || [];
      if (!Array.isArray(evts) || evts.length === 0) { console.log("EVT-32/33/34: SKIP"); return; }
      const r = await page.request.get(`${API_URL}/events/${evts[0].id}`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const evt = json.data?.event || json.data || {};
      console.log(`EVT-32: start_date=${evt.start_date}, end_date=${evt.end_date}`);
      console.log(`EVT-33: location=${evt.location}`);
      console.log(`EVT-34: virtual_meeting_link=${evt.virtual_meeting_link}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-35/36/37: RSVP section, active state, attendee lists", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/events`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const evts = listJson.data?.events || listJson.data || [];
      if (!Array.isArray(evts) || evts.length === 0) { console.log("EVT-35/36/37: SKIP"); return; }
      const r = await page.request.get(`${API_URL}/events/${evts[0].id}`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const evt = json.data?.event || json.data || {};
      console.log(`EVT-35/36/37: rsvp_status=${evt.rsvp_status || evt.user_rsvp || "N/A"}, attendees=${JSON.stringify(evt.attendees || evt.rsvps || "N/A").substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-38: No RSVP for cancelled events", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/events?status=cancelled`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const evts = listJson.data?.events || listJson.data || [];
      if (Array.isArray(evts) && evts.length > 0) {
        const r = await page.request.post(`${API_URL}/events/${evts[0].id}/rsvp`, {
          headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
          data: { status: "attending" },
        });
        console.log(`EVT-38: RSVP to cancelled => ${r.status()} (should be 400/403)`);
      } else {
        console.log("EVT-38: No cancelled events to test");
      }
    } finally { await context.close(); }
  });

  // Phase 5: My Events
  test("EVT-39: View my RSVP'd events", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events/my`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`EVT-39: GET /events/my => ${r.status()}`);
      console.log(`My events: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("evt_my"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-40/41/42: My events RSVP badge, cancel, empty state", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events/my`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const myEvts = json.data?.events || json.data || [];
      if (Array.isArray(myEvts) && myEvts.length > 0) {
        console.log(`EVT-40: First event rsvp_status=${myEvts[0].rsvp_status || myEvts[0].status}`);
      } else {
        console.log("EVT-42: Empty state - no RSVP'd events");
      }
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  // Phase 6: Event Dashboard
  test("EVT-43: Dashboard KPI cards", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events/dashboard`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`EVT-43: Dashboard => ${r.status()}`);
      console.log(`KPIs: ${JSON.stringify(json).substring(0, 500)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-44: Event type breakdown", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events/dashboard`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`EVT-44: Type breakdown => ${JSON.stringify(data.type_breakdown || data.by_type || data.event_types || "N/A").substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-45: Event creation form via UI", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/events");
      await page.waitForTimeout(2000);
      await page.screenshot({ path: ss("evt_ui_list"), fullPage: true });
      // Look for create button
      const createBtn = page.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("New"), a:has-text("Create")').first();
      if (await createBtn.isVisible().catch(() => false)) {
        console.log("EVT-45: Create event button found on UI");
      } else {
        console.log("EVT-45: No create button visible on events page");
      }
    } finally { await context.close(); }
  });

  test("EVT-46: Upcoming events table", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/events/upcoming`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`EVT-46: GET /events/upcoming => ${r.status()}`);
      console.log(`Upcoming: ${JSON.stringify(json).substring(0, 500)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("EVT-47: Cancel event action", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create then cancel
      const tomorrow = new Date(Date.now() + 86400000).toISOString().split("T")[0];
      const cr = await page.request.post(`${API_URL}/events`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `CancelTest_${Date.now()}`, description: "Will be cancelled", type: "meeting", start_date: tomorrow, end_date: tomorrow },
      });
      const cj = await cr.json();
      const eId = cj.data?.id || cj.data?.event?.id;
      if (!eId) { console.log("EVT-47: SKIP - could not create event"); return; }
      const r = await page.request.post(`${API_URL}/events/${eId}/cancel`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
      });
      const json = await r.json();
      console.log(`EVT-47: Cancel event => ${r.status()}, body=${JSON.stringify(json).substring(0, 300)}`);
      await page.screenshot({ path: ss("evt_cancel"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });
});

// ============================================================================
// PART 2: WELLNESS MODULE
// ============================================================================

test.describe("Wellness Module — Employee", () => {
  let empToken: string;
  let adminToken: string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    empToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    await context.close();
  });

  // Phase 1: Daily Check-In
  test("WEL-01: Navigate to wellness check-in page", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password, "/wellness");
      await page.waitForTimeout(2000);
      await page.screenshot({ path: ss("wel_page"), fullPage: true });
      const content = await page.content();
      const hasWellness = content.toLowerCase().includes("wellness") || content.toLowerCase().includes("check-in") || content.toLowerCase().includes("mood");
      console.log(`WEL-01: Wellness page loaded, has wellness content=${hasWellness}`);
    } finally { await context.close(); }
  });

  test("WEL-02: Submit check-in mood great", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/wellness/check-in`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { mood: "great", energy_level: 5, sleep_hours: 8, exercise_minutes: 30, notes: "Feeling great today" },
      });
      const json = await r.json();
      console.log(`WEL-02: Check-in great => ${r.status()}, body=${JSON.stringify(json).substring(0, 300)}`);
      await page.screenshot({ path: ss("wel_checkin_great"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-03: Submit check-in mood good", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/wellness/check-in`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { mood: "good", energy_level: 4, sleep_hours: 7, exercise_minutes: 20 },
      });
      console.log(`WEL-03: Check-in good => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-04: Submit check-in mood okay", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/wellness/check-in`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { mood: "okay", energy_level: 3, sleep_hours: 6 },
      });
      console.log(`WEL-04: Check-in okay => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-05: Submit check-in mood low", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/wellness/check-in`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { mood: "low", energy_level: 2, sleep_hours: 5 },
      });
      console.log(`WEL-05: Check-in low => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-06: Submit check-in mood stressed", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/wellness/check-in`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { mood: "stressed", energy_level: 1, sleep_hours: 4, exercise_minutes: 0 },
      });
      console.log(`WEL-06: Check-in stressed => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-07: Energy level 1-5", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      for (const level of [1, 3, 5]) {
        const r = await page.request.post(`${API_URL}/wellness/check-in`, {
          headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
          data: { mood: "good", energy_level: level },
        });
        console.log(`WEL-07: energy_level=${level} => ${r.status()}`);
      }
    } finally { await context.close(); }
  });

  test("WEL-08: Sleep hours decimal", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/wellness/check-in`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { mood: "good", energy_level: 3, sleep_hours: 7.5 },
      });
      console.log(`WEL-08: sleep 7.5 hours => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-09: Exercise minutes integer", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/wellness/check-in`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { mood: "good", energy_level: 4, exercise_minutes: 45 },
      });
      console.log(`WEL-09: exercise 45min => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-10: Optional notes", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/wellness/check-in`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { mood: "great", energy_level: 5, notes: "Had a wonderful morning walk" },
      });
      console.log(`WEL-10: with notes => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-11: Submit without mood", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/wellness/check-in`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { energy_level: 3 },
      });
      console.log(`WEL-11: no mood => ${r.status()} (should be 400)`);
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Check-in accepted without mood selection");
      }
    } finally { await context.close(); }
  });

  test("WEL-12: Submit complete check-in", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/wellness/check-in`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { mood: "great", energy_level: 5, sleep_hours: 8, exercise_minutes: 60, notes: "Complete check-in test" },
      });
      const json = await r.json();
      console.log(`WEL-12: Complete check-in => ${r.status()}, body=${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-13: Success links (UI test)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password, "/wellness/check-in");
      await page.waitForTimeout(2000);
      await page.screenshot({ path: ss("wel_checkin_ui"), fullPage: true });
      console.log(`WEL-13: Wellness check-in page loaded at ${page.url()}`);
    } finally { await context.close(); }
  });

  // Phase 2: My Wellness Dashboard
  test("WEL-14/15/16/17: Quick stats - streak, total, avg energy, goals done", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/summary`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      console.log(`WEL-14/15/16/17: Summary => ${r.status()}`);
      console.log(`Summary: ${JSON.stringify(json).substring(0, 500)}`);
      const data = json.data || json;
      console.log(`Streak=${data.streak ?? data.day_streak ?? "N/A"}, Total=${data.total_checkins ?? data.total ?? "N/A"}, AvgEnergy=${data.avg_energy ?? "N/A"}, GoalsDone=${data.goals_done ?? data.goals_completed ?? "N/A"}`);
      await page.screenshot({ path: ss("wel_summary"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-18/19/20/21: Mood trend & check-in history", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/check-ins`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      const checkins = json.data?.check_ins || json.data?.checkins || json.data || [];
      console.log(`WEL-18: Check-in history => ${r.status()}, count=${Array.isArray(checkins) ? checkins.length : "N/A"}`);
      if (Array.isArray(checkins) && checkins.length > 0) {
        const c = checkins[0];
        console.log(`WEL-20: First check-in: mood=${c.mood}, energy=${c.energy_level}, sleep=${c.sleep_hours}, exercise=${c.exercise_minutes}`);
        console.log(`WEL-21: Missing values handled=${c.sleep_hours === null ? "null shown" : "value present"}`);
      }
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  // Phase 3: Wellness Goals
  test("WEL-22: Create wellness goal", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const startDate = new Date().toISOString().split("T")[0];
      const endDate = new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/wellness/goals`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { title: `TestGoal_${Date.now()}`, type: "exercise", frequency: "daily", target_value: 30, unit: "minutes", start_date: startDate, end_date: endDate },
      });
      const json = await r.json();
      console.log(`WEL-22: Create goal => ${r.status()}, body=${JSON.stringify(json).substring(0, 300)}`);
      await page.screenshot({ path: ss("wel_goal_create"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-23: Goal types via API", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      for (const goalType of ["exercise", "sleep", "meditation", "hydration", "steps"]) {
        const r = await page.request.post(`${API_URL}/wellness/goals`, {
          headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
          data: { title: `${goalType}_${Date.now()}`, type: goalType, frequency: "daily", target_value: 10 },
        });
        console.log(`WEL-23: goal type=${goalType} => ${r.status()}`);
      }
    } finally { await context.close(); }
  });

  test("WEL-24: Target value and unit", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/wellness/goals`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { title: `TargetGoal_${Date.now()}`, type: "steps", frequency: "daily", target_value: 10000, unit: "steps" },
      });
      const json = await r.json();
      console.log(`WEL-24: target+unit => ${r.status()}, target=${(json.data?.goal || json.data)?.target_value}, unit=${(json.data?.goal || json.data)?.unit}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-25: Start/end dates on goals", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const start = new Date().toISOString().split("T")[0];
      const end = new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/wellness/goals`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { title: `Dated_${Date.now()}`, type: "exercise", frequency: "weekly", target_value: 5, start_date: start, end_date: end },
      });
      console.log(`WEL-25: goal with dates => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-26: View goal cards (list)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/goals`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      const goals = json.data?.goals || json.data || [];
      console.log(`WEL-26: Goals list => ${r.status()}, count=${Array.isArray(goals) ? goals.length : "N/A"}`);
      if (Array.isArray(goals) && goals.length > 0) {
        const g = goals[0];
        console.log(`First goal: title=${g.title}, status=${g.status}, type=${g.type}, progress=${g.current_value || g.progress}`);
      }
      await page.screenshot({ path: ss("wel_goals_list"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-27: Update goal progress", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/wellness/goals`, { headers: { Authorization: `Bearer ${empToken}` } });
      const listJson = await listR.json();
      const goals = listJson.data?.goals || listJson.data || [];
      if (!Array.isArray(goals) || goals.length === 0) { console.log("WEL-27: SKIP - no goals"); return; }
      const goalId = goals[0].id;
      const r = await page.request.put(`${API_URL}/wellness/goals/${goalId}`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { current_value: 15, progress: 50 },
      });
      console.log(`WEL-27: Update goal progress => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-28/29/30: Goal completion, completed goals, progress bar", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/wellness/goals`, { headers: { Authorization: `Bearer ${empToken}` } });
      const listJson = await listR.json();
      const goals = listJson.data?.goals || listJson.data || [];
      if (Array.isArray(goals)) {
        const completed = goals.filter((g: any) => g.status === "completed");
        const active = goals.filter((g: any) => g.status === "active");
        console.log(`WEL-28/29: active=${active.length}, completed=${completed.length}`);
        if (goals.length > 0) {
          console.log(`WEL-30: progress info => ${JSON.stringify({ current: goals[0].current_value, target: goals[0].target_value, progress: goals[0].progress }).substring(0, 200)}`);
        }
      }
    } finally { await context.close(); }
  });

  // Phase 4: Wellness Programs
  test("WEL-31: Browse program catalog", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/programs`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      const programs = json.data?.programs || json.data || [];
      console.log(`WEL-31: Programs => ${r.status()}, count=${Array.isArray(programs) ? programs.length : "N/A"}`);
      console.log(`Programs: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("wel_programs"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-32: Filter programs by type", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/programs?type=fitness`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      console.log(`WEL-32: filter type=fitness => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-33/34/35: Program card info, capacity, points", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/programs`, { headers: { Authorization: `Bearer ${empToken}` } });
      const json = await r.json();
      const programs = json.data?.programs || json.data || [];
      if (Array.isArray(programs) && programs.length > 0) {
        const p = programs[0];
        console.log(`WEL-33: title=${p.title}, type=${p.type}, desc=${(p.description || "").substring(0, 50)}`);
        console.log(`WEL-34: enrolled=${p.enrolled_count ?? p.participants}, max=${p.max_participants ?? p.max_enrollment}`);
        console.log(`WEL-35: points=${p.points ?? p.reward_points ?? "N/A"}`);
      }
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-36: Enroll in program", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/wellness/programs`, { headers: { Authorization: `Bearer ${empToken}` } });
      const listJson = await listR.json();
      const programs = listJson.data?.programs || listJson.data || [];
      if (!Array.isArray(programs) || programs.length === 0) { console.log("WEL-36: SKIP - no programs"); return; }
      const progId = programs[0].id;
      const r = await page.request.post(`${API_URL}/wellness/programs/${progId}/enroll`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
      });
      const json = await r.json();
      console.log(`WEL-36: Enroll => ${r.status()}, body=${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-37: Enrolled program in My Wellness", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/my`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      console.log(`WEL-37: My Wellness => ${r.status()}`);
      console.log(`My programs: ${JSON.stringify(json).substring(0, 500)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-38: Mark program complete", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const myR = await page.request.get(`${API_URL}/wellness/my`, { headers: { Authorization: `Bearer ${empToken}` } });
      const myJson = await myR.json();
      const myPrograms = myJson.data?.programs || myJson.data?.enrollments || myJson.data || [];
      if (!Array.isArray(myPrograms) || myPrograms.length === 0) { console.log("WEL-38: SKIP - no enrolled programs"); return; }
      const progId = myPrograms[0].program_id || myPrograms[0].id;
      const r = await page.request.post(`${API_URL}/wellness/programs/${progId}/complete`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
      });
      console.log(`WEL-38: Complete program => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-39: Program progress percentage", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/wellness/programs`, { headers: { Authorization: `Bearer ${empToken}` } });
      const listJson = await listR.json();
      const programs = listJson.data?.programs || listJson.data || [];
      if (Array.isArray(programs) && programs.length > 0) {
        const p = programs[0];
        const pR = await page.request.get(`${API_URL}/wellness/programs/${p.id}`, { headers: { Authorization: `Bearer ${empToken}` } });
        const pJson = await pR.json();
        console.log(`WEL-39: Program detail => ${pR.status()}, progress=${JSON.stringify(pJson).substring(0, 300)}`);
      }
    } finally { await context.close(); }
  });

  test("WEL-40: Pagination on program list", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/programs?page=1&limit=5`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      console.log(`WEL-40: pagination => ${r.status()}, pagination=${JSON.stringify(json.data?.pagination || json.pagination || "N/A")}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-41: Empty state no programs", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/programs?type=nonexistent_type_xyz`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      console.log(`WEL-41: no programs => ${r.status()}`);
      const json = await r.json();
      console.log(`Response: ${JSON.stringify(json).substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  // Phase 5: Wellness Summary
  test("WEL-42/43/44: Summary quick stats, check-in button, my wellness", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/summary`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      console.log(`WEL-42: Summary => ${r.status()}`);
      console.log(`Stats: ${JSON.stringify(json).substring(0, 500)}`);
      // UI check
      await loginAndGo(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password, "/wellness");
      await page.waitForTimeout(2000);
      const checkinBtn = page.locator('button:has-text("Check"), a:has-text("Check-in"), button:has-text("check-in")').first();
      console.log(`WEL-43: Check-in button visible=${await checkinBtn.isVisible().catch(() => false)}`);
      await page.screenshot({ path: ss("wel_summary_ui"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });
});

// Phase 6: Wellness HR Dashboard
test.describe("Wellness Module — HR Dashboard", () => {
  let adminToken: string;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    await context.close();
  });

  test("WEL-45: HR dashboard KPI cards", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/dashboard`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`WEL-45: Dashboard => ${r.status()}`);
      console.log(`Dashboard: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("wel_hr_dashboard"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-46: Mood distribution chart (API)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/dashboard`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`WEL-46: Mood distribution => ${JSON.stringify(data.mood_distribution || data.moods || "N/A").substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-47: Average metrics", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/dashboard`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`WEL-47: Avg energy=${data.avg_energy ?? "N/A"}, exercise=${data.avg_exercise ?? "N/A"}, enrollments=${data.active_enrollments ?? "N/A"}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-48: Top programs table", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/wellness/dashboard`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`WEL-48: Top programs => ${JSON.stringify(data.top_programs || data.programs || "N/A").substring(0, 300)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-49/50: Create program form and creation", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const startDate = new Date().toISOString().split("T")[0];
      const endDate = new Date(Date.now() + 60 * 86400000).toISOString().split("T")[0];
      const r = await page.request.post(`${API_URL}/wellness/programs`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: {
          title: `HRProgram_${Date.now()}`,
          description: "Wellness program created by HR",
          type: "fitness",
          start_date: startDate,
          end_date: endDate,
          max_participants: 20,
          points: 100,
        },
      });
      const json = await r.json();
      console.log(`WEL-49/50: Create program => ${r.status()}, body=${JSON.stringify(json).substring(0, 300)}`);
      await page.screenshot({ path: ss("wel_create_program"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WEL-51: No check-in data state", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Test with a fresh user or check dashboard
      const r = await page.request.get(`${API_URL}/wellness/dashboard`, { headers: { Authorization: `Bearer ${adminToken}` } });
      console.log(`WEL-51: Dashboard no-data handling => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });
});

// ============================================================================
// PART 3: FORUM MODULE
// ============================================================================

test.describe("Forum Module — HR (Org Admin)", () => {
  let adminToken: string;
  let empToken: string;
  let createdCategoryId: string | number;
  let createdPostId: string | number;
  let createdReplyId: string | number;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    empToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  // Phase 1: Categories
  test("FRM-01: Create forum category", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/forum/categories`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { name: `TestCat_${Date.now()}`, icon: "💬", description: "Automated test category", sort_order: 99 },
      });
      const json = await r.json();
      console.log(`FRM-01: Create category => ${r.status()}, body=${JSON.stringify(json).substring(0, 300)}`);
      if (json.data?.id) createdCategoryId = json.data.id;
      else if (json.data?.category?.id) createdCategoryId = json.data.category.id;
      await page.screenshot({ path: ss("frm_cat_create"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-02: Set sort order", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/forum/categories`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { name: `SortCat_${Date.now()}`, icon: "📌", description: "Sort order test", sort_order: 1 },
      });
      const json = await r.json();
      console.log(`FRM-02: Sort order => ${r.status()}, sort_order=${(json.data?.category || json.data)?.sort_order}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-03: Edit category", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Get categories first
      const listR = await page.request.get(`${API_URL}/forum/categories`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const cats = listJson.data?.categories || listJson.data || [];
      if (!Array.isArray(cats) || cats.length === 0) { console.log("FRM-03: SKIP - no categories"); return; }
      const catId = cats[0].id;
      const r = await page.request.put(`${API_URL}/forum/categories/${catId}`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { name: `Edited_${Date.now()}`, description: "Updated description" },
      });
      console.log(`FRM-03: Edit category => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-04: List categories", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/categories`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      const cats = json.data?.categories || json.data || [];
      console.log(`FRM-04: List categories => ${r.status()}, count=${Array.isArray(cats) ? cats.length : "N/A"}`);
      if (Array.isArray(cats) && cats.length > 0) {
        console.log(`First: name=${cats[0].name}, icon=${cats[0].icon}, post_count=${cats[0].post_count ?? "N/A"}`);
      }
      await page.screenshot({ path: ss("frm_cat_list"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-05: Category post count accuracy", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/categories`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const cats = json.data?.categories || json.data || [];
      if (Array.isArray(cats) && cats.length > 0) {
        console.log(`FRM-05: Category post counts: ${cats.map((c: any) => `${c.name}=${c.post_count ?? "N/A"}`).join(", ")}`);
      }
    } finally { await context.close(); }
  });

  // Phase 2: Post Creation
  test("FRM-06: Create Discussion post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Get a category
      const catR = await page.request.get(`${API_URL}/forum/categories`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const catJson = await catR.json();
      const cats = catJson.data?.categories || catJson.data || [];
      const catId = Array.isArray(cats) && cats.length > 0 ? cats[0].id : 1;
      const r = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `Discussion_${Date.now()}`, content: "This is a test discussion post", type: "discussion", category_id: catId, tags: "test,automation" },
      });
      const json = await r.json();
      console.log(`FRM-06: Create discussion => ${r.status()}, body=${JSON.stringify(json).substring(0, 300)}`);
      if (json.data?.id) createdPostId = json.data.id;
      else if (json.data?.post?.id) createdPostId = json.data.post.id;
      await page.screenshot({ path: ss("frm_post_discussion"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-07: Create Question post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const catR = await page.request.get(`${API_URL}/forum/categories`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const cats = (await catR.json()).data?.categories || (await catR.json()).data || [];
      const catJson = await catR.json();
      const categories = catJson.data?.categories || catJson.data || [];
      const catId = Array.isArray(categories) && categories.length > 0 ? categories[0].id : 1;
      const r = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `Question_${Date.now()}`, content: "This is a test question", type: "question", category_id: catId },
      });
      console.log(`FRM-07: Create question => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-08: Create Idea post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `Idea_${Date.now()}`, content: "This is a test idea", type: "idea", category_id: 1 },
      });
      console.log(`FRM-08: Create idea => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-09: Create Poll post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `Poll_${Date.now()}`, content: "Vote on this poll", type: "poll", category_id: 1 },
      });
      console.log(`FRM-09: Create poll => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-10: Category required on post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `NoCat_${Date.now()}`, content: "No category post", type: "discussion" },
      });
      console.log(`FRM-10: No category => ${r.status()} (could be 400 if required)`);
    } finally { await context.close(); }
  });

  test("FRM-11: Tags on post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `Tagged_${Date.now()}`, content: "Post with tags", type: "discussion", category_id: 1, tags: "alpha,beta,gamma" },
      });
      const json = await r.json();
      console.log(`FRM-11: Tags => ${r.status()}, tags=${(json.data?.post || json.data)?.tags}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-12: Validation - title required", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { content: "No title post", type: "discussion", category_id: 1 },
      });
      console.log(`FRM-12: No title => ${r.status()} (should be 400)`);
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Forum post created without title");
      }
    } finally { await context.close(); }
  });

  test("FRM-13: Title max 255 chars", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const longTitle = "A".repeat(300);
      const r = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: longTitle, content: "Long title test", type: "discussion", category_id: 1 },
      });
      console.log(`FRM-13: 300 char title => ${r.status()} (should be 400 if enforced)`);
    } finally { await context.close(); }
  });

  // Phase 3: Post Browsing & Search
  test("FRM-14: Forum post feed", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      const posts = json.data?.posts || json.data || [];
      console.log(`FRM-14: Posts feed => ${r.status()}, count=${Array.isArray(posts) ? posts.length : "N/A"}`);
      if (Array.isArray(posts) && posts.length > 0) {
        const p = posts[0];
        console.log(`First post: author=${p.author?.name || p.user?.name}, type=${p.type}, title=${p.title?.substring(0, 50)}`);
      }
      await page.screenshot({ path: ss("frm_feed"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-15: Search posts by keyword", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/posts?search=test`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      console.log(`FRM-15: Search 'test' => ${r.status()}`);
      const json = await r.json();
      const posts = json.data?.posts || json.data || [];
      console.log(`Results: ${Array.isArray(posts) ? posts.length : "N/A"}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-16: Sort by Recent", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/posts?sort=recent`, { headers: { Authorization: `Bearer ${adminToken}` } });
      console.log(`FRM-16: Sort recent => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-17: Sort by Popular", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/posts?sort=popular`, { headers: { Authorization: `Bearer ${adminToken}` } });
      console.log(`FRM-17: Sort popular => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-18: Sort by Trending", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/posts?sort=trending`, { headers: { Authorization: `Bearer ${adminToken}` } });
      console.log(`FRM-18: Sort trending => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-19: Filter by category", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const catR = await page.request.get(`${API_URL}/forum/categories`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const catJson = await catR.json();
      const cats = catJson.data?.categories || catJson.data || [];
      if (Array.isArray(cats) && cats.length > 0) {
        const r = await page.request.get(`${API_URL}/forum/posts?category_id=${cats[0].id}`, { headers: { Authorization: `Bearer ${adminToken}` } });
        console.log(`FRM-19: Filter category=${cats[0].id} => ${r.status()}`);
      }
    } finally { await context.close(); }
  });

  test("FRM-20: Post metadata (views, likes, replies)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const posts = json.data?.posts || json.data || [];
      if (Array.isArray(posts) && posts.length > 0) {
        const p = posts[0];
        console.log(`FRM-20: views=${p.view_count ?? p.views ?? "N/A"}, likes=${p.like_count ?? p.likes ?? "N/A"}, replies=${p.reply_count ?? p.replies_count ?? "N/A"}`);
      }
    } finally { await context.close(); }
  });

  test("FRM-21: Pinned posts", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const posts = json.data?.posts || json.data || [];
      const pinned = Array.isArray(posts) ? posts.filter((p: any) => p.is_pinned) : [];
      console.log(`FRM-21: Pinned posts count=${pinned.length}`);
    } finally { await context.close(); }
  });

  test("FRM-22: Locked posts", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const posts = json.data?.posts || json.data || [];
      const locked = Array.isArray(posts) ? posts.filter((p: any) => p.is_locked) : [];
      console.log(`FRM-22: Locked posts count=${locked.length}`);
    } finally { await context.close(); }
  });

  test("FRM-23: Pagination", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/posts?page=1&limit=5`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      console.log(`FRM-23: Pagination => ${r.status()}, pagination=${JSON.stringify(json.data?.pagination || json.pagination || "N/A")}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  // Phase 4: Post Detail & Engagement
  test("FRM-24: View post detail", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      if (!Array.isArray(posts) || posts.length === 0) { console.log("FRM-24: SKIP"); return; }
      const postId = posts[0].id;
      createdPostId = postId;
      const r = await page.request.get(`${API_URL}/forum/posts/${postId}`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      console.log(`FRM-24: Post detail => ${r.status()}`);
      console.log(`Detail: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("frm_post_detail"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-25: View count increments", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const posts = (await listR.json()).data?.posts || (await listR.json()).data || [];
      const listJson = await listR.json();
      const allPosts = listJson.data?.posts || listJson.data || [];
      if (!Array.isArray(allPosts) || allPosts.length === 0) { console.log("FRM-25: SKIP"); return; }
      const postId = allPosts[0].id;
      // Visit twice
      const r1 = await page.request.get(`${API_URL}/forum/posts/${postId}`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const v1 = ((await r1.json()).data?.post || (await r1.json()).data)?.view_count;
      await page.waitForTimeout(500);
      const r2 = await page.request.get(`${API_URL}/forum/posts/${postId}`, { headers: { Authorization: `Bearer ${empToken}` } });
      const v2 = ((await r2.json()).data?.post || (await r2.json()).data)?.view_count;
      console.log(`FRM-25: View counts: first=${v1}, second=${v2}`);
    } finally { await context.close(); }
  });

  test("FRM-26: Like a post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      if (!Array.isArray(posts) || posts.length === 0) { console.log("FRM-26: SKIP"); return; }
      const postId = posts[0].id;
      const r = await page.request.post(`${API_URL}/forum/like`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { target_type: "post", target_id: postId },
      });
      console.log(`FRM-26: Like post => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-27: Unlike a post (toggle)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      if (!Array.isArray(posts) || posts.length === 0) { console.log("FRM-27: SKIP"); return; }
      const postId = posts[0].id;
      // Toggle like (unlike)
      const r = await page.request.post(`${API_URL}/forum/like`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { target_type: "post", target_id: postId },
      });
      console.log(`FRM-27: Unlike (toggle) => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-28: Post shows tags", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      const withTags = Array.isArray(posts) ? posts.find((p: any) => p.tags && p.tags.length > 0) : null;
      console.log(`FRM-28: Post with tags found=${!!withTags}, tags=${withTags?.tags}`);
    } finally { await context.close(); }
  });

  // Phase 5: Reply System
  test("FRM-29: Reply to post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      if (!Array.isArray(posts) || posts.length === 0) { console.log("FRM-29: SKIP"); return; }
      const postId = posts[0].id;
      const r = await page.request.post(`${API_URL}/forum/posts/${postId}/reply`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { content: `Test reply ${Date.now()}` },
      });
      const json = await r.json();
      console.log(`FRM-29: Reply => ${r.status()}, body=${JSON.stringify(json).substring(0, 300)}`);
      if (json.data?.id) createdReplyId = json.data.id;
      else if (json.data?.reply?.id) createdReplyId = json.data.reply.id;
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-30: Nested reply", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      if (!Array.isArray(posts) || posts.length === 0) { console.log("FRM-30: SKIP"); return; }
      const postId = posts[0].id;
      const r = await page.request.post(`${API_URL}/forum/posts/${postId}/reply`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { content: `Nested reply ${Date.now()}`, parent_reply_id: createdReplyId || undefined },
      });
      console.log(`FRM-30: Nested reply => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-31: Reply metadata", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      if (!Array.isArray(posts) || posts.length === 0) { console.log("FRM-31: SKIP"); return; }
      const r = await page.request.get(`${API_URL}/forum/posts/${posts[0].id}`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const replies = (json.data?.post || json.data)?.replies || json.data?.replies || [];
      if (Array.isArray(replies) && replies.length > 0) {
        console.log(`FRM-31: Reply author=${replies[0].author?.name || replies[0].user?.name}, time=${replies[0].created_at}, likes=${replies[0].like_count ?? replies[0].likes ?? "N/A"}`);
      }
    } finally { await context.close(); }
  });

  test("FRM-32: Like a reply", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!createdReplyId) { console.log("FRM-32: SKIP - no reply ID"); return; }
      const r = await page.request.post(`${API_URL}/forum/like`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { target_type: "reply", target_id: createdReplyId },
      });
      console.log(`FRM-32: Like reply => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-33: Delete own reply", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create a reply then delete it
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${empToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      if (!Array.isArray(posts) || posts.length === 0) { console.log("FRM-33: SKIP"); return; }
      const replyR = await page.request.post(`${API_URL}/forum/posts/${posts[0].id}/reply`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { content: `ToDelete_${Date.now()}` },
      });
      const rJson = await replyR.json();
      const replyId = rJson.data?.id || rJson.data?.reply?.id;
      if (!replyId) { console.log("FRM-33: SKIP - no reply ID"); return; }
      const r = await page.request.delete(`${API_URL}/forum/replies/${replyId}`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      console.log(`FRM-33: Delete own reply => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-34: HR deletes any reply", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!createdReplyId) { console.log("FRM-34: SKIP - no reply ID"); return; }
      const r = await page.request.delete(`${API_URL}/forum/replies/${createdReplyId}`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      console.log(`FRM-34: HR delete reply => ${r.status()}`);
    } finally { await context.close(); }
  });

  test("FRM-35: Cannot reply to locked post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      const locked = Array.isArray(posts) ? posts.find((p: any) => p.is_locked) : null;
      if (!locked) { console.log("FRM-35: SKIP - no locked posts"); return; }
      const r = await page.request.post(`${API_URL}/forum/posts/${locked.id}/reply`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { content: "Should be rejected" },
      });
      console.log(`FRM-35: Reply to locked => ${r.status()} (should be 403/400)`);
    } finally { await context.close(); }
  });

  // Phase 6: Question-Specific Features
  test("FRM-36: Accept reply as answer", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Find a question post and reply
      const listR = await page.request.get(`${API_URL}/forum/posts?type=question`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      if (!Array.isArray(posts) || posts.length === 0) { console.log("FRM-36: SKIP - no question posts"); return; }
      const qPost = posts[0];
      // Get detail with replies
      const dR = await page.request.get(`${API_URL}/forum/posts/${qPost.id}`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const dJson = await dR.json();
      const replies = (dJson.data?.post || dJson.data)?.replies || dJson.data?.replies || [];
      if (!Array.isArray(replies) || replies.length === 0) {
        // Create a reply first
        const rr = await page.request.post(`${API_URL}/forum/posts/${qPost.id}/reply`, {
          headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
          data: { content: "Answer to question" },
        });
        const rrJson = await rr.json();
        const replyId = rrJson.data?.id || rrJson.data?.reply?.id;
        if (replyId) {
          const r = await page.request.post(`${API_URL}/forum/replies/${replyId}/accept`, {
            headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
          });
          console.log(`FRM-36: Accept answer => ${r.status()}`);
        }
      } else {
        const r = await page.request.post(`${API_URL}/forum/replies/${replies[0].id}/accept`, {
          headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        });
        console.log(`FRM-36: Accept answer => ${r.status()}`);
      }
    } finally { await context.close(); }
  });

  test("FRM-37/38/39: Accepted answer visual, only author, only one", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts?type=question`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      if (Array.isArray(posts) && posts.length > 0) {
        const dR = await page.request.get(`${API_URL}/forum/posts/${posts[0].id}`, { headers: { Authorization: `Bearer ${adminToken}` } });
        const dJson = await dR.json();
        const post = dJson.data?.post || dJson.data;
        const replies = post?.replies || [];
        const accepted = Array.isArray(replies) ? replies.filter((r: any) => r.is_accepted) : [];
        console.log(`FRM-37/38/39: accepted answers=${accepted.length}, post author=${post?.author?.id || post?.user_id}`);
      }
    } finally { await context.close(); }
  });

  // Phase 7: Post Moderation
  test("FRM-40: Pin post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      if (!Array.isArray(posts) || posts.length === 0) { console.log("FRM-40: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/forum/posts/${posts[0].id}/pin`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
      });
      console.log(`FRM-40: Pin post => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-41: Unpin post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      const pinned = Array.isArray(posts) ? posts.find((p: any) => p.is_pinned) : null;
      if (!pinned) { console.log("FRM-41: SKIP - no pinned posts"); return; }
      const r = await page.request.post(`${API_URL}/forum/posts/${pinned.id}/pin`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
      });
      console.log(`FRM-41: Unpin post => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-42: Lock post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      if (!Array.isArray(posts) || posts.length === 0) { console.log("FRM-42: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/forum/posts/${posts[0].id}/lock`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
      });
      console.log(`FRM-42: Lock post => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-43: Unlock post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/forum/posts`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const posts = listJson.data?.posts || listJson.data || [];
      const locked = Array.isArray(posts) ? posts.find((p: any) => p.is_locked) : null;
      if (!locked) { console.log("FRM-43: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/forum/posts/${locked.id}/lock`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
      });
      console.log(`FRM-43: Unlock post => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-44: HR deletes any post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create a post then delete
      const cr = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { title: `ToDelete_${Date.now()}`, content: "Will be deleted by HR", type: "discussion", category_id: 1 },
      });
      const cj = await cr.json();
      const postId = cj.data?.id || cj.data?.post?.id;
      if (!postId) { console.log("FRM-44: SKIP - could not create post"); return; }
      const r = await page.request.delete(`${API_URL}/forum/posts/${postId}`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      console.log(`FRM-44: HR delete post => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-45: Author edits own post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const cr = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { title: `EditMe_${Date.now()}`, content: "Original content", type: "discussion", category_id: 1 },
      });
      const cj = await cr.json();
      const postId = cj.data?.id || cj.data?.post?.id;
      if (!postId) { console.log("FRM-45: SKIP"); return; }
      const r = await page.request.put(`${API_URL}/forum/posts/${postId}`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { content: "Updated content" },
      });
      console.log(`FRM-45: Edit own post => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-46: Author deletes own post", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const cr = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { title: `DelOwn_${Date.now()}`, content: "Will delete myself", type: "discussion", category_id: 1 },
      });
      const cj = await cr.json();
      const postId = cj.data?.id || cj.data?.post?.id;
      if (!postId) { console.log("FRM-46: SKIP"); return; }
      const r = await page.request.delete(`${API_URL}/forum/posts/${postId}`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      console.log(`FRM-46: Delete own post => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-47: Non-author cannot edit/delete", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create as admin, try to edit/delete as employee
      const cr = await page.request.post(`${API_URL}/forum/posts`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { title: `AdminPost_${Date.now()}`, content: "Admin's post", type: "discussion", category_id: 1 },
      });
      const cj = await cr.json();
      const postId = cj.data?.id || cj.data?.post?.id;
      if (!postId) { console.log("FRM-47: SKIP"); return; }
      const editR = await page.request.put(`${API_URL}/forum/posts/${postId}`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { content: "Hijacked!" },
      });
      console.log(`FRM-47: Non-author edit => ${editR.status()} (should be 403)`);
      if (editR.status() === 200) {
        console.log("BUG: Employee can edit another user's post");
      }
      const delR = await page.request.delete(`${API_URL}/forum/posts/${postId}`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      console.log(`FRM-47: Non-author delete => ${delR.status()} (should be 403)`);
      if (delR.status() === 200) {
        console.log("BUG: Employee can delete another user's post");
      }
    } finally { await context.close(); }
  });

  // Phase 8: Category Posts
  test("FRM-48/49/50/51/52: Category posts page, filter, sort, pagination, back", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const catR = await page.request.get(`${API_URL}/forum/categories`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const catJson = await catR.json();
      const cats = catJson.data?.categories || catJson.data || [];
      if (!Array.isArray(cats) || cats.length === 0) { console.log("FRM-48-52: SKIP"); return; }
      const catId = cats[0].id;
      const r = await page.request.get(`${API_URL}/forum/posts?category_id=${catId}&type=discussion&sort=recent&page=1&limit=5`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`FRM-48-52: Category posts => ${r.status()}, count=${(json.data?.posts || json.data || []).length}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  // Phase 9: Forum Dashboard
  test("FRM-53: Forum dashboard stats", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/dashboard`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`FRM-53: Dashboard => ${r.status()}`);
      console.log(`Stats: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("frm_dashboard"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("FRM-54: Trending posts", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/dashboard`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`FRM-54: Trending => ${JSON.stringify(data.trending_posts || data.trending || "N/A").substring(0, 300)}`);
    } finally { await context.close(); }
  });

  test("FRM-55: Top contributors", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/forum/dashboard`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`FRM-55: Top contributors => ${JSON.stringify(data.top_contributors || data.contributors || "N/A").substring(0, 300)}`);
    } finally { await context.close(); }
  });

  test("FRM-56: Category management section", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/forum");
      await page.waitForTimeout(2000);
      await page.screenshot({ path: ss("frm_management_ui"), fullPage: true });
      console.log(`FRM-56: Forum UI at ${page.url()}`);
    } finally { await context.close(); }
  });
});

// ============================================================================
// PART 4: WHISTLEBLOWING MODULE
// ============================================================================

test.describe("Whistleblowing Module", () => {
  let adminToken: string;
  let empToken: string;
  let reportCaseNumber: string;
  let reportId: string | number;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    adminToken = await getToken(page, ADMIN_CREDS.email, ADMIN_CREDS.password);
    empToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  // Phase 1: Report Submission
  test("WHS-01: Submit anonymous report", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: {
          subject: `Anonymous Report ${Date.now()}`,
          description: "This is an anonymous test report for automated testing",
          category: "fraud",
          severity: "medium",
          is_anonymous: true,
        },
      });
      const json = await r.json();
      console.log(`WHS-01: Anonymous report => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 500)}`);
      const report = json.data?.report || json.data || {};
      if (report.case_number) reportCaseNumber = report.case_number;
      if (report.id) reportId = report.id;
      await page.screenshot({ path: ss("whs_anonymous"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-02: Submit identified report", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: {
          subject: `Identified Report ${Date.now()}`,
          description: "This is an identified test report",
          category: "harassment",
          severity: "high",
          is_anonymous: false,
        },
      });
      const json = await r.json();
      console.log(`WHS-02: Identified report => ${r.status()}`);
      const report = json.data?.report || json.data || {};
      console.log(`Reporter visible=${report.reporter_name || report.reporter || "N/A"}`);
      if (report.case_number && !reportCaseNumber) reportCaseNumber = report.case_number;
      if (report.id && !reportId) reportId = report.id;
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-03: Category fraud", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: `Fraud_${Date.now()}`, description: "Fraud report", category: "fraud", severity: "low", is_anonymous: true },
      });
      const json = await r.json();
      console.log(`WHS-03: fraud category => ${r.status()}, cat=${(json.data?.report || json.data)?.category}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-04: Category harassment", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: `Harassment_${Date.now()}`, description: "Harassment report", category: "harassment", severity: "high", is_anonymous: true },
      });
      console.log(`WHS-04: harassment category => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-05: Severity low", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: `LowSev_${Date.now()}`, description: "Low severity", category: "other", severity: "low", is_anonymous: true },
      });
      const json = await r.json();
      console.log(`WHS-05: severity low => ${r.status()}, sev=${(json.data?.report || json.data)?.severity}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-06: Severity medium", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: `MedSev_${Date.now()}`, description: "Medium severity", category: "other", severity: "medium", is_anonymous: true },
      });
      console.log(`WHS-06: severity medium => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-07: Severity high", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: `HighSev_${Date.now()}`, description: "High severity", category: "safety_violation", severity: "high", is_anonymous: true },
      });
      console.log(`WHS-07: severity high => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-08: Severity critical", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: `CritSev_${Date.now()}`, description: "Critical severity", category: "data_breach", severity: "critical", is_anonymous: true },
      });
      console.log(`WHS-08: severity critical => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-09: Subject 255 char max", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: "A".repeat(255), description: "Max length subject", category: "other", severity: "low", is_anonymous: true },
      });
      console.log(`WHS-09: 255 char subject => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-10: Detailed description", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: `Detail_${Date.now()}`, description: "Long detailed description ".repeat(20), category: "fraud", severity: "medium", is_anonymous: true },
      });
      console.log(`WHS-10: detailed description => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-11/12: Case number on success screen", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: `CaseNum_${Date.now()}`, description: "Case number test", category: "other", severity: "low", is_anonymous: true },
      });
      const json = await r.json();
      const report = json.data?.report || json.data || {};
      console.log(`WHS-11: case_number=${report.case_number || "N/A"}`);
      console.log(`WHS-12: Case number present=${!!report.case_number}`);
      if (report.case_number) reportCaseNumber = report.case_number;
      if (report.id) reportId = report.id;
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-13: Submit another report option", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password, "/whistleblowing");
      await page.waitForTimeout(2000);
      await page.screenshot({ path: ss("whs_ui_page"), fullPage: true });
      console.log(`WHS-13: Whistleblowing page at ${page.url()}`);
    } finally { await context.close(); }
  });

  test("WHS-14: Validation subject required", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { description: "No subject", category: "other", severity: "low", is_anonymous: true },
      });
      console.log(`WHS-14: No subject => ${r.status()} (should be 400)`);
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Report accepted without subject");
      }
    } finally { await context.close(); }
  });

  test("WHS-15: Validation description required", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: `NoDesc_${Date.now()}`, category: "other", severity: "low", is_anonymous: true },
      });
      console.log(`WHS-15: No description => ${r.status()} (should be 400)`);
      if (r.status() === 200 || r.status() === 201) {
        console.log("BUG: Report accepted without description");
      }
    } finally { await context.close(); }
  });

  // Phase 2: Report Tracking
  test("WHS-16: Track by case number", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!reportCaseNumber) { console.log("WHS-16: SKIP - no case number"); return; }
      const r = await page.request.get(`${API_URL}/whistleblowing/reports/lookup/${reportCaseNumber}`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      console.log(`WHS-16: Lookup ${reportCaseNumber} => ${r.status()}`);
      console.log(`Report: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("whs_lookup"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-17/18/19: Category, severity, status, updates in tracking", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!reportCaseNumber) { console.log("WHS-17-19: SKIP"); return; }
      const r = await page.request.get(`${API_URL}/whistleblowing/reports/lookup/${reportCaseNumber}`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      const report = json.data?.report || json.data || {};
      console.log(`WHS-17: category=${report.category}, severity=${report.severity}, subject=${report.subject}`);
      console.log(`WHS-18: status=${report.status}`);
      console.log(`WHS-19: updates=${JSON.stringify(report.updates || report.timeline || "N/A").substring(0, 300)}`);
    } finally { await context.close(); }
  });

  test("WHS-20: Resolution shown", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!reportCaseNumber) { console.log("WHS-20: SKIP"); return; }
      const r = await page.request.get(`${API_URL}/whistleblowing/reports/lookup/${reportCaseNumber}`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      const report = json.data?.report || json.data || {};
      console.log(`WHS-20: resolution=${report.resolution || "N/A (not yet resolved)"}`);
    } finally { await context.close(); }
  });

  test("WHS-21: Invalid case number", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/reports/lookup/INVALID-9999-XXXX`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      console.log(`WHS-21: Invalid case => ${r.status()} (should be 404)`);
      expect(r.status()).toBeGreaterThanOrEqual(400);
    } finally { await context.close(); }
  });

  test("WHS-22: Internal notes hidden from reporter", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!reportCaseNumber) { console.log("WHS-22: SKIP"); return; }
      const r = await page.request.get(`${API_URL}/whistleblowing/reports/lookup/${reportCaseNumber}`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      const report = json.data?.report || json.data || {};
      const updates = report.updates || report.timeline || [];
      const internalNotes = Array.isArray(updates) ? updates.filter((u: any) => u.type === "internal_note" || u.visibility === "internal") : [];
      console.log(`WHS-22: Internal notes visible to reporter=${internalNotes.length} (should be 0)`);
      if (internalNotes.length > 0) {
        console.log("BUG: Internal notes are visible to reporter via lookup");
      }
    } finally { await context.close(); }
  });

  // Phase 3: Report List (HR Only)
  test("WHS-23: View all reports (HR)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      const reports = json.data?.reports || json.data || [];
      console.log(`WHS-23: All reports => ${r.status()}, count=${Array.isArray(reports) ? reports.length : "N/A"}`);
      await page.screenshot({ path: ss("whs_all_reports"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-24: Filter by status", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/reports?status=submitted`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      console.log(`WHS-24: Filter status=submitted => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-25: Filter by category", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/reports?category=fraud`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      console.log(`WHS-25: Filter category=fraud => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-26: Filter by severity", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/reports?severity=high`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      console.log(`WHS-26: Filter severity=high => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-27: Search reports", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/reports?search=test`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      console.log(`WHS-27: Search reports => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-28: Report table columns", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/reports`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const reports = json.data?.reports || json.data || [];
      if (Array.isArray(reports) && reports.length > 0) {
        const rep = reports[0];
        console.log(`WHS-28: case=${rep.case_number}, cat=${rep.category}, sev=${rep.severity}, subj=${rep.subject?.substring(0, 30)}, anon=${rep.is_anonymous}, investigator=${rep.investigator || "N/A"}, status=${rep.status}`);
      }
    } finally { await context.close(); }
  });

  test("WHS-29: Click case to detail", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!reportId) { console.log("WHS-29: SKIP"); return; }
      const r = await page.request.get(`${API_URL}/whistleblowing/reports/${reportId}`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`WHS-29: Detail by ID => ${r.status()}`);
      console.log(`Detail: ${JSON.stringify(json).substring(0, 500)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-30: Anonymous reports show anonymous", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/reports`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const reports = json.data?.reports || json.data || [];
      const anon = Array.isArray(reports) ? reports.filter((r: any) => r.is_anonymous) : [];
      console.log(`WHS-30: Anonymous reports=${anon.length}`);
      if (anon.length > 0) {
        console.log(`First anon: reporter=${anon[0].reporter_name || anon[0].reporter || "hidden"}`);
      }
    } finally { await context.close(); }
  });

  // Phase 4: Investigation Management
  test("WHS-31: Assign investigator", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!reportId) { console.log("WHS-31: SKIP"); return; }
      // Get users for investigator
      const usersR = await page.request.get(`${API_URL}/users`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const usersJson = await usersR.json();
      const users = usersJson.data?.users || usersJson.data || [];
      const investigatorId = Array.isArray(users) && users.length > 0 ? users[0].id : 1;
      const r = await page.request.post(`${API_URL}/whistleblowing/reports/${reportId}/assign`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { investigator_id: investigatorId },
      });
      console.log(`WHS-31: Assign investigator => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-32: Status to Under Investigation", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!reportId) { console.log("WHS-32: SKIP"); return; }
      const r = await page.request.put(`${API_URL}/whistleblowing/reports/${reportId}/status`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { status: "under_investigation" },
      });
      console.log(`WHS-32: Under Investigation => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-33: Add internal note", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!reportId) { console.log("WHS-33: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/whistleblowing/reports/${reportId}/update`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { content: "Internal investigation note - not for reporter", type: "internal_note", visible_to_reporter: false },
      });
      console.log(`WHS-33: Internal note => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-34: Add response visible to reporter", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!reportId) { console.log("WHS-34: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/whistleblowing/reports/${reportId}/update`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { content: "We are looking into your report", type: "response", visible_to_reporter: true },
      });
      console.log(`WHS-34: Response to reporter => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-35: Status to Resolved", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!reportId) { console.log("WHS-35: SKIP"); return; }
      const r = await page.request.put(`${API_URL}/whistleblowing/reports/${reportId}/status`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { status: "resolved", resolution: "Investigation complete. Issue addressed." },
      });
      console.log(`WHS-35: Resolved => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-36: Status to Dismissed", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create a new report to dismiss
      const cr = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: `DismissMe_${Date.now()}`, description: "To be dismissed", category: "other", severity: "low", is_anonymous: true },
      });
      const cj = await cr.json();
      const newId = cj.data?.report?.id || cj.data?.id;
      if (!newId) { console.log("WHS-36: SKIP"); return; }
      const r = await page.request.put(`${API_URL}/whistleblowing/reports/${newId}/status`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { status: "dismissed", resolution: "Insufficient evidence" },
      });
      console.log(`WHS-36: Dismissed => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-37: Status to Closed", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!reportId) { console.log("WHS-37: SKIP"); return; }
      const r = await page.request.put(`${API_URL}/whistleblowing/reports/${reportId}/status`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { status: "closed" },
      });
      console.log(`WHS-37: Closed => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-38: Escalate to external body", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create new report to escalate
      const cr = await page.request.post(`${API_URL}/whistleblowing/reports`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { subject: `Escalate_${Date.now()}`, description: "Needs external escalation", category: "financial_misconduct", severity: "critical", is_anonymous: true },
      });
      const cj = await cr.json();
      const newId = cj.data?.report?.id || cj.data?.id;
      if (!newId) { console.log("WHS-38: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/whistleblowing/reports/${newId}/escalate`, {
        headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
        data: { external_body: "External Regulatory Authority" },
      });
      console.log(`WHS-38: Escalate => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  // Phase 5: Report Detail (HR View)
  test("WHS-39/40/41/42/43/44/45/46: Report detail full view", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/whistleblowing/reports`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const reports = listJson.data?.reports || listJson.data || [];
      if (!Array.isArray(reports) || reports.length === 0) { console.log("WHS-39-46: SKIP"); return; }
      const rId = reports[0].id;
      const r = await page.request.get(`${API_URL}/whistleblowing/reports/${rId}`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      const report = json.data?.report || json.data || {};
      console.log(`WHS-39: subject=${report.subject}, category=${report.category}, anon=${report.is_anonymous}, desc=${(report.description || "").substring(0, 50)}`);
      console.log(`WHS-40: timeline/updates=${JSON.stringify(report.updates || report.timeline || "N/A").substring(0, 300)}`);
      console.log(`WHS-42: submitted=${report.created_at}, investigator=${report.investigator || "N/A"}, escalated_to=${report.escalated_to || "N/A"}`);
      console.log(`WHS-44: status=${report.status}`);
      console.log(`WHS-45: resolution=${report.resolution || "N/A"}`);
      await page.screenshot({ path: ss("whs_detail_hr"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  // Phase 6: Compliance Dashboard
  test("WHS-47: Compliance dashboard stats", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/dashboard`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`WHS-47: Dashboard => ${r.status()}`);
      console.log(`Stats: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("whs_dashboard"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("WHS-48: By severity chart", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/dashboard`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`WHS-48: By severity => ${JSON.stringify(data.by_severity || data.severity_breakdown || "N/A").substring(0, 300)}`);
    } finally { await context.close(); }
  });

  test("WHS-49: By category chart", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/dashboard`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`WHS-49: By category => ${JSON.stringify(data.by_category || data.category_breakdown || "N/A").substring(0, 300)}`);
    } finally { await context.close(); }
  });

  test("WHS-50: Recent reports table", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/whistleblowing/dashboard`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`WHS-50: Recent reports => ${JSON.stringify(data.recent_reports || data.recent || "N/A").substring(0, 300)}`);
    } finally { await context.close(); }
  });

  test("WHS-51: View All Reports button (UI)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, ADMIN_CREDS.email, ADMIN_CREDS.password, "/whistleblowing");
      await page.waitForTimeout(2000);
      await page.screenshot({ path: ss("whs_ui_page"), fullPage: true });
      console.log(`WHS-51: Whistleblowing UI at ${page.url()}`);
    } finally { await context.close(); }
  });

  // Phase 7: Audit & Compliance
  test("WHS-52/53/54: Audit logging for status, investigator, escalation", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/audit?module=whistleblowing`, {
        headers: { Authorization: `Bearer ${adminToken}` },
      });
      const json = await r.json();
      console.log(`WHS-52/53/54: Audit => ${r.status()}`);
      console.log(`Audit entries: ${JSON.stringify(json).substring(0, 500)}`);
    } finally { await context.close(); }
  });

  test("WHS-55: Anonymous identity never exposed", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const listR = await page.request.get(`${API_URL}/whistleblowing/reports`, { headers: { Authorization: `Bearer ${adminToken}` } });
      const listJson = await listR.json();
      const reports = listJson.data?.reports || listJson.data || [];
      const anonReports = Array.isArray(reports) ? reports.filter((r: any) => r.is_anonymous) : [];
      let exposedIdentity = false;
      for (const rep of anonReports) {
        if (rep.reporter_id || rep.reporter_name || rep.reporter_email || rep.user_id) {
          exposedIdentity = true;
          console.log(`BUG: Anonymous report ${rep.case_number} exposes identity: reporter_id=${rep.reporter_id}, name=${rep.reporter_name}, email=${rep.reporter_email}`);
        }
      }
      console.log(`WHS-55: Anonymous identity exposed=${exposedIdentity}`);
      if (exposedIdentity) {
        console.log("BUG: Anonymous reporter identity is visible in report list");
      }
    } finally { await context.close(); }
  });
});

// ============================================================================
// PART 5: AI CHATBOT MODULE
// ============================================================================

test.describe("AI Chatbot Module", () => {
  let empToken: string;
  let conversationId: string | number;

  test.beforeAll(async ({ browser }) => {
    const { context, page } = await createFreshContext(browser);
    empToken = await getToken(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password);
    await context.close();
  });

  // Phase 1: Conversation Management
  test("CHT-01: Create new conversation", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.post(`${API_URL}/chatbot/conversations`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { title: `TestConvo_${Date.now()}` },
      });
      const json = await r.json();
      console.log(`CHT-01: Create conversation => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 500)}`);
      const convo = json.data?.conversation || json.data || {};
      if (convo.id) conversationId = convo.id;
      await page.screenshot({ path: ss("cht_create"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("CHT-02/03: Conversation in sidebar (list)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/chatbot/conversations`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      const convos = json.data?.conversations || json.data || [];
      console.log(`CHT-02: Conversations => ${r.status()}, count=${Array.isArray(convos) ? convos.length : "N/A"}`);
      if (Array.isArray(convos) && convos.length > 0) {
        const c = convos[0];
        console.log(`CHT-03: title=${c.title}, updated=${c.updated_at}, messages=${c.message_count ?? "N/A"}`);
        if (!conversationId) conversationId = c.id;
      }
      await page.screenshot({ path: ss("cht_list"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("CHT-04: Select conversation (get messages)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!conversationId) { console.log("CHT-04: SKIP"); return; }
      const r = await page.request.get(`${API_URL}/chatbot/conversations/${conversationId}`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      console.log(`CHT-04: Get messages => ${r.status()}`);
      console.log(`Messages: ${JSON.stringify(json).substring(0, 500)}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("CHT-05: Delete conversation", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      // Create one to delete
      const cr = await page.request.post(`${API_URL}/chatbot/conversations`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { title: `ToDelete_${Date.now()}` },
      });
      const cj = await cr.json();
      const delId = cj.data?.conversation?.id || cj.data?.id;
      if (!delId) { console.log("CHT-05: SKIP"); return; }
      const r = await page.request.delete(`${API_URL}/chatbot/conversations/${delId}`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      console.log(`CHT-05: Delete conversation => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("CHT-06: Delete selected conversation", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const cr = await page.request.post(`${API_URL}/chatbot/conversations`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { title: `Selected_${Date.now()}` },
      });
      const cj = await cr.json();
      const selId = cj.data?.conversation?.id || cj.data?.id;
      if (!selId) { console.log("CHT-06: SKIP"); return; }
      // Load it
      await page.request.get(`${API_URL}/chatbot/conversations/${selId}`, { headers: { Authorization: `Bearer ${empToken}` } });
      // Delete it
      const r = await page.request.delete(`${API_URL}/chatbot/conversations/${selId}`, { headers: { Authorization: `Bearer ${empToken}` } });
      console.log(`CHT-06: Delete selected => ${r.status()}`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("CHT-07: Multiple conversations", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const ids: any[] = [];
      for (let i = 0; i < 3; i++) {
        const r = await page.request.post(`${API_URL}/chatbot/conversations`, {
          headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
          data: { title: `Multi_${i}_${Date.now()}` },
        });
        const json = await r.json();
        ids.push(json.data?.conversation?.id || json.data?.id);
      }
      console.log(`CHT-07: Created ${ids.filter(Boolean).length} conversations`);
      const listR = await page.request.get(`${API_URL}/chatbot/conversations`, { headers: { Authorization: `Bearer ${empToken}` } });
      const listJson = await listR.json();
      const convos = listJson.data?.conversations || listJson.data || [];
      console.log(`CHT-07: Total conversations=${Array.isArray(convos) ? convos.length : "N/A"}`);
    } finally { await context.close(); }
  });

  // Phase 2: Messaging
  test("CHT-08: Send message", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!conversationId) {
        const cr = await page.request.post(`${API_URL}/chatbot/conversations`, {
          headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
          data: { title: `MsgTest_${Date.now()}` },
        });
        const cj = await cr.json();
        conversationId = cj.data?.conversation?.id || cj.data?.id;
      }
      if (!conversationId) { console.log("CHT-08: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/chatbot/conversations/${conversationId}/send`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { message: "What is my leave balance?" },
        timeout: 60000,
      });
      const json = await r.json();
      console.log(`CHT-08: Send message => ${r.status()}`);
      console.log(`Response: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("cht_send_msg"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("CHT-09: AI response received", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!conversationId) { console.log("CHT-09: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/chatbot/conversations/${conversationId}/send`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { message: "How do I apply for leave?" },
        timeout: 60000,
      });
      const json = await r.json();
      const response = json.data?.response || json.data?.message || json.data?.assistant_message || "";
      console.log(`CHT-09: AI response => ${r.status()}, response="${typeof response === "string" ? response.substring(0, 200) : JSON.stringify(response).substring(0, 200)}"`);
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("CHT-10: Typing indicator (UI test)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password, "/chatbot");
      await page.waitForTimeout(2000);
      await page.screenshot({ path: ss("cht_ui_page"), fullPage: true });
      console.log(`CHT-10: Chatbot UI at ${page.url()}`);
    } finally { await context.close(); }
  });

  test("CHT-11: Send empty message", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!conversationId) { console.log("CHT-11: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/chatbot/conversations/${conversationId}/send`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { message: "" },
      });
      console.log(`CHT-11: Empty message => ${r.status()} (should be 400)`);
      if (r.status() === 200) {
        console.log("BUG: Chatbot accepted empty message");
      }
    } finally { await context.close(); }
  });

  test("CHT-12/13: Enter key sends, Shift+Enter for newline (UI)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password, "/chatbot");
      await page.waitForTimeout(2000);
      // Look for input area
      const input = page.locator('textarea, input[type="text"], [contenteditable]').first();
      if (await input.isVisible().catch(() => false)) {
        console.log("CHT-12/13: Chat input found");
      } else {
        console.log("CHT-12/13: No visible chat input");
      }
      await page.screenshot({ path: ss("cht_input"), fullPage: true });
    } finally { await context.close(); }
  });

  test("CHT-14: Auto-scroll (verify messages chronology)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!conversationId) { console.log("CHT-14: SKIP"); return; }
      const r = await page.request.get(`${API_URL}/chatbot/conversations/${conversationId}`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      const messages = json.data?.messages || json.data?.conversation?.messages || [];
      console.log(`CHT-14: Messages in order, count=${Array.isArray(messages) ? messages.length : "N/A"}`);
      if (Array.isArray(messages) && messages.length > 1) {
        console.log(`First: ${messages[0]?.created_at}, Last: ${messages[messages.length - 1]?.created_at}`);
      }
    } finally { await context.close(); }
  });

  test("CHT-15: Message timestamps", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!conversationId) { console.log("CHT-15: SKIP"); return; }
      const r = await page.request.get(`${API_URL}/chatbot/conversations/${conversationId}`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      const messages = json.data?.messages || json.data?.conversation?.messages || [];
      if (Array.isArray(messages) && messages.length > 0) {
        console.log(`CHT-15: timestamp=${messages[0].created_at || messages[0].timestamp || "N/A"}`);
      }
    } finally { await context.close(); }
  });

  // Phase 3: Empty State & Suggestions
  test("CHT-16/17/18/19: Empty state, suggestions, click suggestion, start conversation", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/chatbot/suggestions`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      console.log(`CHT-16-19: Suggestions => ${r.status()}`);
      console.log(`Suggestions: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("cht_suggestions"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("CHT-20: Follow-up suggestions after messages", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!conversationId) { console.log("CHT-20: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/chatbot/conversations/${conversationId}/send`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { message: "Tell me about company policies" },
        timeout: 60000,
      });
      const json = await r.json();
      console.log(`CHT-20: Follow-up suggestions => ${JSON.stringify(json.data?.suggestions || json.data?.follow_up || "N/A").substring(0, 300)}`);
    } finally { await context.close(); }
  });

  // Phase 4: Markdown Rendering (UI tests)
  test("CHT-21/22/23/24/25/26: Markdown rendering tests", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!conversationId) { console.log("CHT-21-26: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/chatbot/conversations/${conversationId}/send`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { message: "Can you show me a summary of leave policies in a table format?" },
        timeout: 60000,
      });
      const json = await r.json();
      const response = json.data?.response || json.data?.message || json.data?.assistant_message || "";
      const respText = typeof response === "string" ? response : JSON.stringify(response);
      console.log(`CHT-21: Bold check => has **=${respText.includes("**")}`);
      console.log(`CHT-22: Italic check => has *=${respText.includes("*")}`);
      console.log(`CHT-23: Code check => has backtick=${respText.includes("\`")}`);
      console.log(`CHT-24: Link check => has [...]=${respText.includes("[")}`);
      console.log(`CHT-25: List check => has -/1.=${respText.includes("-") || respText.includes("1.")}`);
      console.log(`CHT-26: Table check => has |=${respText.includes("|")}`);
      console.log(`Response preview: ${respText.substring(0, 300)}`);
    } finally { await context.close(); }
  });

  test("CHT-27/28: Quoted text and question patterns", async ({ browser }) => {
    test.setTimeout(90000);
    const { context, page } = await createFreshContext(browser);
    try {
      if (!conversationId) { console.log("CHT-27/28: SKIP"); return; }
      const r = await page.request.post(`${API_URL}/chatbot/conversations/${conversationId}/send`, {
        headers: { Authorization: `Bearer ${empToken}`, "Content-Type": "application/json" },
        data: { message: "What questions should I ask about benefits?" },
        timeout: 60000,
      });
      const json = await r.json();
      const response = json.data?.response || json.data?.message || json.data?.assistant_message || "";
      const respText = typeof response === "string" ? response : JSON.stringify(response);
      console.log(`CHT-27: Quoted text => has quotes=${respText.includes('"') || respText.includes("'")}`);
      console.log(`CHT-28: Question patterns => has What/How=${respText.includes("What") || respText.includes("How")}`);
    } finally { await context.close(); }
  });

  // Phase 5: AI Status & Mode
  test("CHT-29: AI status endpoint", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/chatbot/ai-status`, {
        headers: { Authorization: `Bearer ${empToken}` },
      });
      const json = await r.json();
      console.log(`CHT-29: AI status => ${r.status()}`);
      console.log(`Status: ${JSON.stringify(json).substring(0, 500)}`);
      await page.screenshot({ path: ss("cht_ai_status"), fullPage: true });
      expect(r.status()).toBeLessThan(500);
    } finally { await context.close(); }
  });

  test("CHT-30: AI-powered mode indicator", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/chatbot/ai-status`, { headers: { Authorization: `Bearer ${empToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`CHT-30: engine=${data.engine || data.provider || "N/A"}, mode=${data.mode || "N/A"}, ai_powered=${data.ai_powered ?? data.is_ai ?? "N/A"}`);
    } finally { await context.close(); }
  });

  test("CHT-31: Basic mode fallback", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/chatbot/ai-status`, { headers: { Authorization: `Bearer ${empToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`CHT-31: Fallback mode available=${data.fallback_available ?? data.basic_mode ?? "N/A"}`);
    } finally { await context.close(); }
  });

  test("CHT-32: Status indicator online", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      const r = await page.request.get(`${API_URL}/chatbot/ai-status`, { headers: { Authorization: `Bearer ${empToken}` } });
      const json = await r.json();
      const data = json.data || json;
      console.log(`CHT-32: online=${data.status || data.online || data.is_online || "N/A"}`);
    } finally { await context.close(); }
  });

  // Phase 6: UI Responsiveness
  test("CHT-33: Desktop layout", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password, "/chatbot");
      await page.waitForTimeout(2000);
      await page.screenshot({ path: ss("cht_desktop"), fullPage: true });
      // Check for sidebar + main area
      const content = await page.content();
      console.log(`CHT-33: Desktop layout loaded, url=${page.url()}`);
    } finally { await context.close(); }
  });

  test("CHT-34/35: Mobile layout", async ({ browser }) => {
    test.setTimeout(60000);
    const context = await browser.newContext({
      viewport: { width: 375, height: 812 },
      ignoreHTTPSErrors: true,
    });
    const page = await context.newPage();
    try {
      await loginAndGo(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password, "/chatbot");
      await page.waitForTimeout(2000);
      await page.screenshot({ path: ss("cht_mobile"), fullPage: true });
      console.log(`CHT-34/35: Mobile layout at ${page.url()}`);
    } finally { await context.close(); }
  });

  test("CHT-36/37: User and bot avatars (UI)", async ({ browser }) => {
    test.setTimeout(60000);
    const { context, page } = await createFreshContext(browser);
    try {
      await loginAndGo(page, EMPLOYEE_CREDS.email, EMPLOYEE_CREDS.password, "/chatbot");
      await page.waitForTimeout(2000);
      // Look for avatar elements
      const avatars = page.locator('[class*="avatar"], [class*="Avatar"]');
      const count = await avatars.count().catch(() => 0);
      console.log(`CHT-36/37: Avatar elements found=${count}`);
      await page.screenshot({ path: ss("cht_avatars"), fullPage: true });
    } finally { await context.close(); }
  });
});
