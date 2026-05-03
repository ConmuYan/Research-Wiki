"""Tests for ``lgrlw add-literature --ss`` (Semantic Scholar fetcher).

CLI-level coverage mirrors ``tests/test_add_literature_openalex.py``,
with a handful of unit-level assertions on
:func:`lgrlw.fetchers.semanticscholar._normalize_identifier` to pin the
permissive identifier formats the fetcher advertises.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx
from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fetchers.errors import FetcherError
from lgrlw.fetchers.semanticscholar import (
    SEMANTIC_SCHOLAR_BASE_URL,
    _normalize_identifier,
)
from lgrlw.fs import read_frontmatter

SELF_RAG_PAPER_ID = "649def34f8be52c8b66281af98ae884c09aef38b"


def test_add_ss_fetches_metadata_and_writes_entry(
    project: Path, runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(f"{SEMANTIC_SCHOLAR_BASE_URL}/{SELF_RAG_PAPER_ID}").mock(
        return_value=httpx.Response(200, json=_ss_payload()),
    )

    result = runner.invoke(
        app,
        [
            "add-literature",
            "--ss",
            SELF_RAG_PAPER_ID,
            "--tags",
            "rag,llm",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code == 0, result.output
    assert route.called
    assert route.calls.last.request.url.params["fields"] == (
        "paperId,title,authors,year,venue,externalIds,url"
    )

    paper_id = "asai-2023-self-rag"
    paper = project / "literature-kb" / "02_Literature" / "Papers" / f"{paper_id}.md"
    assert paper.is_file()
    fm, body = read_frontmatter(paper)
    assert fm is not None
    assert fm["title"] == "Self-RAG"
    assert fm["authors"] == ["Akari Asai", "Zeqiu Wu"]
    assert fm["year"] == 2023
    assert fm["venue"] == "arXiv.org"
    assert fm["doi"] == "10.48550/arxiv.2310.11511"
    assert fm["arxiv_id"] == "2310.11511"
    assert fm["semantic_scholar_id"] == SELF_RAG_PAPER_ID
    assert fm["source"] == "semantic_scholar"
    assert fm["tags"] == ["rag", "llm"]
    assert "Self-RAG" in body

    metadata = json.loads(
        (project / "literature-kb" / "01_Raw" / "metadata" / f"{paper_id}.json").read_text(
            encoding="utf-8"
        )
    )
    assert metadata["source"] == "semantic_scholar"
    assert metadata["semantic_scholar_id"] == SELF_RAG_PAPER_ID

    log = (project / "literature-kb" / "00_System" / "log.md").read_text(encoding="utf-8")
    assert f"add-literature ss add id={paper_id}" in log


def test_add_ss_with_api_key_sends_auth_header(
    project: Path,
    runner: CliRunner,
    respx_mock: respx.MockRouter,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("S2_API_KEY", "test-key-value")
    route = respx_mock.get(f"{SEMANTIC_SCHOLAR_BASE_URL}/{SELF_RAG_PAPER_ID}").mock(
        return_value=httpx.Response(200, json=_ss_payload()),
    )

    result = runner.invoke(
        app,
        ["add-literature", "--ss", SELF_RAG_PAPER_ID, "--root", str(project)],
    )

    assert result.exit_code == 0, result.output
    assert route.called
    assert route.calls.last.request.headers["x-api-key"] == "test-key-value"


def test_add_ss_rejects_manual_metadata_overrides(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--ss",
            SELF_RAG_PAPER_ID,
            "--title",
            "Hand Override",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code != 0
    assert "--manual" in result.output


def test_add_ss_fetch_404_writes_nothing(
    project: Path, runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    missing_id = "0" * 40
    respx_mock.get(f"{SEMANTIC_SCHOLAR_BASE_URL}/{missing_id}").mock(
        return_value=httpx.Response(404, json={"error": "Paper not found"}),
    )

    result = runner.invoke(
        app,
        ["add-literature", "--ss", missing_id, "--root", str(project)],
    )

    assert result.exit_code != 0
    assert "Semantic Scholar" in result.output or "ss" in result.output.lower()

    papers_dir = project / "literature-kb" / "02_Literature" / "Papers"
    metadata_dir = project / "literature-kb" / "01_Raw" / "metadata"
    assert [p for p in papers_dir.glob("*.md") if p.name != ".gitkeep"] == []
    assert [p for p in metadata_dir.glob("*.json") if p.name != ".gitkeep"] == []


def test_add_ss_fetch_429_reports_rate_limit(
    project: Path, runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    respx_mock.get(f"{SEMANTIC_SCHOLAR_BASE_URL}/{SELF_RAG_PAPER_ID}").mock(
        return_value=httpx.Response(429, json={"error": "rate limited"}),
    )

    result = runner.invoke(
        app,
        ["add-literature", "--ss", SELF_RAG_PAPER_ID, "--root", str(project)],
    )

    assert result.exit_code != 0
    assert "429" in result.output
    assert "S2_API_KEY" in result.output


def test_add_ss_accepts_url_form(
    project: Path, runner: CliRunner, respx_mock: respx.MockRouter
) -> None:
    route = respx_mock.get(f"{SEMANTIC_SCHOLAR_BASE_URL}/{SELF_RAG_PAPER_ID}").mock(
        return_value=httpx.Response(200, json=_ss_payload()),
    )

    result = runner.invoke(
        app,
        [
            "add-literature",
            "--ss",
            f"https://www.semanticscholar.org/paper/Self-RAG/{SELF_RAG_PAPER_ID}",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code == 0, result.output
    assert route.called


def test_add_ss_mutually_exclusive_with_openalex(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--ss",
            SELF_RAG_PAPER_ID,
            "--openalex",
            "W4385545131",
            "--root",
            str(project),
        ],
    )

    assert result.exit_code != 0
    assert "exactly one" in result.output
    assert "--ss" in result.output


def test_add_manual_with_ss_remains_manual(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "Manual SS Paper",
            "--authors",
            "Alice A",
            "--year",
            "2024",
            "--ss",
            SELF_RAG_PAPER_ID,
            "--root",
            str(project),
        ],
    )

    assert result.exit_code == 0, result.output
    paper = project / "literature-kb" / "02_Literature" / "Papers" / "a-2024-manual-ss-paper.md"
    fm, _ = read_frontmatter(paper)
    assert fm is not None
    assert fm["semantic_scholar_id"] == SELF_RAG_PAPER_ID
    assert fm["source"] == "manual"


def test_add_manual_with_invalid_ss_rejects(project: Path, runner: CliRunner) -> None:
    # Manual entry runs PaperFrontmatter validation, which enforces the
    # 40-hex pattern; supplying garbage through --manual --ss must fail
    # before anything lands on disk.
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "Bad SS",
            "--authors",
            "Alice A",
            "--year",
            "2024",
            "--ss",
            "not-a-sha1",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code != 0
    assert "Semantic Scholar" in result.output


# ---------------------------------------------------------------------------
# Unit tests for the identifier normalizer
# ---------------------------------------------------------------------------
def test_normalizer_accepts_bare_paper_id() -> None:
    assert _normalize_identifier(SELF_RAG_PAPER_ID) == SELF_RAG_PAPER_ID


def test_normalizer_strips_semantic_scholar_url() -> None:
    url = f"https://www.semanticscholar.org/paper/Self-Rag/{SELF_RAG_PAPER_ID}"
    assert _normalize_identifier(url) == SELF_RAG_PAPER_ID


def test_normalizer_strips_semantic_scholar_url_with_query() -> None:
    url = f"https://www.semanticscholar.org/paper/Self-Rag/{SELF_RAG_PAPER_ID}?utm_source=test"
    assert _normalize_identifier(url) == SELF_RAG_PAPER_ID


def test_normalizer_passes_through_prefixed_aliases() -> None:
    assert _normalize_identifier("DOI:10.48550/arxiv.2310.11511") == (
        "DOI:10.48550/arxiv.2310.11511"
    )
    assert _normalize_identifier("ARXIV:2310.11511") == "ARXIV:2310.11511"
    assert _normalize_identifier("CorpusId:263336427") == "CorpusId:263336427"


def test_normalizer_autowraps_bare_doi() -> None:
    assert _normalize_identifier("10.48550/arxiv.2310.11511") == ("DOI:10.48550/arxiv.2310.11511")


def test_normalizer_autowraps_bare_arxiv() -> None:
    assert _normalize_identifier("2310.11511") == "ARXIV:2310.11511"


def test_normalizer_rejects_garbage() -> None:
    with pytest.raises(FetcherError):
        _normalize_identifier("not-a-paper-id")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ss_payload() -> dict[str, object]:
    return {
        "paperId": SELF_RAG_PAPER_ID,
        "title": "Self-RAG",
        "authors": [
            {"authorId": "1745924", "name": "Akari Asai"},
            {"authorId": "1745925", "name": "Zeqiu Wu"},
        ],
        "year": 2023,
        "venue": "arXiv.org",
        "url": f"https://www.semanticscholar.org/paper/{SELF_RAG_PAPER_ID}",
        "externalIds": {
            "DOI": "10.48550/arxiv.2310.11511",
            "ArXiv": "2310.11511",
            "CorpusId": 263336427,
        },
    }
