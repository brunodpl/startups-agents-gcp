"""Settings for csv_transformer agent.

Variable loading order:
  1. .env file (via dotenv)
  2. Real environment variables (override .env)

Vertex AI routing (consuming-gcp-credits SKILL)
------------------------------------------------
Do NOT use GOOGLE_API_KEY for LLM calls.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    GOOGLE_GENAI_USE_VERTEXAI: str = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True")
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "your-gcp-project")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west1")
    ADK_MODEL: str = os.getenv("ADK_MODEL", "gemini-2.5-flash")

    APP_NAME: str = os.getenv("CSV_APP_NAME", "csv_transformer_agent")
    APP_ENV: str = os.getenv("APP_ENV", "dev")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    LOCAL_OUTPUT_DIR: str = os.getenv("LOCAL_OUTPUT_DIR", "./tmp/output")
