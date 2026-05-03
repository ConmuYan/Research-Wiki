"""Tests for networked literature metadata fetchers."""

from __future__ import annotations

import httpx
import pytest
import respx

from lgrlw.fetchers.arxiv import ARXIV_QUERY_URL, ArxivFetcher
from lgrlw.fetchers.crossref import CROSSREF_WORKS_URL, CrossrefFetcher
from lgrlw.fetchers.errors import FetcherError, FetcherNotFoundError
from lgrlw.fetchers.openalex import OPENALEX_WORKS_URL, OpenAlexFetcher


def test_crossref_fetcher_returns_canonical_metadata(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{CROSSREF_WORKS_URL}/10.5555/example").mock(
        return_value=httpx.Response(
            200,
            json={
                "message": {
                    "title": ["Example Paper"],
                    "author": [
                        {"given": "Alice", "family": "A"},
                        {"given": "Bob", "family": "B"},
                    ],
                    "published-print": {"date-parts": [[2024, 1, 1]]},
                    "container-title": ["ExampleConf"],
                    "DOI": "10.5555/example",
                    "URL": "https://doi.org/10.5555/example",
                }
            },
        )
    )

    metadata = CrossrefFetcher().fetch("https://doi.org/10.5555/EXAMPLE")

    assert route.called
    assert metadata.title == "Example Paper"
    assert metadata.authors == ["Alice A", "Bob B"]
    assert metadata.year == 2024
    assert metadata.venue == "ExampleConf"
    assert metadata.doi == "10.5555/example"
    assert metadata.url == "https://doi.org/10.5555/example"
    assert metadata.source == "crossref"


