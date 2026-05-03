"""End-to-end guide-style integration test.

This single test walks the exact happy-path sequence a first-time user
would follow when reading `README.md` Quick Start + `docs/cli-reference.md`
top-to-bottom:

1. ``lgrlw init``
2. ``lgrlw new-workspace``
3. Four ``lgrlw add-literature`` invocations, one per v0.2 source
   (DOI, arXiv, OpenAlex, Semantic Scholar). Each goes through the
   ``--manual`` path so the test stays deterministic and never touches
   the network; the four corresponding ``--<source>`` fetch paths are
   already covered by the per-fetcher respx-mocked tests.
4. ``lgrlw export-pack``
5. Promotion preconditions are seeded directly on disk.
6. ``lgrlw promote``
7. ``lgrlw lint`` must come out green across the resulting KB.

If any of the CLI surfaces changes (option spelling, default value,
artefact path), this test fails loudly and points at the regression in
the documented Quick Start flow.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fs import read_frontmatter, write_frontmatter


def _run(runner: CliRunner, *args: object) -> None:
    result = runner.invoke(app, [str(a) for a in args])
    assert result.exit_code == 0, f"args={args!r}\noutput=\n{result.output}"


def test_readme_quickstart_end_to_end(tmp_path: Path, runner: CliRunner) -> None:
    root = tmp_path / "my-research"

    # 1) lgrlw init -------------------------------------------------------
    _run(runner, "init", root, "--direction", "efficient-llm-inference")
    assert (root / ".lgrlw.toml").is_file()
    assert (root / "literature-kb").is_dir()
    assert (root / "research-workspaces").is_dir()

    # 2) lgrlw new-workspace ---------------------------------------------
    _run(
        runner,
        "new-workspace",
        "paper_001",
        "--kind",
        "paper",
        "--title",
        "A working title",
        "--root",
        root,
    )
    workspace = root / "research-workspaces" / "paper_001"
    assert workspace.is_dir()
    status_path = workspace / "00_Project" / "paper_status.md"
    assert status_path.is_file()

    # 3) Four add-literature entries via --manual (deterministic; the
    #    networked --doi/--arxiv/--openalex/--ss paths are exercised by
    #    the per-fetcher respx-mocked tests).
    _run(
        runner,
        "add-literature",
        "--manual",
        "--title",
        "DOI Paper",
        "--authors",
        "Alice A",
        "--year",
        "2024",
        "--venue",
        "ICLR 2024",
        "--doi",
        "10.5555/demo-doi",
        "--root",
        root,
    )
    _run(
        runner,
        "add-literature",
        "--manual",
        "--title",
        "arXiv Paper",
        "--authors",
        "Bob B",
        "--year",
        "2024",
        "--arxiv",
        "2401.00001",
        "--root",
        root,
    )
    _run(
        runner,
        "add-literature",
        "--manual",
        "--title",
        "OpenAlex Paper",
        "--authors",
        "Carol C",
        "--year",
        "2024",
        "--openalex",
        "W4385545131",
        "--root",
        root,
    )
    _run(
        runner,
        "add-literature",
        "--manual",
        "--title",
        "Semantic Scholar Paper",
        "--authors",
        "Dave D",
        "--year",
        "2024",
        "--ss",
        "649def34f8be52c8b66281af98ae884c09aef38b",
        "--root",
        root,
    )
    papers_dir = root / "literature-kb" / "02_Literature" / "Papers"
    cards = sorted(p.name for p in papers_dir.glob("*.md") if p.name != ".gitkeep")
    assert cards == [
        "a-2024-doi-paper.md",
        "b-2024-arxiv-paper.md",
        "c-2024-openalex-paper.md",
        "d-2024-semantic-scholar-paper.md",
    ]

    # Each identifier survived into its dedicated frontmatter field.
    doi_fm, _ = read_frontmatter(papers_dir / "a-2024-doi-paper.md")
    assert doi_fm is not None and doi_fm["doi"] == "10.5555/demo-doi"
    arxiv_fm, _ = read_frontmatter(papers_dir / "b-2024-arxiv-paper.md")
    assert arxiv_fm is not None and arxiv_fm["arxiv_id"] == "2401.00001"
    oa_fm, _ = read_frontmatter(papers_dir / "c-2024-openalex-paper.md")
    assert oa_fm is not None and oa_fm["openalex_id"] == "W4385545131"
    ss_fm, _ = read_frontmatter(papers_dir / "d-2024-semantic-scholar-paper.md")
    assert ss_fm is not None and ss_fm["semantic_scholar_id"] == (
        "649def34f8be52c8b66281af98ae884c09aef38b"
    )

    # 4) lgrlw export-pack ----------------------------------------------
    _run(runner, "export-pack", "paper_001", "--root", root)
    export_root = root / "literature-kb" / "06_Exports"
    packs = [p for p in export_root.iterdir() if p.is_dir()]
    assert len(packs) == 1, packs
    pack = packs[0]
    manifest_path = pack / "export_manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["workspace_id"] == "paper_001"
    assert set(manifest["paper_ids"]) == {
        "a-2024-doi-paper",
        "b-2024-arxiv-paper",
        "c-2024-openalex-paper",
        "d-2024-semantic-scholar-paper",
    }

    # 5) Seed the promote preconditions directly on disk. In real use the
    #    author edits these files by hand after acceptance; we mirror that
    #    editing programmatically so the test stays reproducible.
    status_fm, status_body = read_frontmatter(status_path)
    assert status_fm is not None
    status_fm.update(
        {
            "status": "accepted",
            "final_title": "A Working Title",
            "final_authors": ["Alice Guide", "Bob Guide"],
            "venue": "ICLR 2026",
            "year": 2026,
            "doi": "10.5555/guide-accepted",
        }
    )
    write_frontmatter(status_path, status_fm, status_body)

    promotion = workspace / "06_Promotion"
    (promotion / "final_metadata.md").write_text(
        "# Final metadata\n\nCamera-ready: https://example.com/papers/guide.pdf\n",
        encoding="utf-8",
    )
    checklist = promotion / "promotion_checklist.md"
    checklist.write_text(
        checklist.read_text(encoding="utf-8").replace("- [ ]", "- [x]"),
        encoding="utf-8",
    )
    (promotion / "add_back_to_kb_plan.md").write_text(
        "# Add-back-to-KB plan\n\n"
        "- Cite the accepted paper from 03_Field_Structure/method_taxonomy.md.\n"
        "- Add a row to 05_Evidence/claims.md summarising the main claim.\n",
        encoding="utf-8",
    )

    # 6) lgrlw promote --------------------------------------------------
    _run(runner, "promote", "paper_001", "--root", root)
    # `paper_slug` picks the last whitespace-separated token of the first
    # final author as the "last name" portion of the slug.
    promoted_id = "guide-2026-a-working-title"
    promoted_card = papers_dir / f"{promoted_id}.md"
    assert promoted_card.is_file()
    promoted_fm, _ = read_frontmatter(promoted_card)
    assert promoted_fm is not None
    assert promoted_fm["source"] == "promoted"
    assert promoted_fm["status"] == "accepted"
    bibtex = root / "literature-kb" / "01_Raw" / "bibtex" / f"{promoted_id}.bib"
    assert bibtex.is_file()
    assert bibtex.read_text(encoding="utf-8").startswith(f"@inproceedings{{{promoted_id},")

    log = (root / "literature-kb" / "00_System" / "log.md").read_text(encoding="utf-8")
    assert "add-literature manual add id=a-2024-doi-paper" in log
    assert "add-literature manual add id=b-2024-arxiv-paper" in log
    assert "add-literature manual add id=c-2024-openalex-paper" in log
    assert "add-literature manual add id=d-2024-semantic-scholar-paper" in log
    assert f"promote workspace=paper_001 id={promoted_id}" in log

    # 7) lgrlw lint -----------------------------------------------------
    lint_result = runner.invoke(app, ["lint", "--root", str(root)])
    assert lint_result.exit_code == 0, lint_result.output
    assert "all checks passed" in lint_result.output
