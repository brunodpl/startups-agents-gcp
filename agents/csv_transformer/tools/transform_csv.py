"""Tool: transform_csv — transforms a CSV based on column mapping, order, and drops."""

import csv
import io
import uuid
from pathlib import Path
from typing import Any

from google.adk.tools import ToolContext

from ..config import Settings


def transform_csv(
    tool_context: ToolContext,
    column_mapping: dict[str, str],
    column_order: list[str],
    drop_columns: list[str],
) -> dict[str, Any]:
    """Transforms a previously-read CSV file by renaming, reordering, and
    dropping columns.

    Args:
        column_mapping: Dict mapping old column names to new names.
                        e.g. {"fecha": "date", "importe": "amount"}
        column_order: Ordered list of final column names (after renaming).
                      e.g. ["amount", "date", "name"]
        drop_columns: List of original column names to remove.
                      e.g. ["notas"]

    Returns:
        dict with output_filename, output_path, applied_renames,
        applied_order, applied_drops, row_count, and csv_text.
    """
    state = tool_context.state

    local_path = state.get("csv_local_path")
    original_headers = state.get("csv_headers")
    delimiter = state.get("csv_delimiter", ",")

    if not local_path or not original_headers:
        return {"status": "error", "reason": "no_csv_loaded", "hint": "run read_csv_attachment first"}

    path = Path(local_path)
    if not path.exists():
        return {"status": "error", "reason": "csv_file_not_found", "path": local_path}

    text_content = path.read_text(encoding="utf-8")
    reader = csv.reader(io.StringIO(text_content), delimiter=delimiter)
    all_rows = list(reader)

    if not all_rows:
        return {"status": "error", "reason": "empty_csv"}

    src_headers = all_rows[0]
    data_rows = all_rows[1:]

    header_index = {h.strip(): i for i, h in enumerate(src_headers)}

    for old in drop_columns:
        if old.strip() not in header_index:
            return {
                "status": "error",
                "reason": "column_not_found",
                "column": old.strip(),
                "available": src_headers,
            }

    for old in column_mapping:
        if old.strip() not in header_index:
            return {
                "status": "error",
                "reason": "column_not_found",
                "column": old.strip(),
                "available": src_headers,
            }

    new_headers_map = {}
    for h in src_headers:
        stripped = h.strip()
        new_headers_map[stripped] = column_mapping.get(stripped, stripped)

    if not column_order:
        final_order = [new_headers_map[h.strip()] for h in src_headers if h.strip() not in [d.strip() for d in drop_columns]]
    else:
        final_order = column_order

    if not drop_columns:
        final_drop_names = []
    else:
        final_drop_names = [d.strip() for d in drop_columns]

    row_count = 0
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
    writer.writerow(final_order)

    for row in data_rows:
        new_row = {}
        for i, h in enumerate(src_headers):
            stripped = h.strip()
            if stripped in final_drop_names:
                continue
            new_name = new_headers_map[stripped]
            new_row[new_name] = row[i] if i < len(row) else ""

        ordered_row = [new_row.get(name, "") for name in final_order]
        writer.writerow(ordered_row)
        row_count += 1

    csv_text = output.getvalue()

    output_dir = Path(Settings.LOCAL_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"transformed_{uuid.uuid4().hex}.csv"
    output_path = output_dir / output_filename
    output_path.write_text(csv_text, encoding="utf-8")

    return {
        "status": "success",
        "output_filename": output_filename,
        "output_path": str(output_path),
        "applied_renames": column_mapping,
        "applied_order": final_order,
        "applied_drops": final_drop_names,
        "row_count": row_count,
        "csv_text": csv_text,
    }
