"""Tests for ``lgrlw import-bib`` and its underlying ingest module (v0.4)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fs import read_frontmatter
from lgrlw.ingest import BibEntry, find_pdf_candidate, parse_bib

FIXTURES = Path(__file__).parent / "fixtures"


def _make_pdf(path: Path, content: bytes = b"%PDF-1.4\n") -> Path:
    path.write_bytes(content)
    return path


# ---------------------------------------------------------------------------
# Pure-parser tests
# ---------------------------------------------------------------------------


def test_parse_bib_extracts_core_fields() -> None:
    entries = parse_bib(FIXTURES / "sample_import.bib")

    by_key = {entry.cite_key: entry for entry in entries}

    lewis = by_key["lewis2020rag"]
    assert lewis.entry_type == "inproceedings"
    assert lewis.title.startswith("Retrieval-Augmented Generation")
    assert lewis.authors == [
        "Patrick Lewis",
        "Ethan Perez",
        "Aleksandra Piktus",
    ]
    assert lewis.year == 2020
    assert lewis.venue == "NeurIPS"
    assert lewis.arxiv_id == "2005.11401"
    assert lewis.doi == "10.48550/arXiv.2005.11401"

    asai = by_key["asai2023selfrag"]
    assert asai.authors[0] == "Akari Asai"
    assert asai.arxiv_id == "2310.11511"
    # Self-RAG keeps the braces' case-protected casing.
    assert "Self-RAG" in asai.title

    broken = by_key["broken"]
    assert broken.title == "Missing Author and Year"
    assert broken.authors == []
    assert broken.year is None


def test_parse_bib_normalises_authors_without_commas() -> None:
    entries = parse_bib(FIXTURES / "sample_import.bib")
    lewis = next(e for e in entries if e.cite_key == "lewis2020rag")
    # Already "First Last" form in the fixture; must be preserved.
    assert lewis.authors == ["Patrick Lewis", "Ethan Perez", "Aleksandra Piktus"]


# ---------------------------------------------------------------------------
# PDF match helper
# ---------------------------------------------------------------------------


def test_find_pdf_candidate_matches_arxiv_id_first(tmp_path: Path) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    arxiv_pdf = _make_pdf(pdf_dir / "2310.11511.pdf")
    _make_pdf(pdf_dir / "unrelated.pdf")

    entry = BibEntry(
        cite_key="asai2023selfrag",
        entry_type="article",
        title="Self-RAG",
        authors=["Akari Asai"],
        year=2023,
        venue=None,
        doi=None,
        arxiv_id="2310.11511",
        openalex_id=None,
        semantic_scholar_id=None,
        url=None,
        abstract=None,
    )

    match = find_pdf_candidate(entry, pdf_dir)
    assert match == arxiv_pdf


def test_find_pdf_candidate_falls_back_to_cite_key(tmp_path: Path) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    key_pdf = _make_pdf(pdf_dir / "asai2023selfrag_main.pdf")

    entry = BibEntry(
        cite_key="asai2023selfrag",
        entry_type="article",
        title="Self-RAG",
        authors=["Akari Asai"],
        year=2023,
        venue=None,
        doi=None,
        arxiv_id=None,
        openalex_id=None,
        semantic_scholar_id=None,
        url=None,
        abstract=None,
    )

    assert find_pdf_candidate(entry, pdf_dir) == key_pdf


def test_find_pdf_candidate_returns_none_when_no_match(tmp_path: Path) -> None:
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    _make_pdf(pdf_dir / "totally-unrelated.pdf")

    entry = BibEntry(
        cite_key="asai2023selfrag",
        entry_type="article",
        title="Self-RAG",
        authors=["Akari Asai"],
        year=2023,
        venue=None,
        doi=None,
        arxiv_id="2310.11511",
        openalex_id=None,
        semantic_scholar_id=None,
        url=None,
        abstract=None,
    )

    assert find_pdf_candidate(entry, pdf_dir) is None


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_import_bib_dry_run_writes_nothing(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "import-bib",
            str(FIXTURES / "sample_import.bib"),
            "--root",
            str(project),
            "--dry-run",
        ],
    )
    # Broken entry makes exit code non-zero (skipped_error), but no files
    # should have been written.
    assert "would_import" in result.output

    papers_dir = project / "literature-kb" / "02_Literature" / "Papers"
    papers = [p for p in papers_dir.glob("*.md") if p.name != ".gitkeep"]
    assert not papers

    imports_dir = project / "literature-kb" / "01_Raw" / "imports"
    assert not imports_dir.exists() or not any(imports_dir.iterdir())


def test_import_bib_creates_cards_and_manifest(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "import-bib",
            str(FIXTURES / "sample_import.bib"),
            "--root",
            str(project),
        ],
    )
    # The broken entry triggers a non-zero exit but valid entries are still
    # written.
    papers_dir = project / "literature-kb" / "02_Literature" / "Papers"
    papers = sorted(p.stem for p in papers_dir.glob("*.md") if p.name != ".gitkeep")
    assert len(papers) == 3
    assert any("lewis" in stem and "2020" in stem for stem in papers)

    # Manifest exists and enumerates every bib entry.
    imports_dir = project / "literature-kb" / "01_Raw" / "imports"
    runs = list(imports_dir.iterdir())
    assert len(runs) == 1
    run = runs[0]
    manifest_path = run / "manifest.json"
    assert manifest_path.is_file()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"].endswith("_bib_import")
    assert manifest["dry_run"] is False
    assert manifest["counts"]["imported"] == 3
    assert manifest["counts"]["skipped_error"] == 1

    # Source bib is archived alongside the manifest.
    assert (run / "source.bib").is_file()

    # Resulting paper card validates against schema.
    lewis = next(p for p in papers_dir.glob("*.md") if "lewis" in p.stem)
    fm, _ = read_frontmatter(lewis)
    assert fm is not None
    assert fm["arxiv_id"] == "2005.11401"
    assert fm["type"] == "paper"

    # Broken entry surfaces via exit code.
    assert result.exit_code != 0


def test_import_bib_skip_duplicate_does_not_force(project: Path, runner: CliRunner) -> None:
    bib = FIXTURES / "sample_import.bib"

    # First run imports everything.
    runner.invoke(app, ["import-bib", str(bib), "--root", str(project)])

    # Second run must detect duplicates and skip.
    result = runner.invoke(
        app,
        ["import-bib", str(bib), "--root", str(project), "--on-duplicate", "skip"],
    )
    imports_dir = project / "literature-kb" / "01_Raw" / "imports"
    runs = sorted(imports_dir.iterdir())
    assert len(runs) == 2

    manifest = json.loads((runs[1] / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["skipped_duplicate"] == 3
    assert manifest["counts"]["imported"] == 0
    # Broken entry still errors.
    assert manifest["counts"]["skipped_error"] == 1

    # Exit code non-zero because of the broken entry.
    assert result.exit_code != 0


def test_import_bib_on_duplicate_fail_aborts_before_writes(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    bib = FIXTURES / "sample_import.bib"

    # Pre-populate one entry to trigger duplicate detection.
    runner.invoke(
        app,
        [
            "add-literature",
            "--arxiv",
            "2005.11401",
            "--manual",
            "--title",
            "Retrieval-Augmented Generation",
            "--authors",
            "Patrick Lewis",
            "--year",
            "2020",
            "--root",
            str(project),
        ],
    )

    result = runner.invoke(
        app,
        ["import-bib", str(bib), "--root", str(project), "--on-duplicate", "fail"],
    )
    assert result.exit_code != 0
    assert "on_duplicate" in result.output.lower() or "fail" in result.output.lower()

    # Nothing written for this run: no imports dir has been touched.
    imports_dir = project / "literature-kb" / "01_Raw" / "imports"
    assert not imports_dir.exists() or not any(imports_dir.iterdir())


def test_import_bib_with_pdf_dir_archives_matching_pdfs(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    pdf_dir = tmp_path / "papers"
    pdf_dir.mkdir()
    _make_pdf(pdf_dir / "2005.11401.pdf", content=b"%PDF-1.4\nLewis\n")
    _make_pdf(pdf_dir / "asai2023selfrag.pdf", content=b"%PDF-1.4\nAsai\n")
    # No match for the karpukhin entry.

    runner.invoke(
        app,
        [
            "import-bib",
            str(FIXTURES / "sample_import.bib"),
            "--root",
            str(project),
            "--pdf-dir",
            str(pdf_dir),
        ],
    )

    archive_dir = project / "literature-kb" / "01_Raw" / "pdf"
    archived = sorted(p.name for p in archive_dir.glob("*.pdf"))
    assert len(archived) == 2

    # Manifest records pdf_source correctly.
    imports_dir = project / "literature-kb" / "01_Raw" / "imports"
    manifest = json.loads(
        (next(imports_dir.iterdir()) / "manifest.json").read_text(encoding="utf-8")
    )
    pdf_states = {row["cite_key"]: row["pdf_source"] for row in manifest["entries"]}
    assert pdf_states["lewis2020rag"] == "local"
    assert pdf_states["asai2023selfrag"] == "local"
    assert pdf_states["karpukhin2020dpr"] == "none"
    assert pdf_states["broken"] == "none"
