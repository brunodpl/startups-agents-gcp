"""In-context knowledge loader (F3).

The diagnosis reasons with VC frameworks that live as Markdown under
``knowledge/``. We inject them straight into the SynthesizerAgent's instruction
(NO RAG / no Discovery Engine — a hard constraint of this demo), so the model
must cite them by name.
"""

from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).parent.parent / "knowledge"


def load_frameworks(directory: Path | None = None) -> str:
    """Concatenate every ``*.md`` framework into a single string.

    Each file is prefixed with ``# Framework: <stem>`` so the model can cite it
    by name. Files are read in sorted order for deterministic output. Returns an
    empty string if the directory is missing or has no frameworks.
    """
    directory = directory or KNOWLEDGE_DIR
    if not directory.is_dir():
        return ""

    parts: list[str] = []
    for md in sorted(directory.glob("*.md")):
        content = md.read_text(encoding="utf-8").strip()
        parts.append(f"# Framework: {md.stem}\n\n{content}")
    return "\n\n".join(parts)
