"""Root agent for the startup-diagnostics demo.

F2: the root agent is the DiscoveryAgent — given an investment thesis it queries
the YC OSS source (search_startups tool), scores candidates, and returns a
shortlist. Becomes the full 4-stage pipeline (SequentialAgent) in F3.
"""

import os

# Vertex AI routing MUST be set before google.adk resolves the model backend,
# so LLM calls go through aiplatform.googleapis.com (Marketing credit) even on
# Cloud Run without a .env file. See the `consuming-gcp-credits` skill.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "your-gcp-project")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west1")

from .sub_agents.discovery import discovery_agent  # noqa: E402

# F2: the DiscoveryAgent is the root so we can test thesis -> scored shortlist in
# isolation. In F3 this becomes the full SequentialAgent built in pipeline.py
# (discovery -> per-candidate analysis -> diagnosis -> reporting).
root_agent = discovery_agent
