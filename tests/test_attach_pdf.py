"""Tests for ``lgrlw attach-pdf`` and the ``lgrlw.ingest.attach`` module (v0.4.x)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.ingest.attach import (
    attach_scan,
    attach_single,
    build_kb_index,
    match_pdf_to_paper,
)


def _make_pdf(path: Path, content: bytes = b"%PDF-1.4\n") -> Path:
    path.write_bytes(content)
    return path


def _seed_paper(
    project: Path,
    runner: CliRunner,
    *,
    paper_id: str,
    title: str = "Example Paper",
    authors: str = "Jane Doe",
    year: int = 2024,
    arxiv: str | None = None,
    doi: str | None = None,
) -> None:
    args = [
        "add-literature",
        "--manual",
        "--title",
        title,
        "--authors",
        authors,
        "--year",
        str(year),
        "--id",
        paper_id,
        "--root",
        str(project),
    ]
    if arxiv is not None:
        args.extend(["--arxiv", arxiv])
    if doi is not None:
        args.extend(["--doi", doi])
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Matcher tests (pure, no CLI)
# ---------------------------------------------------------------------------


def test_build_kb_index_captures_identifiers(project: Path, runner: CliRunner) -> None:
    _seed_paper(
        project,
        runner,
        paper_id="asai-2023-self-rag",
        title="Self-RAG",
        authors="Akari Asai",
        year=2023,
        arxiv="2310.11511",
        doi="10.48550/arXiv.2310.11511",
    )
    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    index = build_kb_index(paths)

    assert "asai-2023-self-rag" in index.paper_ids
    assert index.by_arxiv["2310.11511"] == "asai-2023-self-rag"
    # Flattened DOI lookup goes through the scan path via match_pdf_to_paper,
    # but the raw table should still contain the lower-cased DOI variants.
    assert any(paper_id == "asai-2023-self-rag" for paper_id in index.by_doi.values())


def test_match_by_paper_id_substring(project: Path, runner: CliRunner, tmp_path: Path) -> None:
    _seed_paper(project, runner, paper_id="asai-2023-self-rag")
    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    index = build_kb_index(paths)

    pdf = _make_pdf(tmp_path / "2023-asai-2023-self-rag-final.pdf")
    match = match_pdf_to_paper(pdf, index)
    assert match is not None
    assert match.paper_id == "asai-2023-self-rag"
    assert match.reason == "paper_id"


def test_match_by_arxiv_id(project: Path, runner: CliRunner, tmp_path: Path) -> None:
    _seed_paper(project, runner, paper_id="asai-2023-self-rag", arxiv="2310.11511")
    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    index = build_kb_index(paths)

    pdf = _make_pdf(tmp_path / "arxiv_2310.11511_v2.pdf")
    match = match_pdf_to_paper(pdf, index)
    assert match is not None
    assert match.paper_id == "asai-2023-self-rag"
    assert match.reason == "arxiv_id"


def test_match_by_doi_flattened_substring(project: Path, runner: CliRunner, tmp_path: Path) -> None:
    _seed_paper(
        project,
        runner,
        paper_id="lewis-2020-rag",
        title="RAG",
        authors="Patrick Lewis",
        year=2020,
        doi="10.48550/arxiv.2005.11401",
    )
    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    index = build_kb_index(paths)

    # filename uses slashes replaced by underscores; the flattened DOI
    # is 1048550arxiv200511401 which should appear inside the stem
    # as a contiguous alphanumeric substring.
    pdf = _make_pdf(tmp_path / "10_48550_arxiv_2005_11401_camera_ready.pdf")
    match = match_pdf_to_paper(pdf, index)
    assert match is not None
    assert match.paper_id == "lewis-2020-rag"
    assert match.reason == "doi"


def test_match_returns_none_for_unknown_pdf(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    _seed_paper(project, runner, paper_id="asai-2023-self-rag")
    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    index = build_kb_index(paths)

    pdf = _make_pdf(tmp_path / "something-else-entirely.pdf")
    assert match_pdf_to_paper(pdf, index) is None


# ---------------------------------------------------------------------------
# attach_single / attach_scan API
# ---------------------------------------------------------------------------


def test_attach_single_archives_and_logs(project: Path, runner: CliRunner, tmp_path: Path) -> None:
    _seed_paper(project, runner, paper_id="jane-2024-example")
    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    pdf = _make_pdf(tmp_path / "source.pdf", content=b"%PDF-1.4\nfoo\n")

    outcome = attach_single(
        paths,
        paper_id="jane-2024-example",
        pdf_path=pdf,
        force_pdf=False,
    )
    assert outcome.status == "archived"
    assert outcome.archived is not None
    assert outcome.archived.is_file()
    assert outcome.archived.read_bytes() == pdf.read_bytes()

    log = (project / "literature-kb" / "00_System" / "log.md").read_text(encoding="utf-8")
    assert "attach-pdf" in log
    assert "jane-2024-example" in log


def test_attach_single_rejects_unknown_paper(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    pdf = _make_pdf(tmp_path / "source.pdf")

    outcome = attach_single(
        paths,
        paper_id="ghost-paper",
        pdf_path=pdf,
        force_pdf=False,
    )
    assert outcome.status == "skipped_error"
    assert "does not exist" in (outcome.error or "")


def test_attach_single_refuses_overwrite_without_force_pdf(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    _seed_paper(project, runner, paper_id="jane-2024-example")
    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    first = _make_pdf(tmp_path / "first.pdf", content=b"%PDF-1.4\nfirst\n")
    second = _make_pdf(tmp_path / "second.pdf", content=b"%PDF-1.4\nsecond\n")

    assert (
        attach_single(paths, paper_id="jane-2024-example", pdf_path=first, force_pdf=False).status
        == "archived"
    )

    collide = attach_single(paths, paper_id="jane-2024-example", pdf_path=second, force_pdf=False)
    assert collide.status == "already_attached"
    assert (paths.kb_raw_pdf / "jane-2024-example.pdf").read_bytes() == first.read_bytes()

    replaced = attach_single(paths, paper_id="jane-2024-example", pdf_path=second, force_pdf=True)
    assert replaced.status == "archived"
    assert (paths.kb_raw_pdf / "jane-2024-example.pdf").read_bytes() == second.read_bytes()


def test_attach_single_move_removes_source(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    _seed_paper(project, runner, paper_id="jane-2024-example")
    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    pdf = _make_pdf(tmp_path / "source.pdf")

    outcome = attach_single(
        paths,
        paper_id="jane-2024-example",
        pdf_path=pdf,
        force_pdf=False,
        remove_source=True,
    )
    assert outcome.status == "archived"
    assert not pdf.exists()


def test_attach_scan_matches_multiple_pdfs(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    _seed_paper(
        project,
        runner,
        paper_id="asai-2023-self-rag",
        arxiv="2310.11511",
    )
    _seed_paper(
        project,
        runner,
        paper_id="lewis-2020-rag",
        authors="Patrick Lewis",
        year=2020,
        arxiv="2005.11401",
    )
    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    scan_dir = tmp_path / "inbox"
    scan_dir.mkdir()
    _make_pdf(scan_dir / "2310.11511.pdf", content=b"%PDF-1.4\nasai\n")
    _make_pdf(scan_dir / "lewis-2020-rag.pdf", content=b"%PDF-1.4\nlewis\n")
    _make_pdf(scan_dir / "unrelated_paper.pdf", content=b"%PDF-1.4\nnope\n")

    results = attach_scan(paths, scan_dir, force_pdf=False, remove_source=False)
    statuses = {r.source.name: r.status for r in results}
    assert statuses == {
        "2310.11511.pdf": "archived",
        "lewis-2020-rag.pdf": "archived",
        "unrelated_paper.pdf": "unmatched",
    }

    archive_dir = paths.kb_raw_pdf
    assert (archive_dir / "asai-2023-self-rag.pdf").is_file()
    assert (archive_dir / "lewis-2020-rag.pdf").is_file()


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_attach_pdf_explicit_mode(project: Path, runner: CliRunner, tmp_path: Path) -> None:
    _seed_paper(project, runner, paper_id="jane-2024-example")
    pdf = _make_pdf(tmp_path / "source.pdf")

    result = runner.invoke(
        app,
        [
            "attach-pdf",
            str(pdf),
            "--id",
            "jane-2024-example",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (project / "literature-kb" / "01_Raw" / "pdf" / "jane-2024-example.pdf").is_file()


def test_cli_attach_pdf_scan_incoming(project: Path, runner: CliRunner) -> None:
    _seed_paper(project, runner, paper_id="jane-2024-example")
    incoming = project / "literature-kb" / "01_Raw" / "pdf" / "_incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    _make_pdf(incoming / "jane-2024-example.pdf")

    result = runner.invoke(
        app,
        [
            "attach-pdf",
            "--scan-incoming",
            "--move",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (project / "literature-kb" / "01_Raw" / "pdf" / "jane-2024-example.pdf").is_file()
    # --move deletes the inbox copy.
    assert not (incoming / "jane-2024-example.pdf").exists()


def test_cli_attach_pdf_rejects_conflicting_flags(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    pdf = _make_pdf(tmp_path / "source.pdf")
    incoming = project / "literature-kb" / "01_Raw" / "pdf" / "_incoming"
    incoming.mkdir(parents=True, exist_ok=True)

    result = runner.invoke(
        app,
        [
            "attach-pdf",
            str(pdf),
            "--id",
            "x",
            "--scan-incoming",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code != 0
    assert "incompatible" in result.output.lower()


def test_cli_attach_pdf_requires_mode(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        ["attach-pdf", "--root", str(project)],
    )
    assert result.exit_code != 0
    assert "--id" in result.output or "--scan" in result.output
