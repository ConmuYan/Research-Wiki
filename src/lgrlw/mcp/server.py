"""Research-Wiki Model Context Protocol server.

The MCP layer is deliberately thin: tools call the same backend helpers
used by the Typer CLI and return structured JSON-compatible dictionaries.
No tool performs network I/O unless the caller explicitly selects a
networked ``add_literature`` mode (``doi``, ``arxiv``, ``openalex`` or
``ss``), mirroring the CLI contract.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Literal

import typer
from mcp.server.fastmcp import FastMCP

from lgrlw._resources import templates_root
from lgrlw.commands.add_literature import (
    _archive_pdf,
    _fetch_arxiv_metadata,
    _fetch_doi_metadata,
    _fetch_openalex_metadata,
    _fetch_ss_metadata,
    _fetched_frontmatter,
    _manual_frontmatter,
    _split_csv,
    _write_literature_entry,
)
from lgrlw.commands.init import _materialise_subproject
from lgrlw.config import dump_config, load_config
from lgrlw.export.pack import build_export_pack
from lgrlw.fs import copy_tree, read_frontmatter, write_frontmatter
from lgrlw.lint import format_findings, run_all
from lgrlw.monorepo import (
    MONOREPO_DIR,
    MonorepoError,
    iter_subprojects,
    load_monorepo_config,
    resolve_subproject,
)
from lgrlw.paths import PROJECT_MARKER, ProjectPaths, find_project_root
from lgrlw.promote import PromoteError, promote_workspace
from lgrlw.schemas import (
    PAPER_ID_PATTERN,
    WORKSPACE_ID_PATTERN,
    LintFinding,
    PaperStatus,
    ProjectConfig,
    WorkspaceKind,
    WorkspacePaperFrontmatter,
    WorkspaceStatus,
)

AddLiteratureMode = Literal["manual", "doi", "arxiv", "openalex", "ss"]
PaperStatusName = Literal["published", "accepted", "preprint"]
WorkspaceKindName = Literal["paper", "idea"]


def create_server(default_root: Path | None = None) -> FastMCP:
    """Create a configured Research-Wiki MCP server.

    ``default_root`` is used by tools/resources when a per-call ``root``
    argument is omitted. If it is also ``None``, resolution falls back to
    the process working directory, exactly like the CLI.
    """
    server = FastMCP(
        "Research-Wiki",
        instructions=(
            "Operate on Research-Wiki projects. Tools mirror the lgrlw CLI; "
            "use root/direction to select a project or monorepo direction."
        ),
    )

    @server.tool(
        name="init_project",
        title="Initialise Research-Wiki Project",
        description=(
            "Create a Research-Wiki project. With monorepo=true, create an umbrella "
            "root plus the first directions/<slug>/ subproject."
        ),
        structured_output=True,
    )
    def init_project(
        root: str,
        direction: str,
        monorepo: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        target = Path(root).resolve()
        _validate_direction_slug(direction)
        marker = target / PROJECT_MARKER
        if marker.is_file() and not force:
            raise ValueError(f"{target} already hosts a Research-Wiki project")
        target.mkdir(parents=True, exist_ok=True)

        if monorepo:
            sub_root = target / MONOREPO_DIR / direction
            if (sub_root / PROJECT_MARKER).is_file() and not force:
                raise ValueError(f"direction {direction!r} already exists at {sub_root}")
            _materialise_subproject(sub_root, direction)
            dump_config(
                ProjectConfig(
                    schema_version="1.1.0",
                    direction=direction,
                    monorepo=True,
                    directions=[direction],
                ),
                marker,
            )
            return {
                "ok": True,
                "layout": "monorepo",
                "root": str(target),
                "direction": direction,
                "subproject_root": str(sub_root),
            }

        _materialise_subproject(target, direction)
        return {
            "ok": True,
            "layout": "single",
            "root": str(target),
            "direction": direction,
        }

    @server.tool(
        name="add_direction",
        title="Add Monorepo Direction",
        description="Add directions/<slug>/ to an existing Research-Wiki monorepo umbrella.",
        structured_output=True,
    )
    def add_direction(
        direction: str,
        root: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        umbrella_root = _project_root(root, default_root)
        _validate_direction_slug(direction)
        cfg = load_monorepo_config(umbrella_root)
        sub_root = umbrella_root / MONOREPO_DIR / direction
        if direction in cfg.directions and (sub_root / PROJECT_MARKER).is_file() and not force:
            raise ValueError(f"direction {direction!r} already registered at {sub_root}")

        _materialise_subproject(sub_root, direction)
        if direction not in cfg.directions:
            cfg = cfg.model_copy(update={"directions": [*cfg.directions, direction]})
            dump_config(cfg, umbrella_root / PROJECT_MARKER)

        return {
            "ok": True,
            "root": str(umbrella_root),
            "direction": direction,
            "subproject_root": str(sub_root),
            "directions": list(cfg.directions),
        }

    @server.tool(
        name="new_workspace",
        title="Create Workspace",
        description="Create a paper/idea workspace under research-workspaces/<name>/.",
        structured_output=True,
    )
    def new_workspace(
        name: str,
        title: str,
        kind: WorkspaceKindName = "paper",
        root: str | None = None,
        direction: str | None = None,
    ) -> dict[str, Any]:
        if not WORKSPACE_ID_PATTERN.fullmatch(name):
            raise ValueError(f"invalid workspace id {name!r}")
        if not title.strip():
            raise ValueError("title must not be empty")

        paths = _resolve_paths(root, direction, default_root)
        dst = paths.workspace(name)
        if dst.exists():
            raise ValueError(f"workspace already exists: {dst}")

        workspace_kind = WorkspaceKind(kind)
        tpl = templates_root() / "research-workspace" / workspace_kind.value
        if not tpl.is_dir():
            raise ValueError(f"no workspace template for kind {workspace_kind.value!r}")
        copy_tree(tpl, dst)

        if workspace_kind == WorkspaceKind.paper:
            status_path = dst / "00_Project" / "paper_status.md"
            _, body = read_frontmatter(status_path)
            fm = WorkspacePaperFrontmatter(
                id=name,
                kind=workspace_kind,
                title=title,
                status=WorkspaceStatus.drafting,
                created_on=date.today(),
            )
            write_frontmatter(status_path, fm.model_dump(mode="json", exclude_none=True), body)

        return {
            "ok": True,
            "root": str(paths.root),
            "workspace": name,
            "workspace_path": str(dst),
            "kind": workspace_kind.value,
        }

    @server.tool(
        name="add_literature",
        title="Add Literature",
        description=(
            "Add a paper to the KB. mode=manual is offline; doi/arxiv/openalex/ss "
            "perform the same explicit network fetch as the CLI."
        ),
        structured_output=True,
    )
    def add_literature(
        mode: AddLiteratureMode = "manual",
        title: str = "",
        authors: str = "",
        year: int = 0,
        venue: str | None = None,
        doi: str | None = None,
        arxiv: str | None = None,
        openalex: str | None = None,
        ss: str | None = None,
        url: str | None = None,
        status: PaperStatusName = "published",
        tags: str | None = None,
        paper_id: str | None = None,
        force: bool = False,
        pdf_path: str | None = None,
        force_pdf: bool = False,
        root: str | None = None,
        direction: str | None = None,
    ) -> dict[str, Any]:
        paths = _resolve_paths(root, direction, default_root)
        tags_list = _split_csv(tags or "")
        paper_status = PaperStatus(status)

        try:
            if mode == "manual":
                fm = _manual_frontmatter(
                    title=title,
                    authors=authors,
                    year=year,
                    venue=venue,
                    doi=doi,
                    arxiv=arxiv,
                    openalex=openalex,
                    ss=ss,
                    url=url,
                    status=paper_status,
                    tags=tags_list,
                    paper_id=paper_id,
                )
            elif mode == "doi":
                fm = _fetched_frontmatter(
                    _fetch_doi_metadata(doi or ""),
                    status=paper_status,
                    tags=tags_list,
                    paper_id=paper_id,
                )
            elif mode == "arxiv":
                fm = _fetched_frontmatter(
                    _fetch_arxiv_metadata(arxiv or ""),
                    status=paper_status,
                    tags=tags_list,
                    paper_id=paper_id,
                )
            elif mode == "openalex":
                fm = _fetched_frontmatter(
                    _fetch_openalex_metadata(openalex or ""),
                    status=paper_status,
                    tags=tags_list,
                    paper_id=paper_id,
                )
            else:
                fm = _fetched_frontmatter(
                    _fetch_ss_metadata(ss or ""),
                    status=paper_status,
                    tags=tags_list,
                    paper_id=paper_id,
                )
        except typer.Exit as exc:
            raise ValueError("invalid add_literature request") from exc

        pdf = Path(pdf_path) if pdf_path else None
        try:
            pdf_archive = _archive_pdf(paths, fm.id, pdf, force_pdf=force_pdf)
        except typer.Exit as exc:
            raise ValueError("invalid pdf attachment") from exc

        _write_literature_entry(
            paths,
            fm,
            force=force,
            source_label=mode,
            pdf_archive=pdf_archive,
        )
        return {
            "ok": True,
            "root": str(paths.root),
            "paper_id": fm.id,
            "paper_card": str(paths.kb_papers / f"{fm.id}.md"),
            "metadata_json": str(paths.kb_raw_metadata / f"{fm.id}.json"),
            "pdf_archive": str(pdf_archive) if pdf_archive is not None else None,
        }

    @server.tool(
        name="export_pack",
        title="Export KB Pack",
        description="Build an immutable dated KB snapshot for a workspace.",
        structured_output=True,
    )
    def export_pack(
        workspace: str,
        root: str | None = None,
        direction: str | None = None,
    ) -> dict[str, Any]:
        paths = _resolve_paths(root, direction, default_root)
        pack_dir = build_export_pack(paths, workspace)
        return {
            "ok": True,
            "root": str(paths.root),
            "workspace": workspace,
            "pack_dir": str(pack_dir),
            "mirror_dir": str(paths.workspace_kb_exports(workspace) / pack_dir.name),
        }

    @server.tool(
        name="promote",
        title="Promote Workspace Paper",
        description="Promote an accepted workspace paper into the KB atomically.",
        structured_output=True,
    )
    def promote(
        workspace: str,
        paper_id: str | None = None,
        force: bool = False,
        root: str | None = None,
        direction: str | None = None,
    ) -> dict[str, Any]:
        paths = _resolve_paths(root, direction, default_root)
        try:
            result = promote_workspace(paths, workspace, paper_id=paper_id, force=force)
        except PromoteError as exc:
            raise ValueError(str(exc)) from exc
        return {
            "ok": True,
            "root": str(paths.root),
            "paper_id": result.paper_id,
            "paper_card": str(result.paper_card),
            "metadata_json": str(result.metadata_json),
            "bibtex": str(result.bibtex),
            "log": str(result.log),
        }

    @server.tool(
        name="lint",
        title="Lint Research-Wiki Project",
        description=(
            "Run structure/schema/boundary/manifest lint. A monorepo umbrella with no "
            "direction is linted recursively across every direction."
        ),
        structured_output=True,
    )
    def lint(
        root: str | None = None,
        direction: str | None = None,
    ) -> dict[str, Any]:
        report_root, findings = _run_lint(root, direction, default_root)
        errors = sum(1 for finding in findings if finding.severity == "error")
        warnings = sum(1 for finding in findings if finding.severity == "warning")
        return {
            "ok": not findings,
            "root": str(report_root),
            "errors": errors,
            "warnings": warnings,
            "findings": [finding.model_dump(mode="json") for finding in findings],
            "text": format_findings(findings, project_root=report_root) if findings else "",
        }

    @server.resource(
        "lgrlw://project/summary",
        name="project_summary",
        title="Research-Wiki project summary",
        description="JSON summary of the default Research-Wiki project root.",
        mime_type="application/json",
    )
    def project_summary() -> str:
        roots = _resource_subprojects(default_root)
        return json.dumps(
            {
                "subprojects": [
                    {
                        "root": str(paths.root),
                        "papers": _count_markdown(paths.kb_papers),
                        "workspaces": _count_dirs(paths.workspaces),
                    }
                    for paths in roots
                ]
            },
            ensure_ascii=False,
            indent=2,
        )

    @server.resource(
        "lgrlw://kb/papers",
        name="kb_papers",
        title="KB paper list",
        description="JSON list of paper-card frontmatter records in the default project.",
        mime_type="application/json",
    )
    def kb_papers() -> str:
        papers: list[dict[str, Any]] = []
        for paths in _resource_subprojects(default_root):
            if not paths.kb_papers.is_dir():
                continue
            for md in sorted(paths.kb_papers.glob("*.md")):
                if md.name == ".gitkeep":
                    continue
                fm, _ = read_frontmatter(md)
                papers.append({"root": str(paths.root), "path": str(md), "frontmatter": fm})
        return json.dumps(papers, ensure_ascii=False, indent=2)

    @server.resource(
        "lgrlw://workspaces",
        name="workspaces",
        title="Workspace list",
        description="JSON list of workspaces in the default project.",
        mime_type="application/json",
    )
    def workspaces() -> str:
        items: list[dict[str, Any]] = []
        for paths in _resource_subprojects(default_root):
            if not paths.workspaces.is_dir():
                continue
            for workspace in sorted(p for p in paths.workspaces.iterdir() if p.is_dir()):
                status_path = workspace / "00_Project" / "paper_status.md"
                fm = None
                if status_path.is_file():
                    fm, _ = read_frontmatter(status_path)
                items.append(
                    {
                        "root": str(paths.root),
                        "workspace": workspace.name,
                        "path": str(workspace),
                        "paper_status": fm,
                    }
                )
        return json.dumps(items, ensure_ascii=False, indent=2)

    return server


def run_stdio_server(default_root: Path | None = None) -> None:
    """Run the Research-Wiki MCP server over stdio."""
    create_server(default_root=default_root).run(transport="stdio")


def _project_root(root: str | None, default_root: Path | None) -> Path:
    if root is not None:
        resolved = Path(root).resolve()
    elif default_root is not None:
        resolved = default_root.resolve()
    else:
        resolved = find_project_root(Path.cwd())
    if not (resolved / PROJECT_MARKER).is_file():
        raise ValueError(f"{resolved} is not a Research-Wiki project")
    return resolved


def _resolve_paths(
    root: str | None,
    direction: str | None,
    default_root: Path | None,
) -> ProjectPaths:
    selected_root = Path(root).resolve() if root is not None else default_root
    try:
        return resolve_subproject(selected_root, direction)
    except MonorepoError as exc:
        raise ValueError(str(exc)) from exc


def _run_lint(
    root: str | None,
    direction: str | None,
    default_root: Path | None,
) -> tuple[Path, list[LintFinding]]:
    selected_root = _project_root(root, default_root)
    cfg = load_config(selected_root / PROJECT_MARKER)
    if cfg.monorepo and direction is None:
        findings: list[LintFinding] = []
        for subproject in iter_subprojects(selected_root):
            findings.extend(run_all(subproject))
        return selected_root, findings
    paths = _resolve_paths(root, direction, default_root)
    return paths.root, run_all(paths)


def _resource_subprojects(default_root: Path | None) -> list[ProjectPaths]:
    root = _project_root(None, default_root)
    cfg = load_config(root / PROJECT_MARKER)
    if cfg.monorepo:
        return iter_subprojects(root)
    return [ProjectPaths(root=root, kb_name=cfg.kb_name, workspaces_name=cfg.workspaces_name)]


def _validate_direction_slug(direction: str) -> None:
    if not PAPER_ID_PATTERN.fullmatch(direction):
        raise ValueError(f"invalid direction slug {direction!r}")


def _count_markdown(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for p in path.glob("*.md") if p.name != ".gitkeep")


def _count_dirs(path: Path) -> int:
    if not path.is_dir():
        return 0
    return sum(1 for p in path.iterdir() if p.is_dir())


__all__ = ["create_server", "run_stdio_server"]
