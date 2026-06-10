"""Unit tests for the Spanish press/directories discovery source.

Deterministic: Firecrawl (search + scrape) and the Vertex ``genai`` client are
monkeypatched, so no network and no credit is spent. We only test our
orchestration, normalization and error isolation.

Run: ``uv run python -m pytest tests/test_spain_source.py -q``
"""

from agents.tools import spain_source

# ── fakes ────────────────────────────────────────────────────────────────────


class _FakeWebResult:
    def __init__(self, url: str, title: str = "t", description: str = "d") -> None:
        self.url = url
        self.title = title
        self.description = description


class _FakeSearchData:
    def __init__(self, urls: list[str]) -> None:
        self.web = [_FakeWebResult(u) for u in urls]


class _FakeDoc:
    def __init__(self, markdown: str) -> None:
        self.markdown = markdown


def _fake_firecrawl(urls: list[str], markdown: str = "## Startups gallegas..."):
    class _Fake:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def search(self, query, **kwargs):
            return _FakeSearchData(urls)

        def scrape(self, url, **kwargs):
            return _FakeDoc(markdown)

    return _Fake


class _FakeResp:
    def __init__(self, text: str) -> None:
        self.text = text


def _fake_genai_client(text: str):
    class _Models:
        def generate_content(self, **kwargs):
            return _FakeResp(text)

    class _Client:
        def __init__(self, **kwargs) -> None:
            self.models = _Models()

    return _Client


CANNED = """[
  {"name": "Situm", "website": "https://situm.com", "one_liner": "Posicionamiento indoor",
   "industries": ["deeptech"], "regions": ["Galicia, Spain"], "stage": "series A"},
  {"name": "Quincemil", "website": "quincemil.gal", "one_liner": "Media local",
   "industries": [], "regions": [], "stage": null},
  {"name": "", "website": "https://noname.com"},
  {"name": "SinWeb", "website": ""}
]"""


def _patch_happy_path(monkeypatch, canned: str = CANNED) -> None:
    monkeypatch.setattr(spain_source.Settings, "FIRECRAWL_API_KEY", "fc-test")
    monkeypatch.setattr(spain_source.Settings, "GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setattr(
        spain_source,
        "Firecrawl",
        _fake_firecrawl(["https://elreferente.es/articulo-1"]),
    )
    monkeypatch.setattr(spain_source.genai, "Client", _fake_genai_client(canned))


# ── search_spain ─────────────────────────────────────────────────────────────


def test_search_spain_normalizes_and_filters(monkeypatch) -> None:
    _patch_happy_path(monkeypatch)
    out = spain_source.search_spain("fintech", "Galicia", limit=10)

    names = [c["name"] for c in out]
    # Entries without name or website are dropped.
    assert names == ["Situm", "Quincemil"]
    # Every candidate is tagged with this source.
    assert all(c["source"] == "spain" for c in out)
    # Regions preserved when present, defaulted to [region] when empty.
    assert out[0]["regions"] == ["Galicia, Spain"]
    assert out[1]["regions"] == ["Galicia"]


def test_search_spain_defaults_region_to_spain(monkeypatch) -> None:
    _patch_happy_path(monkeypatch)
    out = spain_source.search_spain("fintech", None, limit=10)
    # No region requested → candidates without regions default to España.
    assert out[1]["regions"] == ["España"]


def test_search_spain_empty_without_api_key(monkeypatch) -> None:
    monkeypatch.setattr(spain_source.Settings, "FIRECRAWL_API_KEY", "")
    assert spain_source.search_spain("fintech", "Galicia") == []


def test_search_spain_empty_on_search_error(monkeypatch) -> None:
    monkeypatch.setattr(spain_source.Settings, "FIRECRAWL_API_KEY", "fc-test")
    monkeypatch.setattr(spain_source.Settings, "GOOGLE_CLOUD_PROJECT", "test-project")

    class _Boom:
        def __init__(self, api_key: str) -> None: ...

        def search(self, query, **kwargs):
            raise RuntimeError("firecrawl down")

    monkeypatch.setattr(spain_source, "Firecrawl", _Boom)
    assert spain_source.search_spain("fintech", "Galicia") == []


