"""Unit tests for the in-context knowledge loader (F3).

Run: ``uv run python -m pytest tests/test_knowledge.py -q``
"""

from agents.knowledge import load_frameworks


def test_load_frameworks_concatenates_with_titles(tmp_path) -> None:
    (tmp_path / "a.md").write_text("Contenido A", encoding="utf-8")
    (tmp_path / "b.md").write_text("Contenido B", encoding="utf-8")

    out = load_frameworks(tmp_path)

    assert "# Framework: a" in out
    assert "# Framework: b" in out
    assert "Contenido A" in out
    assert "Contenido B" in out
    # Deterministic, sorted order: a before b.
    assert out.index("Framework: a") < out.index("Framework: b")


def test_load_frameworks_empty_dir(tmp_path) -> None:
    assert load_frameworks(tmp_path) == ""


def test_load_frameworks_real_dir() -> None:
    # The repo ships frameworks under knowledge/*.md.
    out = load_frameworks()
    assert "Framework:" in out
    assert len(out) > 100
