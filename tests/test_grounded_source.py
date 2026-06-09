"""Unit tests for the grounded discovery source (P0.2).

Deterministic: the Vertex ``genai`` client is monkeypatched, so no network and
no credit is spent. We only test our normalization + JSON parsing.

Run: ``uv run python -m pytest tests/test_grounded_source.py -q``
"""

from agents.tools import grounded_source

# ── _parse_json_array ────────────────────────────────────────────────────────


def test_parse_json_array_plain() -> None:
    assert grounded_source._parse_json_array('[{"name": "X"}]') == [{"name": "X"}]


def test_parse_json_array_code_fenced() -> None:
    raw = '```json\n[{"name": "X"}]\n```'
    assert grounded_source._parse_json_array(raw) == [{"name": "X"}]


def test_parse_json_array_prose_fallback() -> None:
    raw = 'Aquí tienes:\n[{"name": "Y"}]\nEso es todo.'
    assert grounded_source._parse_json_array(raw) == [{"name": "Y"}]


def test_parse_json_array_garbage_returns_empty() -> None:
    assert grounded_source._parse_json_array("no json here") == []


# ── search_grounded ──────────────────────────────────────────────────────────


class _FakeResp:
    def __init__(self, text: str) -> None:
        self.text = text


def _fake_client_returning(text: str):
    class _Models:
        def generate_content(self, **kwargs):
            return _FakeResp(text)

    class _Client:
        def __init__(self, **kwargs) -> None:
            self.models = _Models()

    return _Client


CANNED = """[
  {"name": "Imatia", "website": "https://imatia.com", "one_liner": "Plataforma low-code",
   "industries": ["software"], "regions": ["Galicia, Spain"], "stage": "growth"},
  {"name": "Bosonit", "website": "bosonit.com", "one_liner": "Data & AI",
   "industries": [], "regions": [], "stage": null},
  {"name": "", "website": "https://noname.com"},
  {"name": "NoSite", "website": ""}
]"""


def test_search_grounded_normalizes_and_filters(monkeypatch) -> None:
    # Set the project explicitly so the test doesn't depend on a baked-in default.
    monkeypatch.setattr(grounded_source.Settings, "GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setattr(
        grounded_source.genai, "Client", _fake_client_returning(CANNED)
    )
    out = grounded_source.search_grounded("software", "galicia", limit=10)

    names = [c["name"] for c in out]
    # Entries without name or website are dropped.
    assert names == ["Imatia", "Bosonit"]
    # Every grounded candidate is tagged.
    assert all(c["source"] == "grounded" for c in out)
    # Regions preserved when present, defaulted to [region] when empty.
    assert out[0]["regions"] == ["Galicia, Spain"]
    assert out[1]["regions"] == ["galicia"]


def test_search_grounded_empty_on_error(monkeypatch) -> None:
    # Project set so we exercise the client-error path, not the empty-project guard.
    monkeypatch.setattr(grounded_source.Settings, "GOOGLE_CLOUD_PROJECT", "test-project")

    class _BoomModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("vertex down")

    class _BoomClient:
        def __init__(self, **kwargs) -> None:
            self.models = _BoomModels()

    monkeypatch.setattr(grounded_source.genai, "Client", _BoomClient)
    assert grounded_source.search_grounded("software", "galicia") == []