def test_search_spain_tolerates_failed_scrapes(monkeypatch) -> None:
    """One page failing to scrape must not kill the whole source."""
    monkeypatch.setattr(spain_source.Settings, "FIRECRAWL_API_KEY", "fc-test")
    monkeypatch.setattr(spain_source.Settings, "GOOGLE_CLOUD_PROJECT", "test-project")

    class _Flaky:
        def __init__(self, api_key: str) -> None: ...

        def search(self, query, **kwargs):
            return _FakeSearchData(
                ["https://elreferente.es/ok", "https://elreferente.es/rota"]
            )

        def scrape(self, url, **kwargs):
            if url.endswith("rota"):
                raise RuntimeError("404")
            return _FakeDoc("contenido real")

    monkeypatch.setattr(spain_source, "Firecrawl", _Flaky)
    monkeypatch.setattr(spain_source.genai, "Client", _fake_genai_client(CANNED))
    out = spain_source.search_spain("fintech", "Galicia", limit=10)
    assert [c["name"] for c in out] == ["Situm", "Quincemil"]


def test_search_spain_empty_on_gemini_error(monkeypatch) -> None:
    monkeypatch.setattr(spain_source.Settings, "FIRECRAWL_API_KEY", "fc-test")
    monkeypatch.setattr(spain_source.Settings, "GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setattr(
        spain_source, "Firecrawl", _fake_firecrawl(["https://elreferente.es/a"])
    )

    class _BoomModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("vertex down")

    class _BoomClient:
        def __init__(self, **kwargs) -> None:
            self.models = _BoomModels()

    monkeypatch.setattr(spain_source.genai, "Client", _BoomClient)
    assert spain_source.search_spain("fintech", "Galicia") == []


def test_resolve_website_returns_first_non_press_origin() -> None:
    class _Client:
        def search(self, query, **kwargs):
            return _FakeSearchData(
                [
                    "https://elreferente.es/articulo-sobre-ella",  # press → skip
                    "https://www.linkedin.com/company/sinweb",  # social → skip
                    "https://sinweb.gal/producto/precios",
                ]
            )

    url = spain_source._resolve_website(_Client(), "SinWeb", "Galicia")
    # Origin only: the candidate website is the homepage, not a deep page.
    assert url == "https://sinweb.gal"


def test_resolve_website_empty_when_only_blocked_domains() -> None:
    class _Client:
        def search(self, query, **kwargs):
            return _FakeSearchData(
                ["https://elreferente.es/a", "https://x.com/sinweb"]
            )

    assert spain_source._resolve_website(_Client(), "SinWeb", None) == ""


def test_search_spain_resolves_missing_websites(monkeypatch) -> None:
    """A startup named in the press without a linked website gets its site
    resolved via an extra Firecrawl search instead of being dropped."""
    monkeypatch.setattr(spain_source.Settings, "FIRECRAWL_API_KEY", "fc-test")
    monkeypatch.setattr(spain_source.Settings, "GOOGLE_CLOUD_PROJECT", "test-project")

    class _Client:
        def __init__(self, api_key: str) -> None: ...

        def search(self, query, **kwargs):
            if "SinWeb" in query:  # website-resolution query
                return _FakeSearchData(["https://sinweb.gal/about"])
            return _FakeSearchData(["https://elreferente.es/articulo-1"])

        def scrape(self, url, **kwargs):
            return _FakeDoc("contenido real")

    monkeypatch.setattr(spain_source, "Firecrawl", _Client)
    monkeypatch.setattr(spain_source.genai, "Client", _fake_genai_client(CANNED))
    out = spain_source.search_spain("fintech", "Galicia", limit=10)

    names = [c["name"] for c in out]
    assert "SinWeb" in names
    sinweb = next(c for c in out if c["name"] == "SinWeb")
    assert sinweb["website"] == "https://sinweb.gal"


def test_search_spain_empty_when_no_pages_scraped(monkeypatch) -> None:
    """No scrapeable content → [] without ever calling Gemini."""
    monkeypatch.setattr(spain_source.Settings, "FIRECRAWL_API_KEY", "fc-test")
    monkeypatch.setattr(spain_source.Settings, "GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setattr(spain_source, "Firecrawl", _fake_firecrawl([]))

    called = {"gemini": False}

    class _Models:
        def generate_content(self, **kwargs):
            called["gemini"] = True
            return _FakeResp("[]")

    class _Client:
        def __init__(self, **kwargs) -> None:
            self.models = _Models()

    monkeypatch.setattr(spain_source.genai, "Client", _Client)
    assert spain_source.search_spain("fintech", "Galicia") == []
    assert called["gemini"] is False
