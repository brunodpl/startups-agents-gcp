"""Observability wiring (P1.5).

Routes the stdlib ``logging`` the pipeline already uses to Google Cloud Logging,
so structured logs land next to the Cloud Run request logs. Tracing is enabled
separately by the ``--trace_to_cloud`` deploy flag (no code here).

Telemetry must NEVER break the app: every failure is swallowed with a warning.
It only activates on Cloud Run (``K_SERVICE`` is set there); locally and in
tests it is a no-op. ``DISABLE_CLOUD_LOGGING`` forces it off everywhere.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def init_cloud_logging() -> None:
    """Best-effort: attach the Cloud Logging handler on Cloud Run. Never raises."""
    if os.getenv("DISABLE_CLOUD_LOGGING"):
        return
    # Only ship to Cloud Logging when actually on Cloud Run (avoids credential
    # prompts / noise locally and in tests).
    if not os.getenv("K_SERVICE"):
        return
    try:
        import google.cloud.logging

        client = google.cloud.logging.Client()
        client.setup_logging(log_level=logging.INFO)
        logger.info("Cloud Logging initialised.")
    except Exception as e:  # telemetry must never break the app
        logger.warning("Cloud Logging not initialised: %s", e)
