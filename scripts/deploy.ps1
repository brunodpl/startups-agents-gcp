# Codified deploy for the startup-diagnostics agent (P0.1).
#
# Runs the import preflight + unit tests, then deploys to Cloud Run with the
# flags the service actually needs:
#   --memory=2Gi      512Mi OOMs the full pipeline
#   --timeout=900     MAX_CANDIDATES(5) × ~70s/candidata + discovery/reporting;
#                     600s was exceeded by the 8-candidate run of 2026-06-10
#   --trace_to_cloud  agent traces in Cloud Trace (P1.5)
#
# Identifiers and secrets are NEVER hard-coded/committed:
#   - GOOGLE_CLOUD_PROJECT is read from the environment (the GCP project to use).
#   - FIRECRAWL_API_KEY is read from the environment and stored in Secret Manager;
#     the service reads it via --set-secrets, not a plaintext env var.
#   - SESSION_SERVICE_URI (optional) persists sessions in Agent Engine so runs
#     survive scale-to-zero and can feed evals (agentengine://projects/...).
#
# Usage (PowerShell):
#   $env:GOOGLE_CLOUD_PROJECT = "your-gcp-project-id"
#   $env:FIRECRAWL_API_KEY    = "fc-..."
#   $env:SESSION_SERVICE_URI  = "agentengine://projects/.../locations/europe-west1/reasoningEngines/..."
#   ./scripts/deploy.ps1

# "Continue", not "Stop": gcloud writes informational messages to stderr (e.g.
# "Updated IAM policy"), and under "Stop" PowerShell 5.1 turns that into a
# terminating NativeCommandError mid-script. Every native call below checks
# $LASTEXITCODE explicitly instead.
$ErrorActionPreference = "Continue"

if (-not $env:GOOGLE_CLOUD_PROJECT) {
    Write-Error "GOOGLE_CLOUD_PROJECT no está en el entorno. Expórtalo antes de desplegar."
    exit 1
}
if (-not $env:FIRECRAWL_API_KEY) {
    Write-Error "FIRECRAWL_API_KEY no está en el entorno. Expórtala antes de desplegar."
    exit 1
}

$project = $env:GOOGLE_CLOUD_PROJECT
$secretName = "firecrawl-api-key"

Write-Host "==> Preflight (import guard: catches a missing runtime dep before deploy)"
uv run python -m agents._preflight
if ($LASTEXITCODE -ne 0) { Write-Error "Preflight failed; aborting deploy."; exit 1 }

Write-Host "==> Unit tests"
uv run python -m pytest -q
if ($LASTEXITCODE -ne 0) { Write-Error "Tests failed; aborting deploy."; exit 1 }

# ── Firecrawl key -> Secret Manager (no plaintext key on the service or repo) ──
Write-Host "==> Storing FIRECRAWL_API_KEY in Secret Manager ($secretName)"
gcloud secrets describe $secretName --project=$project *> $null
$secretExists = ($LASTEXITCODE -eq 0)
# Write the value WITHOUT a trailing newline so the stored secret isn't corrupted.
$tmp = [System.IO.Path]::GetTempFileName()
[System.IO.File]::WriteAllText($tmp, $env:FIRECRAWL_API_KEY)
try {
    if ($secretExists) {
        gcloud secrets versions add $secretName --project=$project --data-file=$tmp
    } else {
        gcloud secrets create $secretName --project=$project `
            --replication-policy=automatic --data-file=$tmp
    }
    if ($LASTEXITCODE -ne 0) { Write-Error "Could not write the secret; aborting."; exit 1 }
} finally {
    Remove-Item $tmp -Force
}

# The Cloud Run runtime service account must be able to read the secret.
$projectNumber = (gcloud projects describe $project --format="value(projectNumber)")
$runtimeSa = "$projectNumber-compute@developer.gserviceaccount.com"
Write-Host "==> Granting secretAccessor on $secretName to $runtimeSa"
gcloud secrets add-iam-policy-binding $secretName --project=$project `
    --member="serviceAccount:$runtimeSa" `
    --role="roles/secretmanager.secretAccessor" *> $null
if ($LASTEXITCODE -ne 0) { Write-Error "Could not grant secret access; aborting."; exit 1 }

# ── Session persistence (Agent Engine) ────────────────────────────────────────
# Optional but recommended: without it sessions are in-memory and die with the
# instance (scale-to-zero), so past runs can't be replayed or turned into evals.
$sessionArgs = @()
if ($env:SESSION_SERVICE_URI) {
    Write-Host "==> Sessions persisted via Agent Engine ($($env:SESSION_SERVICE_URI -replace 'projects/\d+', 'projects/<number>'))"
    $sessionArgs = @("--session_service_uri=$env:SESSION_SERVICE_URI")
} else {
    Write-Warning "SESSION_SERVICE_URI no está en el entorno: las sesiones serán in-memory (se pierden al reciclar la instancia)."
}

Write-Host "==> Deploy to Cloud Run (startup-diagnostics, europe-west1)"
# adk options come BEFORE the `agents` positional and the `--`; gcloud
# passthrough args come AFTER the `--`.
uv run python -m google.adk.cli deploy cloud_run `
    --project=$project `
    --region=europe-west1 `
    --service_name=startup-diagnostics `
    --with_ui `
    --trace_to_cloud `
    @sessionArgs `
    agents `
    -- `
    --allow-unauthenticated `
    --memory=2Gi `
    --timeout=900 `
    --update-env-vars="GOOGLE_CLOUD_PROJECT=$project,GOOGLE_CLOUD_LOCATION=global" `
    --set-secrets="FIRECRAWL_API_KEY=${secretName}:latest"
if ($LASTEXITCODE -ne 0) { Write-Error "adk deploy failed."; exit 1 }

# NOTE: adk bakes `ENV GOOGLE_CLOUD_LOCATION=<--region>` (=europe-west1) into the
# image, but Gemini 3 is only served from `global`/us-central1. The Cloud Run
# env var above OVERRIDES that Docker ENV at runtime, so model calls go to
# `global` (still Vertex → Marketing credit) while the service runs in europe-west1.
