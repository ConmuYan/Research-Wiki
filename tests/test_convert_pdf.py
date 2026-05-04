"""Tests for ``lgrlw convert-pdf`` and the ``lgrlw.convert`` sub-package (v0.5)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.convert import list_backends
from lgrlw.convert.run import (
    convert_paper,
    list_paper_ids_with_pdf,
)
from lgrlw.convert.stub import STUB_PLACEHOLDER_HEADER


def _make_pdf(path: Path, content: bytes = b"%PDF-1.4\n") -> Path:
    path.write_bytes(content)
    return path


def _seed_with_pdf(
    project: Path,
    runner: CliRunner,
    *,
    paper_id: str,
    pdf: Path,
) -> None:
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "Example Paper",
            "--authors",
            "Jane Doe",
            "--year",
            "2024",
            "--id",
            paper_id,
            "--pdf",
            str(pdf),
            "--root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# Registry & stub backend
# ---------------------------------------------------------------------------


def test_registry_exposes_stub_and_mineru_by_default() -> None:
    backends = list_backends()
    assert "stub" in backends
    assert "mineru" in backends  # registered but heavyweight import is deferred


def test_convert_paper_with_stub_writes_placeholder(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    pdf = _make_pdf(tmp_path / "source.pdf")
    _seed_with_pdf(project, runner, paper_id="jane-2024-example", pdf=pdf)

    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    outcome = convert_paper(paths, paper_id="jane-2024-example", backend="stub", force=False)
    assert outcome.status == "converted"
    assert outcome.markdown_path is not None
    markdown = outcome.markdown_path.read_text(encoding="utf-8")
    assert markdown.startswith(STUB_PLACEHOLDER_HEADER)
    assert "jane-2024-example" in markdown

    log = (project / "literature-kb" / "00_System" / "log.md").read_text(encoding="utf-8")
    assert "convert-pdf" in log
    assert "jane-2024-example" in log


def test_convert_paper_missing_pdf_returns_skipped_no_pdf(project: Path, runner: CliRunner) -> None:
    # Seed a paper WITHOUT a PDF.
    result = runner.invoke(
        app,
        [
            "add-literature",
            "--manual",
            "--title",
            "No PDF",
            "--authors",
            "Jane Doe",
            "--year",
            "2024",
            "--id",
            "jane-2024-nopdf",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output

    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    outcome = convert_paper(paths, paper_id="jane-2024-nopdf", backend="stub", force=False)
    assert outcome.status == "skipped_no_pdf"
    assert outcome.markdown_path is None


def test_convert_paper_refuses_overwrite_without_force(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    pdf = _make_pdf(tmp_path / "source.pdf")
    _seed_with_pdf(project, runner, paper_id="jane-2024-example", pdf=pdf)

    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    first = convert_paper(paths, paper_id="jane-2024-example", backend="stub", force=False)
    assert first.status == "converted"

    second = convert_paper(paths, paper_id="jane-2024-example", backend="stub", force=False)
    assert second.status == "skipped_exists"
    assert "--force" in (second.error or "")

    replaced = convert_paper(paths, paper_id="jane-2024-example", backend="stub", force=True)
    assert replaced.status == "converted"


def test_list_paper_ids_with_pdf_returns_sorted_stems(
    project: Path, runner: CliRunner, tmp_path: Path
) -> None:
    pdf_a = _make_pdf(tmp_path / "a.pdf", content=b"%PDF-1.4\nA\n")
    pdf_b = _make_pdf(tmp_path / "b.pdf", content=b"%PDF-1.4\nB\n")
    _seed_with_pdf(project, runner, paper_id="alpha-2024-paper", pdf=pdf_a)
    _seed_with_pdf(project, runner, paper_id="bravo-2024-paper", pdf=pdf_b)

    from lgrlw.monorepo import resolve_subproject

    paths = resolve_subproject(project, None)
    ids = list_paper_ids_with_pdf(paths)
    assert ids == ["alpha-2024-paper", "bravo-2024-paper"]


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_convert_pdf_single_paper(project: Path, runner: CliRunner, tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "source.pdf")
    _seed_with_pdf(project, runner, paper_id="jane-2024-example", pdf=pdf)

    result = runner.invoke(
        app,
        [
            "convert-pdf",
            "jane-2024-example",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output
    markdown = (
        project
        / "literature-kb"
        / "01_Raw"
        / "mineru_md"
        / "jane-2024-example"
        / "jane-2024-example.md"
    )
    assert markdown.is_file()


def test_cli_convert_pdf_all(project: Path, runner: CliRunner, tmp_path: Path) -> None:
    pdf_a = _make_pdf(tmp_path / "a.pdf", content=b"%PDF-1.4\nA\n")
    pdf_b = _make_pdf(tmp_path / "b.pdf", content=b"%PDF-1.4\nB\n")
    _seed_with_pdf(project, runner, paper_id="alpha-2024-paper", pdf=pdf_a)
    _seed_with_pdf(project, runner, paper_id="bravo-2024-paper", pdf=pdf_b)

    result = runner.invoke(
        app,
        [
            "convert-pdf",
            "--all",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code == 0, result.output

    for pid in ("alpha-2024-paper", "bravo-2024-paper"):
        markdown = project / "literature-kb" / "01_Raw" / "mineru_md" / pid / f"{pid}.md"
        assert markdown.is_file()


def test_cli_convert_pdf_rejects_unknown_backend(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "convert-pdf",
            "any-id",
            "--backend",
            "nope",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code != 0
    assert "unknown backend" in result.output.lower()


def test_cli_convert_pdf_requires_target(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "convert-pdf",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code != 0
    assert "--all" in result.output or "<paper-id>" in result.output


def test_cli_convert_pdf_rejects_positional_with_all(project: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        app,
        [
            "convert-pdf",
            "some-id",
            "--all",
            "--root",
            str(project),
        ],
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output.lower()
