"""Unit tests for Cloud Logging init (P1.5).

Telemetry must NEVER break the app, and must stay a no-op off Cloud Run (so it
doesn't add noise or hit credentials locally / in tests).

Run: ``uv run python -m pytest tests/test_observability.py -q``
"""

import agents.observability as obs


def test_init_cloud_logging_noop_off_cloud_run(monkeypatch) -> None:
    monkeypatch.delenv("DISABLE_CLOUD_LOGGING", raising=False)
    monkeypatch.delenv("K_SERVICE", raising=False)  # not on Cloud Run
    obs.init_cloud_logging()  # must be a no-op, no raise


def test_init_cloud_logging_swallows_errors_on_cloud_run(monkeypatch) -> None:
    monkeypatch.delenv("DISABLE_CLOUD_LOGGING", raising=False)
    monkeypatch.setenv("K_SERVICE", "startup-diagnostics")  # pretend Cloud Run

    import google.cloud.logging

    def _boom(*args, **kwargs):
        raise RuntimeError("no credentials")

    monkeypatch.setattr(google.cloud.logging, "Client", _boom)
    obs.init_cloud_logging()  # client blows up → must be swallowed, no raise
