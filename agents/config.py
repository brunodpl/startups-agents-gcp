"""Central settings for the startup-diagnostics agents.

Vertex AI routing (see the `consuming-gcp-credits` skill)
---------------------------------------------------------
All LLM calls MUST go through Vertex AI (aiplatform.googleapis.com) so they
consume the Marketing AI Agents credit (433.58 €, expires 2026-06-25) and NOT
the free tier.  Never use GOOGLE_API_KEY / google.generativeai for transport.

Loading order: a local `.env` (via python-dotenv) fills values that are not
already present in the real environment; real env vars always win.  On Cloud
Run the values fall back to the hard-coded defaults below.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── Vertex AI routing (aiplatform.googleapis.com → Marketing credit) ──────
    GOOGLE_GENAI_USE_VERTEXAI: str = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True")
    # No default on purpose: supply it via a local ``.env`` or a Cloud Run env
    # var at deploy time (see scripts/deploy.ps1). Empty keeps the real project
    # ID out of the (public) repo.
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    # Gemini 3 is NOT served from europe-west1; "global" has both models we use.
    # Still Vertex (aiplatform.googleapis.com) → Marketing credit. The Cloud Run
    # service stays in europe-west1; only model inference uses this location.
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "global")

    # ── Models ────────────────────────────────────────────────────────────────
    # Flash for cheap/fast steps; Pro for the final synthesis (from F3).
    MODEL_FLASH: str = os.getenv("MODEL_FLASH", "gemini-3.5-flash")
    MODEL_PRO: str = os.getenv("MODEL_PRO", "gemini-3.1-pro-preview")

    # ── Discovery ─────────────────────────────────────────────────────────────
    # Safety cap on how many qualified candidates (es_candidato) flow into the
    # per-candidate analysis. Discovery is a binary qualifier, not a ranker:
    # every candidate that passes the gate is kept, up to this many. Guards the
    # Cloud Run timeout/memory budget against an overly generous gate.
    # 5, not 8: a candidate costs ~70s (research + parallel analysts + Pro
    # synthesis), so 8 blew the request timeout on 2026-06-10; 5 x ~70s fits
    # comfortably in the 900s deploy timeout.
    MAX_CANDIDATES: int = int(os.getenv("MAX_CANDIDATES", "5"))
    # Placeholder sector used when a thesis omits one (configurable default).
    DISCOVERY_SECTOR_DEFAULT: str = os.getenv(
        "DISCOVERY_SECTOR_DEFAULT", "artificial intelligence"
    )

    # ── App ─────────────────────────────────────────────────────────────────--
    APP_NAME: str = os.getenv("APP_NAME", "startup_diagnostics")
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ── External tools ────────────────────────────────────────────────────────
    # Firecrawl API key for the fetch_url tool (F2). SECRET → keep in .env only,
    # and pass it to Cloud Run at deploy time (env var / Secret Manager).
    FIRECRAWL_API_KEY: str = os.getenv("FIRECRAWL_API_KEY", "")
