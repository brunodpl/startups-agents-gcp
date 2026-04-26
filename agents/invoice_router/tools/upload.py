"""Tool: handle_uploaded_file

Processes a file attachment that arrives via the `adk web` UI.

ADK represents uploaded files as `google.genai.types.Part` objects inside
`tool_context.user_content.parts`.  When the user attaches a file in the
browser the part carries:
  - part.inline_data.mime_type  → e.g. "application/pdf", "image/jpeg"
  - part.inline_data.data       → raw bytes (base64-decoded by the SDK)

The tool:
  1. Iterates every non-text part in the current turn.
  2. Saves the file to LOCAL_OUTPUT_DIR (configurable via .env).
  3. Returns a structured dict that downstream tools / the agent can act on.

Routing note (consuming-gcp-credits SKILL):
  Heavy extraction work must go through Cloud Storage + Document AI / Vertex AI,
  NOT through local processing.  This tool is intentionally minimal: it lands
  the file locally so the agent can acknowledge receipt, and it returns a GCS
  stub path that future tools will use to upload to storage.googleapis.com.
"""

import base64
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Any

from google.adk.tools import ToolContext

from ..config import Settings


def handle_uploaded_file(tool_context: ToolContext) -> dict[str, Any]:  # noqa: D401
    """Inspect the current turn for file attachments and persist them locally.

    Returns a summary dict with one entry per detected file:
    {
      "files": [
        {
          "filename": "factura_abc.pdf",
          "mime_type": "application/pdf",
          "local_path": "/tmp/output/factura_abc.pdf",
          "gcs_stub": "gs://your-gcp-project-inbox/incoming/factura_abc.pdf",
          "size_bytes": 84302
        },
        ...
      ],
      "count": 1
    }

    If no files are present, returns {"files": [], "count": 0}.
    """
    output_dir = Path(Settings.LOCAL_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    detected: list[dict[str, Any]] = []

    # ADK exposes the current user message via tool_context.user_content
    user_content = getattr(tool_context, "user_content", None)
    if user_content is None:
        return {"files": [], "count": 0}

    parts = getattr(user_content, "parts", []) or []

    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is None:
            continue

        mime_type: str = getattr(inline, "mime_type", "application/octet-stream")
        raw_data = getattr(inline, "data", b"")

        # SDK may deliver data as bytes or as a base64 string depending on version
        if isinstance(raw_data, str):
            file_bytes = base64.b64decode(raw_data)
        else:
            file_bytes = raw_data  # already bytes

        ext = mimetypes.guess_extension(mime_type) or ".bin"
        # Normalise common MIME quirks
        if ext == ".jpe":
            ext = ".jpg"
        if ext == ".pdf":  # sometimes guessed as .pdf already — keep it
            ext = ".pdf"

        unique_name = f"{uuid.uuid4().hex}{ext}"
        local_path = output_dir / unique_name

        local_path.write_bytes(file_bytes)

        gcs_bucket = os.getenv("GCS_INBOX_BUCKET", "your-gcp-project-inbox")
        gcs_stub = f"gs://{gcs_bucket}/incoming/{unique_name}"

        detected.append(
            {
                "filename": unique_name,
                "mime_type": mime_type,
                "local_path": str(local_path),
                "gcs_stub": gcs_stub,
                "size_bytes": len(file_bytes),
            }
        )

    return {"files": detected, "count": len(detected)}
