"""Tool: handle_uploaded_file — guarda archivos adjuntos del turno actual."""

import base64
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Any

from google.adk.tools import ToolContext

from ..config import Settings


def handle_uploaded_file(tool_context: ToolContext) -> dict[str, Any]:
    """Persiste los archivos adjuntos del turno. Devuelve lista con local_path y gcs_stub."""
    output_dir = Path(Settings.LOCAL_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    detected: list[dict[str, Any]] = []

    user_content = getattr(tool_context, "user_content", None)
    if user_content is None:
        return {"files": [], "count": 0}

    for part in (getattr(user_content, "parts", []) or []):
        inline = getattr(part, "inline_data", None)
        if inline is None:
            continue

        mime_type: str = getattr(inline, "mime_type", "application/octet-stream")
        raw_data = getattr(inline, "data", b"")
        file_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data

        ext = mimetypes.guess_extension(mime_type) or ".bin"
        if ext == ".jpe":
            ext = ".jpg"

        unique_name = f"{uuid.uuid4().hex}{ext}"
        local_path = output_dir / unique_name
        local_path.write_bytes(file_bytes)

        gcs_bucket = os.getenv("GCS_INBOX_BUCKET", "your-gcp-project-inbox")
        detected.append({
            "filename": unique_name,
            "mime_type": mime_type,
            "local_path": str(local_path),
            "gcs_stub": f"gs://{gcs_bucket}/incoming/{unique_name}",
            "size_bytes": len(file_bytes),
        })

    return {"files": detected, "count": len(detected)}