def test_crossref_fetcher_sends_mailto_from_environment(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CROSSREF_MAILTO", "maintainer@example.com")
    route = respx_mock.get(f"{CROSSREF_WORKS_URL}/10.5555/mailto").mock(
        return_value=httpx.Response(200, json={"message": _minimal_message("Mailto Paper")})
    )

    CrossrefFetcher().fetch("10.5555/mailto")

    assert route.calls.last.request.url.params["mailto"] == "maintainer@example.com"


def test_crossref_fetcher_raises_not_found(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{CROSSREF_WORKS_URL}/10.5555/missing").mock(
        return_value=httpx.Response(404, json={"status": "error"})
    )

    with pytest.raises(FetcherNotFoundError):
        CrossrefFetcher().fetch("10.5555/missing")


def test_crossref_fetcher_rejects_malformed_payload(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{CROSSREF_WORKS_URL}/10.5555/malformed").mock(
        return_value=httpx.Response(200, json={"message": {"title": ["No Authors"]}})
    )

    with pytest.raises(FetcherError):
        CrossrefFetcher().fetch("10.5555/malformed")


def test_crossref_fetcher_rejects_invalid_doi() -> None:
    with pytest.raises(FetcherError):
        CrossrefFetcher().fetch("not-a-doi")


def test_arxiv_fetcher_returns_canonical_metadata(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(ARXIV_QUERY_URL, params={"id_list": "2310.11511"}).mock(
        return_value=httpx.Response(200, text=_arxiv_feed())
    )

    metadata = ArxivFetcher().fetch("https://arxiv.org/abs/2310.11511")

    assert route.called
    assert metadata.title == "Self-RAG"
    assert metadata.authors == ["Akari Asai", "Zeqiu Wu"]
    assert metadata.year == 2023
    assert metadata.venue == "arXiv preprint"
    assert metadata.arxiv_id == "2310.11511"
    assert metadata.url == "https://arxiv.org/abs/2310.11511"
    assert metadata.source == "arxiv"


def test_arxiv_fetcher_raises_not_found(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ARXIV_QUERY_URL, params={"id_list": "2310.00000"}).mock(
        return_value=httpx.Response(200, text=_arxiv_empty_feed())
    )

    with pytest.raises(FetcherNotFoundError):
        ArxivFetcher().fetch("2310.00000")


def test_arxiv_fetcher_rejects_malformed_xml(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(ARXIV_QUERY_URL, params={"id_list": "2310.11511"}).mock(
        return_value=httpx.Response(200, text="<feed>")
    )

    with pytest.raises(FetcherError):
        ArxivFetcher().fetch("2310.11511")


def test_arxiv_fetcher_rejects_invalid_id() -> None:
    with pytest.raises(FetcherError):
        ArxivFetcher().fetch("not-an-arxiv-id")


def test_openalex_fetcher_returns_canonical_metadata(respx_mock: respx.MockRouter) -> None:
    route = respx_mock.get(f"{OPENALEX_WORKS_URL}/W4385545131").mock(
        return_value=httpx.Response(200, json=_openalex_payload())
    )

    metadata = OpenAlexFetcher().fetch("https://openalex.org/W4385545131")

    assert route.called
    assert metadata.title == "Self-RAG"
    assert metadata.authors == ["Akari Asai", "Zeqiu Wu"]
    assert metadata.year == 2023
    assert metadata.venue == "arXiv (Cornell University)"
    assert metadata.openalex_id == "W4385545131"
    assert metadata.doi == "10.48550/arxiv.2310.11511"
    assert metadata.url == "https://doi.org/10.48550/arxiv.2310.11511"
    assert metadata.source == "openalex"


def test_openalex_fetcher_sends_mailto_from_environment(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENALEX_EMAIL", "maintainer@example.com")
    route = respx_mock.get(f"{OPENALEX_WORKS_URL}/W4385545131").mock(
        return_value=httpx.Response(200, json=_openalex_payload())
    )

    OpenAlexFetcher().fetch("W4385545131")

    assert route.calls.last.request.url.params["mailto"] == "maintainer@example.com"


def test_openalex_fetcher_raises_not_found(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{OPENALEX_WORKS_URL}/W0000000000").mock(
        return_value=httpx.Response(404, json={"error": "missing"})
    )

    with pytest.raises(FetcherNotFoundError):
        OpenAlexFetcher().fetch("W0000000000")


def test_openalex_fetcher_rejects_malformed_payload(respx_mock: respx.MockRouter) -> None:
    respx_mock.get(f"{OPENALEX_WORKS_URL}/W4385545131").mock(
        return_value=httpx.Response(200, json={"display_name": "No Authors"})
    )

    with pytest.raises(FetcherError):
        OpenAlexFetcher().fetch("W4385545131")


def test_openalex_fetcher_rejects_invalid_id() -> None:
    with pytest.raises(FetcherError):
        OpenAlexFetcher().fetch("not-an-openalex-id")


def _minimal_message(title: str) -> dict[str, object]:
    return {
        "title": [title],
        "author": [{"given": "Alice", "family": "A"}],
        "issued": {"date-parts": [[2024]]},
        "container-title": ["ExampleConf"],
    }


def _arxiv_feed() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2310.11511</id>
    <updated>2023-10-18T00:00:00Z</updated>
    <published>2023-10-18T00:00:00Z</published>
    <title>Self-RAG</title>
    <summary>Example abstract.</summary>
    <author><name>Akari Asai</name></author>
    <author><name>Zeqiu Wu</name></author>
    <arxiv:primary_category term="cs.CL" />
  </entry>
</feed>
"""


def _arxiv_empty_feed() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" />
"""


def _openalex_payload() -> dict[str, object]:
    return {
        "id": "https://openalex.org/W4385545131",
        "display_name": "Self-RAG",
        "authorships": [
            {"author": {"display_name": "Akari Asai"}},
            {"author": {"display_name": "Zeqiu Wu"}},
        ],
        "publication_year": 2023,
        "primary_location": {"source": {"display_name": "arXiv (Cornell University)"}},
        "doi": "https://doi.org/10.48550/arxiv.2310.11511",
        "ids": {
            "doi": "https://doi.org/10.48550/arxiv.2310.11511",
            "openalex": "https://openalex.org/W4385545131",
        },
    }
