"""Root agent for the startup-diagnostics demo.

F3: the root agent is the full pipeline (SequentialAgent) built in pipeline.py:
discovery -> per-candidate analysis/diagnosis. F4 appends the reporting stage.
"""

import os

# Vertex AI routing MUST be set before google.adk resolves the model backend,
# so LLM calls go through aiplatform.googleapis.com (Marketing credit) even on
# Cloud Run without a .env file. See the `consuming-gcp-credits` skill.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "your-gcp-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")  # Gemini 3 not in europe-west1

from .observability import init_cloud_logging

# Route logs to Cloud Logging on Cloud Run (no-op locally; never raises).
init_cloud_logging()

from .pipeline import build_pipeline  # noqa: E402

# F3: the root agent is the full 4-stage pipeline.
root_agent = build_pipeline()
