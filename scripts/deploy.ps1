# Codified deploy for the startup-diagnostics agent (P0.1).
#
# Runs the import preflight + unit tests, then deploys to Cloud Run with the
# flags the service actually needs:
#   --memory=2Gi      512Mi OOMs the full pipeline
#   --timeout=600     the full pipeline can take minutes
#   --trace_to_cloud  agent traces in Cloud Trace (P1.5)
# FIRECRAWL_API_KEY is read from the environment, never hardcoded/committed.
#
# Usage (PowerShell):
#   $env:FIRECRAWL_API_KEY = "fc-..."   # or rely on it already being set
#   ./scripts/deploy.ps1

$ErrorActionPreference = "Stop"

Write-Host "==> Preflight (import guard: catches a missing runtime dep before deploy)"
uv run python -m agents._preflight
if ($LASTEXITCODE -ne 0) { Write-Error "Preflight failed; aborting deploy."; exit 1 }

Write-Host "==> Unit tests"
uv run python -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Error "Tests failed; aborting deploy."; exit 1 }

if (-not $env:FIRECRAWL_API_KEY) {
    Write-Error "FIRECRAWL_API_KEY no está en el entorno. Expórtala antes de desplegar."
    exit 1
}

Write-Host "==> Deploy to Cloud Run (startup-diagnostics, europe-west1)"
# adk options come BEFORE the `agents` positional and the `--`; gcloud
# passthrough args come AFTER the `--`.
uv run python -m google.adk.cli deploy cloud_run `
    --project=your-gcp-project `
    --region=europe-west1 `
    --service_name=startup-diagnostics `
    --with_ui `
    --trace_to_cloud `
    agents `
    -- `
    --allow-unauthenticated `
    --memory=2Gi `
    --timeout=600 `
    --update-env-vars="GOOGLE_CLOUD_LOCATION=global,FIRECRAWL_API_KEY=$env:FIRECRAWL_API_KEY"

# NOTE: adk bakes `ENV GOOGLE_CLOUD_LOCATION=<--region>` (=europe-west1) into the
# image, but Gemini 3 is only served from `global`/us-central1. The Cloud Run
# env var above OVERRIDES that Docker ENV at runtime, so model calls go to
# `global` (still Vertex → Marketing credit) while the service runs in europe-west1.
