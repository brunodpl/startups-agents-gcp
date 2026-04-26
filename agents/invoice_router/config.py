import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # LLM
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    ADK_MODEL: str = os.getenv("ADK_MODEL", "gemini-2.5-flash")

    # App
    APP_NAME: str = os.getenv("APP_NAME", "invoice_router_agent")
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # WhatsApp
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")

    # Gmail
    GMAIL_CLIENT_ID: str = os.getenv("GMAIL_CLIENT_ID", "")
    GMAIL_CLIENT_SECRET: str = os.getenv("GMAIL_CLIENT_SECRET", "")
    GMAIL_REFRESH_TOKEN: str = os.getenv("GMAIL_REFRESH_TOKEN", "")
    GMAIL_INBOX_ADDRESS: str = os.getenv("GMAIL_INBOX_ADDRESS", "")

    # Supabase (next iteration)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_SCHEMA: str = os.getenv("SUPABASE_SCHEMA", "agent_ops")

    # Delivery targets (next iteration)
    GOOGLE_DRIVE_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
    LOCAL_OUTPUT_DIR: str = os.getenv("LOCAL_OUTPUT_DIR", "./tmp/output")
    EXTERNAL_API_BASE_URL: str = os.getenv("EXTERNAL_API_BASE_URL", "")
    EXTERNAL_API_TOKEN: str = os.getenv("EXTERNAL_API_TOKEN", "")
