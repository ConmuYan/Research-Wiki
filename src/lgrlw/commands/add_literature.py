"""``lgrlw add-literature`` -- register a new paper in the KB."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console
from slugify import slugify

from lgrlw.fetchers import ArxivFetcher, CrossrefFetcher, FetcherError
from lgrlw.fs import ensure_dir, write_frontmatter
from lgrlw.paths import ProjectPaths, resolve_project
from lgrlw.render.paper_card import render_paper_card
from lgrlw.schemas import PaperFrontmatter, PaperKind, PaperMetadata, PaperStatus

console = Console()


def add_literature_command(
    manual: Annotated[
        bool,
        typer.Option(
            "--manual",
            help="Create a hand-entered literature record.",
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
    doi: Annotated[
        str | None,
        typer.Option(
            "--doi",
            help="DOI. With --manual, stored as metadata; without --manual, fetched from Crossref.",
        ),
    ] = None,
    arxiv: Annotated[
        str | None,
        typer.Option(
            "--arxiv",
            help="arXiv id. With --manual, stored as metadata; without --manual, fetched from arXiv.",
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
    """Add a literature entry to the KB."""
    mode = _select_mode(manual, doi, arxiv)
    paths = resolve_project(root)
    tags_list = _split_csv(tags or "")

    if mode == "manual":
        fm = _manual_frontmatter(
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            doi=doi,
            arxiv=arxiv,
            url=url,
            status=status,
            tags=tags_list,
            paper_id=paper_id,
        )
        source_label = "manual"
    elif mode == "doi":
        _reject_fetch_mode_overrides(
            mode=mode,
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            url=url,
        )
        metadata = _fetch_doi_metadata(doi or "")
        fm = _fetched_frontmatter(metadata, status=status, tags=tags_list, paper_id=paper_id)
        source_label = "doi"
    else:
        _reject_fetch_mode_overrides(
            mode=mode,
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            url=url,
        )
        metadata = _fetch_arxiv_metadata(arxiv or "")
        fm = _fetched_frontmatter(metadata, status=status, tags=tags_list, paper_id=paper_id)
        source_label = "arxiv"

    _write_literature_entry(paths, fm, force=force, source_label=source_label)


def _select_mode(
    manual: bool,
    doi: str | None,
    arxiv: str | None,
) -> Literal["manual", "doi", "arxiv"]:
    if manual:
        return "manual"
    sources = [name for name, value in (("doi", doi), ("arxiv", arxiv)) if value]
    if sources == ["doi"]:
        return "doi"
    if sources == ["arxiv"]:
        return "arxiv"
    if len(sources) > 1:
        console.print("[red]error[/red] provide exactly one network source: --doi or --arxiv")
        console.print("       use --manual to store multiple identifiers as hand-entered metadata")
        raise typer.Exit(code=1)
    console.print("[red]error[/red] provide a literature source: --manual, --doi, or --arxiv")
    raise typer.Exit(code=1)


def _manual_frontmatter(
    *,
    title: str,
    authors: str,
    year: int,
    venue: str | None,
    doi: str | None,
    arxiv: str | None,
    url: str | None,
    status: PaperStatus,
    tags: list[str],
    paper_id: str | None,
) -> PaperFrontmatter:
    missing = [
        flag
        for flag, value in (("--title", title), ("--authors", authors), ("--year", year))
        if not value
    ]
    if missing:
        console.print(f"[red]error[/red] manual entry requires {', '.join(missing)}")
        raise typer.Exit(code=1)

    authors_list = _split_csv(authors)
    if not authors_list:
        console.print("[red]error[/red] --authors must contain at least one name")
        raise typer.Exit(code=1)

    generated_id = paper_id or _slug_for(authors_list[0], year, title)

    try:
        return PaperFrontmatter(
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
            tags=tags,
        )
    except ValueError as exc:
        console.print(f"[red]error[/red] invalid paper metadata: {exc}")
        raise typer.Exit(code=1) from exc


def _reject_fetch_mode_overrides(
    *,
    mode: Literal["doi", "arxiv"],
    title: str,
    authors: str,
    year: int,
    venue: str | None,
    url: str | None,
) -> None:
    provided = []
    if title:
        provided.append("--title")
    if authors:
        provided.append("--authors")
    if year:
        provided.append("--year")
    if venue is not None:
        provided.append("--venue")
    if url is not None:
        provided.append("--url")
    if provided:
        console.print(
            f"[red]error[/red] --{mode} fetch mode does not accept "
            f"{', '.join(provided)}; use --manual for hand-entered metadata"
        )
        raise typer.Exit(code=1)


def _fetch_doi_metadata(doi: str) -> PaperMetadata:
    fetcher = CrossrefFetcher()
    try:
        return fetcher.fetch(doi)
    except FetcherError as exc:
        console.print(f"[red]error[/red] DOI fetch failed: {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        fetcher.close()


def _fetch_arxiv_metadata(arxiv: str) -> PaperMetadata:
    fetcher = ArxivFetcher()
    try:
        return fetcher.fetch(arxiv)
    except FetcherError as exc:
        console.print(f"[red]error[/red] arXiv fetch failed: {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        fetcher.close()


def _fetched_frontmatter(
    metadata: PaperMetadata,
    *,
    status: PaperStatus,
    tags: list[str],
    paper_id: str | None,
) -> PaperFrontmatter:
    if metadata.year is None:
        console.print("[red]error[/red] fetched metadata is missing publication year")
        raise typer.Exit(code=1)

    generated_id = paper_id or _slug_for(metadata.authors[0], metadata.year, metadata.title)

    try:
        return PaperFrontmatter(
            id=generated_id,
            title=metadata.title,
            authors=metadata.authors,
            year=metadata.year,
            venue=metadata.venue,
            doi=metadata.doi,
            arxiv_id=metadata.arxiv_id,
            openalex_id=metadata.openalex_id,
            semantic_scholar_id=metadata.semantic_scholar_id,
            url=metadata.url,
            status=status,
            source=metadata.source,
            added_on=date.today(),
            tags=tags,
        )
    except ValueError as exc:
        console.print(f"[red]error[/red] invalid fetched metadata: {exc}")
        raise typer.Exit(code=1) from exc


def _write_literature_entry(
    paths: ProjectPaths,
    fm: PaperFrontmatter,
    *,
    force: bool,
    source_label: str,
) -> None:
    ensure_dir(paths.kb_papers)
    paper_path = paths.kb_papers / f"{fm.id}.md"
    paper_exists = paper_path.exists()
    if paper_exists and not force:
        console.print(f"[red]error[/red] paper id {fm.id!r} already exists at {paper_path}")
        console.print("       re-run with --force to replace it")
        raise typer.Exit(code=1)

    frontmatter_dict = fm.model_dump(mode="json", exclude_none=True)
    body = render_paper_card(fm)
    write_frontmatter(paper_path, frontmatter_dict, body)

    ensure_dir(paths.kb_raw_metadata)
    meta_path = paths.kb_raw_metadata / f"{fm.id}.json"
    meta_path.write_text(
        json.dumps(frontmatter_dict, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    action = "replace" if force and paper_exists else "add"
    _append_log(paths, f"add-literature {source_label} {action} id={fm.id}")

    console.print(f"[green]added[/green] {fm.id}")
    console.print(f"  card     : {paper_path.relative_to(paths.root)}")
    console.print(f"  metadata : {meta_path.relative_to(paths.root)}")


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
