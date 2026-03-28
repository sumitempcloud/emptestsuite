"""
Multi-Tenant Isolation E2E Test
===============================
Verifies that TechNova (org 5) and GlobalTech (org 9) cannot see or
manipulate each other's data across all major API endpoints.

Tested endpoints:
  - Users / Employees
  - Leave
  - Documents
  - Announcements
  - Assets
  - Events
  - Surveys
  - Tickets
  - Forum
  - Positions
  - Cross-org manipulation (update, delete, approve)
"""

import requests
import json
import sys
from dataclasses import dataclass, field
from typing import Optional

BASE = "https://test-empcloud-api.empcloud.com/api/v1"

# ── credentials ───────────────────────────────────────────────────────
TENANTS = {
    "TechNova": {"email": "ananya@technova.in", "password": "Welcome@123", "org_id": 5},
    "GlobalTech": {"email": "john@globaltech.com", "password": "Welcome@123", "org_id": 9},
}


# ── helpers ───────────────────────────────────────────────────────────
@dataclass
class Result:
    name: str
    passed: bool
    detail: str = ""


results: list[Result] = []


def record(name: str, passed: bool, detail: str = ""):
    tag = "PASS" if passed else "FAIL"
    results.append(Result(name, passed, detail))
    print(f"  [{tag}] {name}" + (f"  -- {detail}" if detail else ""))


def login(email: str, password: str) -> Optional[str]:
    """Return bearer token or None."""
    for path in ["/auth/login", "/login", "/auth/signin"]:
        try:
            r = requests.post(
                BASE + path,
                json={"email": email, "password": password},
                timeout=30,
            )
            if r.status_code in (200, 201):
                body = r.json()
                # Try common token locations
                for key_path in [
                    lambda b: b.get("token"),
                    lambda b: b.get("data", {}).get("token"),
                    lambda b: b.get("access_token"),
                    lambda b: b.get("data", {}).get("access_token"),
                    lambda b: b.get("data", {}).get("accessToken"),
                    lambda b: b.get("accessToken"),
                    lambda b: b.get("data", {}).get("tokens", {}).get("access_token"),
                    lambda b: b.get("data", {}).get("tokens", {}).get("token"),
                ]:
                    tok = key_path(body)
                    if tok:
                        return tok
        except Exception:
            continue
    return None


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def safe_get(url: str, headers: dict, params: dict = None) -> requests.Response:
    return requests.get(url, headers=headers, params=params or {}, timeout=30)


def safe_post(url: str, headers: dict, json_body: dict = None) -> requests.Response:
    return requests.post(url, headers=headers, json=json_body or {}, timeout=30)


def safe_put(url: str, headers: dict, json_body: dict = None) -> requests.Response:
    return requests.put(url, headers=headers, json=json_body or {}, timeout=30)


def safe_patch(url: str, headers: dict, json_body: dict = None) -> requests.Response:
    return requests.patch(url, headers=headers, json=json_body or {}, timeout=30)


def safe_delete(url: str, headers: dict) -> requests.Response:
    return requests.delete(url, headers=headers, timeout=30)


def extract_items(resp: requests.Response) -> list:
    """Best-effort extraction of list items from various response shapes."""
    if resp.status_code not in (200, 201):
        return []
    try:
        body = resp.json()
    except Exception:
        return []
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for key in ["data", "results", "items", "records", "rows", "list"]:
            val = body.get(key)
            if isinstance(val, list):
                return val
            if isinstance(val, dict):
                # nested: data.items, data.results, etc.
                for inner in ["items", "results", "rows", "records", "list", "data"]:
                    inner_val = val.get(inner)
                    if isinstance(inner_val, list):
                        return inner_val
    return []


def extract_ids(items: list) -> list:
    """Pull id / _id from a list of dicts."""
    ids = []
    for item in items:
        if isinstance(item, dict):
            for k in ["id", "_id", "ID"]:
                if k in item:
                    ids.append(item[k])
                    break
    return ids


