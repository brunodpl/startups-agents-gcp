"""Tool: read_csv_attachment — reads a CSV file attached to the current turn."""

import base64
import csv
import io
import mimetypes
import uuid
from pathlib import Path
from typing import Any

from google.adk.tools import ToolContext

from ..config import Settings

MAX_PREVIEW_ROWS = 5


def _detect_delimiter(sample: str) -> str:
    """Detect the most likely CSV delimiter from a text sample."""
    candidates = [",", ";", "\t"]
    best = ","
    best_count = 0
    sample = sample[:4096]
    for delim in candidates:
        count = sample.count(delim)
        if count > best_count:
            best_count = count
            best = delim
    return best


def _detect_encoding(raw_bytes: bytes) -> str:
    """Try UTF-8 first, fall back to Latin-1."""
    try:
        raw_bytes.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def read_csv_attachment(tool_context: ToolContext) -> dict[str, Any]:
    """Reads the first CSV file attached to the current conversation turn.

    Extracts the file, saves it locally, detects delimiter and encoding,
    parses headers and preview rows.

    Returns:
        dict with filename, local_path, has_headers, headers, row_count,
        preview_rows, and delimiter.
    """
    user_content = getattr(tool_context, "user_content", None)
    if user_content is None:
        return {"status": "error", "reason": "no_user_content"}

    parts = getattr(user_content, "parts", []) or []

    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is None:
            continue

        mime_type = getattr(inline, "mime_type", "application/octet-stream")
        raw_data = getattr(inline, "data", b"")
        file_bytes = base64.b64decode(raw_data) if isinstance(raw_data, str) else raw_data

        if not file_bytes:
            return {"status": "error", "reason": "empty_file"}

        text_content = file_bytes.decode(_detect_encoding(file_bytes))

        ext = mimetypes.guess_extension(mime_type) or ".csv"
        if ext in (".jpe", ".jpeg"):
            ext = ".csv"

        output_dir = Path(Settings.LOCAL_OUTPUT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        unique_name = f"{uuid.uuid4().hex}{ext}"
        local_path = output_dir / unique_name
        local_path.write_bytes(file_bytes)

        delimiter = _detect_delimiter(text_content)

        reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
        all_rows = list(reader)

        has_headers = False
        if all_rows:
            first_row_lower = [cell.lower().strip() for cell in all_rows[0]]
            has_headers = any(
                not cell.replace(".", "").replace("-", "").replace(",", "").isdigit()
                for cell in first_row_lower
            )

        if has_headers:
            headers = all_rows[0]
            data_rows = all_rows[1:]
        else:
            headers = [f"col_{i}" for i in range(len(all_rows[0]))] if all_rows else []
            data_rows = all_rows

        preview_rows = data_rows[:MAX_PREVIEW_ROWS]

        tool_context.state["csv_local_path"] = str(local_path)
        tool_context.state["csv_headers"] = headers
        tool_context.state["csv_delimiter"] = delimiter
        tool_context.state["csv_has_headers"] = has_headers

        return {
            "status": "success",
            "filename": unique_name,
            "local_path": str(local_path),
            "has_headers": has_headers,
            "headers": headers,
            "row_count": len(data_rows),
            "preview_rows": preview_rows,
            "delimiter": delimiter,
        }

    return {"status": "error", "reason": "no_csv_attachment_found"}
