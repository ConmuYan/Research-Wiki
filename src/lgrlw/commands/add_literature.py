"""``lgrlw add-literature`` -- register a new paper in the KB.

v0.1 supports ``--manual`` only. Networked fetchers (``--arxiv`` / ``--doi``
/ ``--ss``) are scheduled for v0.2 and intentionally not wired up here.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from slugify import slugify

from lgrlw.fs import ensure_dir, write_frontmatter
from lgrlw.paths import ProjectPaths, resolve_project
from lgrlw.render.paper_card import render_paper_card
from lgrlw.schemas import PaperFrontmatter, PaperKind, PaperStatus

console = Console()


def add_literature_command(
    manual: Annotated[
        bool,
        typer.Option(
            "--manual",
            help=("Required in v0.1. Networked fetchers (--arxiv / --doi / --ss) land in v0.2."),
        ),
    ] = False,
    title: Annotated[str, typer.Option("--title", help="Paper title.")] = "",
    authors: Annotated[
        str,
        typer.Option(
            "--authors",
            help="Comma-separated author list (e.g. 'First Last, Another Name').",
        ),
    ] = "",
    year: Annotated[int, typer.Option("--year", help="Publication year.")] = 0,
    venue: Annotated[str | None, typer.Option("--venue", help="Venue or journal.")] = None,
    doi: Annotated[str | None, typer.Option("--doi", help="DOI (e.g. 10.1000/foo).")] = None,
    arxiv: Annotated[
        str | None,
        typer.Option(
            "--arxiv",
            help="arXiv id (stored as metadata only in v0.1; not fetched).",
        ),
    ] = None,
    url: Annotated[str | None, typer.Option("--url", help="Canonical URL.")] = None,
    status: Annotated[
        PaperStatus,
        typer.Option("--status", help="Publication status."),
    ] = PaperStatus.published,
    tags: Annotated[
        str | None,
        typer.Option("--tags", help="Comma-separated tags."),
    ] = None,
    paper_id: Annotated[
        str | None,
        typer.Option("--id", help="Override the generated slug id."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Overwrite an existing paper card and metadata with the same id.",
        ),
    ] = False,
    root: Annotated[
        Path | None,
        typer.Option("--root", help="Project root (auto-detect if omitted)."),
    ] = None,
) -> None:
    """Add a manual literature entry to the KB."""
    if not manual:
        console.print(
            "[red]error[/red] v0.1 requires --manual. "
            "Networked fetchers (--arxiv / --doi / --ss) ship in v0.2."
        )
        raise typer.Exit(code=1)

    missing = [
        flag
        for flag, value in (("--title", title), ("--authors", authors), ("--year", year))
        if not value
    ]
    if missing:
        console.print(f"[red]error[/red] manual entry requires {', '.join(missing)}")
        raise typer.Exit(code=1)

    paths = resolve_project(root)

    authors_list = _split_csv(authors)
    if not authors_list:
        console.print("[red]error[/red] --authors must contain at least one name")
        raise typer.Exit(code=1)
    tags_list = _split_csv(tags or "")

    generated_id = paper_id or _slug_for(authors_list[0], year, title)

    try:
        fm = PaperFrontmatter(
            id=generated_id,
            title=title,
            authors=authors_list,
            year=year,
            venue=venue,
            doi=doi,
            arxiv_id=arxiv,
            url=url,
            status=status,
            source=PaperKind.manual,
            added_on=date.today(),
            tags=tags_list,
        )
    except ValueError as exc:
        console.print(f"[red]error[/red] invalid paper metadata: {exc}")
        raise typer.Exit(code=1) from exc

    ensure_dir(paths.kb_papers)
    paper_path = paths.kb_papers / f"{generated_id}.md"
    paper_exists = paper_path.exists()
    if paper_exists and not force:
        console.print(f"[red]error[/red] paper id {generated_id!r} already exists at {paper_path}")
        console.print("       re-run with --force to replace it")
        raise typer.Exit(code=1)

    frontmatter_dict = fm.model_dump(mode="json", exclude_none=True)
    body = render_paper_card(fm)
    write_frontmatter(paper_path, frontmatter_dict, body)

    ensure_dir(paths.kb_raw_metadata)
    meta_path = paths.kb_raw_metadata / f"{generated_id}.json"
    meta_path.write_text(
        json.dumps(frontmatter_dict, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    action = "replace" if force and paper_exists else "add"
    _append_log(paths, f"add-literature manual {action} id={generated_id}")

    console.print(f"[green]added[/green] {generated_id}")
    console.print(f"  card     : {paper_path.relative_to(paths.root)}")
    console.print(f"  metadata : {meta_path.relative_to(paths.root)}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _split_csv(raw: str) -> list[str]:
    return [token.strip() for token in raw.split(",") if token.strip()]


def _slug_for(first_author: str, year: int, title: str) -> str:
    parts = first_author.replace(",", " ").split()
    last_name = parts[-1] if parts else "anon"
    seed = f"{last_name}-{year}-{title}"
    return (
        slugify(
            seed,
            max_length=60,
            lowercase=True,
            regex_pattern=r"[^a-z0-9-]",
        )
        or "paper"
    )


def _append_log(paths: ProjectPaths, message: str) -> None:
    ensure_dir(paths.kb_system)
    log = paths.kb_system / "log.md"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"- {timestamp}  {message}\n"
    if log.is_file():
        with log.open("a", encoding="utf-8") as f:
            f.write(entry)
    else:
        log.write_text(f"# KB Log\n\n{entry}", encoding="utf-8")


__all__ = ["add_literature_command"]
