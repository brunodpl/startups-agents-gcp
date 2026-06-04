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
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "your-gcp-project")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west1")

    # ── Models ────────────────────────────────────────────────────────────────
    # Flash for cheap/fast steps; Pro for the final synthesis (from F3).
    MODEL_FLASH: str = os.getenv("MODEL_FLASH", "gemini-2.5-flash")
    MODEL_PRO: str = os.getenv("MODEL_PRO", "gemini-2.5-pro")

    # ── App ─────────────────────────────────────────────────────────────────--
    APP_NAME: str = os.getenv("APP_NAME", "startup_diagnostics")
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