def org_of(item: dict) -> Optional[int]:
    """Try to extract org/organization id from an item."""
    for k in ["organization_id", "org_id", "organisationId", "organizationId", "orgId", "org"]:
        val = item.get(k)
        if val is not None:
            try:
                return int(val)
            except (ValueError, TypeError):
                pass
    return None


# ── endpoint catalogue ────────────────────────────────────────────────
# (label, GET-list path, singular noun for cross-org tests)
LIST_ENDPOINTS = [
    ("Users",         ["/users", "/employees"]),
    ("Leave",         ["/leave/applications"]),
    ("Documents",     ["/documents"]),
    ("Announcements", ["/announcements"]),
    ("Assets",        ["/assets"]),
    ("Events",        ["/events"]),
    ("Surveys",       ["/surveys"]),
    ("Tickets",       ["/helpdesk/tickets"]),
    ("Forum",         ["/forum/posts"]),
    ("Positions",     ["/positions"]),
]


def discover_working_path(token: str, paths: list[str]) -> Optional[str]:
    """Return the first path that gives 2xx."""
    hdr = auth_header(token)
    for p in paths:
        try:
            r = safe_get(BASE + p, hdr)
            if r.status_code in (200, 201):
                return p
        except Exception:
            continue
    return None


# ══════════════════════════════════════════════════════════════════════
#  MAIN TEST LOGIC
# ══════════════════════════════════════════════════════════════════════
def main():
    print("=" * 70)
    print("  MULTI-TENANT ISOLATION TEST")
    print("=" * 70)

    # ── 1. Login both tenants ─────────────────────────────────────────
    print("\n[1] Authenticating tenants...")
    tokens = {}
    for name, creds in TENANTS.items():
        tok = login(creds["email"], creds["password"])
        if tok:
            tokens[name] = tok
            print(f"  {name}: authenticated OK")
        else:
            print(f"  {name}: FAILED to authenticate — aborting")
            sys.exit(1)

    tn_hdr = auth_header(tokens["TechNova"])
    gt_hdr = auth_header(tokens["GlobalTech"])
    tn_org = TENANTS["TechNova"]["org_id"]
    gt_org = TENANTS["GlobalTech"]["org_id"]

    # ── 2. Discover working paths for each endpoint ───────────────────
    print("\n[2] Discovering endpoint paths...")
    working: dict[str, str] = {}  # label -> path
    for label, candidates in LIST_ENDPOINTS:
        path = discover_working_path(tokens["TechNova"], candidates)
        if path:
            working[label] = path
            print(f"  {label}: {path}")
        else:
            print(f"  {label}: no working path found (skipped)")

    # ── 3. Read isolation — each tenant lists data, confirm no cross-org leak
    print("\n[3] READ ISOLATION — listing data per tenant, checking org boundaries...")
    # Store IDs for cross-org manipulation tests later
    tenant_ids: dict[str, dict[str, list]] = {"TechNova": {}, "GlobalTech": {}}

    for label, path in working.items():
        # TechNova listing
        tn_resp = safe_get(BASE + path, tn_hdr)
        tn_items = extract_items(tn_resp)

        # GlobalTech listing
        gt_resp = safe_get(BASE + path, gt_hdr)
        gt_items = extract_items(gt_resp)

        tenant_ids["TechNova"][label] = extract_ids(tn_items)
        tenant_ids["GlobalTech"][label] = extract_ids(gt_items)

        # Check that TechNova items don't contain GlobalTech org
        tn_leaked = [it for it in tn_items if org_of(it) == gt_org]
        gt_leaked = [it for it in gt_items if org_of(it) == tn_org]

        # Also check ID overlap — if both have IDs, they should be disjoint
        tn_id_set = set(map(str, tenant_ids["TechNova"][label]))
        gt_id_set = set(map(str, tenant_ids["GlobalTech"][label]))
        id_overlap = tn_id_set & gt_id_set

        if tn_leaked:
            record(
                f"Read isolation: {label} — TechNova sees GlobalTech data",
                False,
                f"{len(tn_leaked)} leaked items with org={gt_org}",
            )
        elif gt_leaked:
            record(
                f"Read isolation: {label} — GlobalTech sees TechNova data",
                False,
                f"{len(gt_leaked)} leaked items with org={tn_org}",
            )
        elif id_overlap and len(tn_items) > 0 and len(gt_items) > 0:
            # Overlapping IDs could indicate shared data (or just auto-increment collision).
            # Flag only if the items actually look identical.
            record(
                f"Read isolation: {label} — overlapping IDs",
                False,
                f"Shared IDs: {list(id_overlap)[:5]}",
            )
        else:
            record(
                f"Read isolation: {label}",
                True,
                f"TechNova={len(tn_items)} items, GlobalTech={len(gt_items)} items, no cross-org leak",
            )

    # ── 4. Direct-access isolation — tenant A tries to GET tenant B's specific resource
    print("\n[4] DIRECT ACCESS ISOLATION — fetching other tenant's resources by ID...")
    for label, path in working.items():
        # GlobalTech tries to access TechNova IDs
        for rid in tenant_ids["TechNova"].get(label, [])[:3]:
            url = f"{BASE}{path}/{rid}"
            r = safe_get(url, gt_hdr)
            items = extract_items(r) if r.status_code in (200, 201) else []
            body = {}
            try:
                body = r.json()
            except Exception:
                pass

            # Check if the response actually contains the resource
            is_blocked = r.status_code in (403, 404, 401, 400)
            if not is_blocked and r.status_code in (200, 201):
                # Check if the data belongs to the wrong org
                data = body.get("data", body)
                if isinstance(data, dict) and org_of(data) == tn_org:
                    is_blocked = False  # truly leaked
                elif isinstance(data, dict) and not data:
                    is_blocked = True  # empty = blocked
                else:
                    # Could be empty or belongs to correct org — treat as OK if empty
                    if not data or data == {}:
                        is_blocked = True

            record(
                f"Direct access: GlobalTech -> TechNova {label} id={rid}",
                is_blocked,
                f"status={r.status_code}" + (" LEAKED" if not is_blocked else " blocked"),
            )
            break  # one ID per endpoint is enough

        # TechNova tries to access GlobalTech IDs
        for rid in tenant_ids["GlobalTech"].get(label, [])[:3]:
            url = f"{BASE}{path}/{rid}"
            r = safe_get(url, tn_hdr)
            body = {}
            try:
                body = r.json()
            except Exception:
                pass
            is_blocked = r.status_code in (403, 404, 401, 400)
            if not is_blocked and r.status_code in (200, 201):
                data = body.get("data", body)
                if isinstance(data, dict) and org_of(data) == gt_org:
                    is_blocked = False
                elif isinstance(data, dict) and not data:
                    is_blocked = True
                else:
                    if not data or data == {}:
                        is_blocked = True

            record(
                f"Direct access: TechNova -> GlobalTech {label} id={rid}",
                is_blocked,
                f"status={r.status_code}" + (" LEAKED" if not is_blocked else " blocked"),
            )
            break

    # ── 5. Cross-org MUTATION — try to update/delete/approve other tenant's resources
    print("\n[5] CROSS-ORG MUTATION — attempting update/delete/approve on other tenant's data...")

    mutation_tests = [
        # (label, method, path_template, body)
        ("Update", "PUT", None, {"name": "HACKED", "title": "HACKED", "status": "hacked"}),
        ("Patch", "PATCH", None, {"status": "approved", "name": "HACKED"}),
        ("Delete", "DELETE", None, None),
    ]

    for label, path in working.items():
        # GlobalTech tries to mutate TechNova resources
        for rid in tenant_ids["TechNova"].get(label, [])[:1]:
            url = f"{BASE}{path}/{rid}"

            # PUT / update
            r = safe_put(url, gt_hdr, {"name": "HACKED", "title": "HACKED"})
            is_blocked = r.status_code in (403, 404, 401, 400, 405)
            record(
                f"Cross-org UPDATE: GlobalTech -> TechNova {label} id={rid}",
                is_blocked,
                f"status={r.status_code}",
            )

            # PATCH
            r = safe_patch(url, gt_hdr, {"status": "approved"})
            is_blocked = r.status_code in (403, 404, 401, 400, 405)
            record(
                f"Cross-org PATCH: GlobalTech -> TechNova {label} id={rid}",
                is_blocked,
                f"status={r.status_code}",
            )

            # DELETE
            r = safe_delete(url, gt_hdr)
            is_blocked = r.status_code in (403, 404, 401, 400, 405)
            record(
                f"Cross-org DELETE: GlobalTech -> TechNova {label} id={rid}",
                is_blocked,
                f"status={r.status_code}",
            )

        # TechNova tries to mutate GlobalTech resources
        for rid in tenant_ids["GlobalTech"].get(label, [])[:1]:
            url = f"{BASE}{path}/{rid}"

            r = safe_put(url, tn_hdr, {"name": "HACKED", "title": "HACKED"})
            is_blocked = r.status_code in (403, 404, 401, 400, 405)
            record(
                f"Cross-org UPDATE: TechNova -> GlobalTech {label} id={rid}",
                is_blocked,
                f"status={r.status_code}",
            )

            r = safe_patch(url, tn_hdr, {"status": "approved"})
            is_blocked = r.status_code in (403, 404, 401, 400, 405)
            record(
                f"Cross-org PATCH: TechNova -> GlobalTech {label} id={rid}",
                is_blocked,
                f"status={r.status_code}",
            )

            r = safe_delete(url, tn_hdr)
            is_blocked = r.status_code in (403, 404, 401, 400, 405)
            record(
                f"Cross-org DELETE: TechNova -> GlobalTech {label} id={rid}",
                is_blocked,
                f"status={r.status_code}",
            )

    # ── 6. Leave-specific: approve/reject other org's leave ───────────
    print("\n[6] LEAVE-SPECIFIC — cross-org approve/reject...")
    if "Leave" in working:
        leave_path = working["Leave"]
        for rid in tenant_ids["TechNova"].get("Leave", [])[:1]:
            for action in ["approve", "reject"]:
                for suffix in [f"/{rid}/{action}", f"/{rid}/status"]:
                    url = BASE + leave_path + suffix
                    r = safe_post(url, gt_hdr, {"status": action + "d"})
                    is_blocked = r.status_code in (403, 404, 401, 400, 405)
                    r2 = safe_patch(url, gt_hdr, {"status": action + "d"})
                    is_blocked2 = r2.status_code in (403, 404, 401, 400, 405)
                    record(
                        f"Leave {action}: GlobalTech -> TechNova leave id={rid} ({suffix})",
                        is_blocked and is_blocked2,
                        f"POST={r.status_code}, PATCH={r2.status_code}",
                    )
                    break  # only first suffix pattern

    # ── 7. Ticket-specific: cross-org status change ───────────────────
    print("\n[7] TICKET-SPECIFIC — cross-org status change...")
    if "Tickets" in working:
        ticket_path = working["Tickets"]
        for rid in tenant_ids["TechNova"].get("Tickets", [])[:1]:
            url = f"{BASE}{ticket_path}/{rid}"
            r = safe_patch(url, gt_hdr, {"status": "closed"})
            is_blocked = r.status_code in (403, 404, 401, 400, 405)
            record(
                f"Ticket close: GlobalTech -> TechNova ticket id={rid}",
                is_blocked,
                f"status={r.status_code}",
            )

    # ══════════════════════════════════════════════════════════════════
    #  SUMMARY
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    print(f"  Total: {total}  |  Passed: {passed}  |  Failed: {failed}")

    if failed:
        print(f"\n  FAILURES ({failed}):")
        for r in results:
            if not r.passed:
                print(f"    [FAIL] {r.name}  -- {r.detail}")

    print()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
