"""Post-deploy smoke test (P0.1): kick off the LIVE pipeline and assert a report.

The broken 2026-06-04 revision returned 200 on health checks but 500 on /run
(missing ``firecrawl``). This asserts the full pipeline runs end-to-end and
produces a non-empty report — the check that revision lacked.

The full pipeline takes minutes (TOP_N candidates + the Pro synthesis), so
holding a single HTTP connection open is fragile (proxies / egress sever long
connections). Instead this FIRES /run and then POLLS the session state with
short requests until the report appears — robust to long runtimes and to
connection limits. (The server completes the run even if the firing connection
drops.)

Usage:
    uv run python scripts/smoke.py [BASE_URL]

Exit 0 = ok, non-zero = smoke failed.
"""

from __future__ import annotations

import sys
import time
import uuid

import httpx

DEFAULT_URL = "https://startup-diagnostics-PROJECT_NUMBER.europe-west1.run.app"
APP = "agents"
THESIS = "Busco startups de inteligencia artificial, etapa seed, ámbito global."
POLL_BUDGET_S = 420
POLL_EVERY_S = 15


def main() -> int:
    base = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL).rstrip("/")
    user = "smoke"
    session = f"smoke-{uuid.uuid4().hex[:8]}"

    with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
        r = client.post(f"{base}/apps/{APP}/users/{user}/sessions/{session}", json={})
        if r.status_code not in (200, 201):
            print(f"SMOKE FAIL: create session -> {r.status_code}: {r.text[:300]}")
            return 1

        body = {
            "app_name": APP,
            "user_id": user,
            "session_id": session,
            "new_message": {"role": "user", "parts": [{"text": THESIS}]},
            "streaming": False,
        }
        # Fire the run. We don't hold the (multi-minute) connection — the server
        # completes it regardless; a short-timeout drop here is expected.
        try:
            client.post(f"{base}/run", json=body, timeout=httpx.Timeout(20.0))
        except httpx.HTTPError:
            pass

        waited = 0
        while waited < POLL_BUDGET_S:
            time.sleep(POLL_EVERY_S)
            waited += POLL_EVERY_S
            try:
                r = client.get(f"{base}/apps/{APP}/users/{user}/sessions/{session}")
            except httpx.HTTPError:
                continue
            if r.status_code == 200:
                report = ((r.json().get("state") or {}).get("report") or "").strip()
                if report:
                    print(f"SMOKE OK: report present ({len(report)} chars) after ~{waited}s.")
                    return 0

    print(f"SMOKE FAIL: no 'report' in session state after {POLL_BUDGET_S}s.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
