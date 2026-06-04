"""Settings for invoice_router_agent.

Variable loading order:
  1. .env file (via dotenv)
  2. Real environment variables (override .env)

Vertex AI routing (consuming-gcp-credits SKILL)
------------------------------------------------
Do NOT use GOOGLE_API_KEY for LLM calls — it routes to the free-tier
generativelanguage.googleapis.com and will NOT consume the Marketing
credit (433.58 €, expires 2026-06-25).  Use the three Vertex AI vars
below instead.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── LLM / Vertex AI (aiplatform.googleapis.com) ──────────────────────────
    # GOOGLE_GENAI_USE_VERTEXAI is set to "True" in agent.py BEFORE any import
    # so LlmAgent always routes through Vertex AI.  Redundant here but kept as
    # documentation.
    GOOGLE_GENAI_USE_VERTEXAI: str = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True")
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "your-gcp-project")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west1")
    ADK_MODEL: str = os.getenv("ADK_MODEL", "gemini-2.5-flash")

    # App
    APP_NAME: str = os.getenv("APP_NAME", "invoice_router_agent")
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ── Cloud Storage inbox (storage.googleapis.com, Marketing credit) ────────
    GCS_INBOX_BUCKET: str = os.getenv("GCS_INBOX_BUCKET", "your-gcp-project-inbox")
    LOCAL_OUTPUT_DIR: str = os.getenv("LOCAL_OUTPUT_DIR", "./tmp/output")

    # ── WhatsApp channel ──────────────────────────────────────────────────────
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")

    # ── Gmail channel ─────────────────────────────────────────────────────────
    GMAIL_CLIENT_ID: str = os.getenv("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET: str = os.getenv("GMAIL_CLIENT_SECRET", "")
    GMAIL_REFRESH_TOKEN: str = os.getenv("GMAIL_REFRESH_TOKEN", "")
    GMAIL_INBOX_ADDRESS: str = os.getenv("GMAIL_INBOX_ADDRESS", "")

    # ── Supabase (próxima iteración) ──────────────────────────────────────────
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_SCHEMA: str = os.getenv("SUPABASE_SCHEMA", "agent_ops")

    # ── Delivery targets ──────────────────────────────────────────────────────
    GOOGLE_DRIVE_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    EXTERNAL_API_BASE_URL: str = os.getenv("EXTERNAL_API_BASE_URL", "")
    EXTERNAL_API_TOKEN: str = os.getenv("EXTERNAL_API_TOKEN", "")
