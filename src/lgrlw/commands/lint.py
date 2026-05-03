"""``lgrlw lint`` -- verify structure, schema, boundary, and manifest invariants."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from lgrlw.config import load_config
from lgrlw.lint import format_findings, run_all
from lgrlw.monorepo import MonorepoError, iter_subprojects, resolve_subproject
from lgrlw.paths import PROJECT_MARKER, find_project_root
from lgrlw.schemas import LintFinding, LintSeverity

console = Console()


def lint_command(
    project_root: Annotated[
        Path | None,
        typer.Argument(
            help="Project root (auto-detect if omitted).",
        ),
    ] = None,
    root: Annotated[
        Path | None,
        typer.Option(
            "--root",
            help="Project root (auto-detect if omitted).",
        ),
    ] = None,
    direction: Annotated[
        str | None,
        typer.Option(
            "--direction",
            help=(
                "Monorepo direction slug. Without it, a monorepo umbrella is "
                "linted recursively across every direction; a single-direction "
                "project ignores this option."
            ),
        ),
    ] = None,
) -> None:
    """Run every invariant check and exit non-zero on any finding.

    When the resolved root is a monorepo umbrella, every direction
    listed in its ``.lgrlw.toml`` is linted in turn and findings are
    merged (each finding's ``path`` is prefixed with
    ``directions/<slug>/``).
    """
    if project_root is not None and root is not None and project_root.resolve() != root.resolve():
        console.print("[red]error[/red] provide either positional project root or --root, not both")
        raise typer.Exit(code=1)

    explicit_root = root or project_root
    try:
        umbrella_root = _resolve_umbrella_root(explicit_root)
    except FileNotFoundError as exc:
        console.print(f"[red]error[/red] {exc}")
        raise typer.Exit(code=1) from exc

    cfg = load_config(umbrella_root / PROJECT_MARKER)

    if cfg.monorepo and direction is None:
        try:
            subprojects = iter_subprojects(umbrella_root)
        except MonorepoError as exc:
            console.print(f"[red]error[/red] {exc}")
            raise typer.Exit(code=1) from exc
        findings: list[LintFinding] = []
        for sub in subprojects:
            findings.extend(run_all(sub))
        # All `LintFinding.path` values are absolute paths; relativising
        # them against the umbrella root naturally renders them with a
        # `directions/<slug>/...` prefix in the output.
        report_root = umbrella_root
    else:
        try:
            paths = resolve_subproject(explicit_root, direction)
        except MonorepoError as exc:
            console.print(f"[red]error[/red] {exc}")
            raise typer.Exit(code=1) from exc
        findings = run_all(paths)
        report_root = paths.root

    if not findings:
        console.print("[green]lint[/green] all checks passed")
        return

    errors = sum(1 for f in findings if f.severity == LintSeverity.error.value)
    warnings = sum(1 for f in findings if f.severity == LintSeverity.warning.value)
    typer.echo(format_findings(findings, project_root=report_root))

    summary = f"summary: {errors} error(s), {warnings} warning(s)"
    console.print(f"[red]{summary}[/red]" if errors else f"[yellow]{summary}[/yellow]")
    raise typer.Exit(code=1)


def _resolve_umbrella_root(explicit_root: Path | None) -> Path:
    """Return the *outermost* ``.lgrlw.toml`` ancestor.

    When invoked from inside ``directions/<slug>/`` of a monorepo, we
    want lint to consider the umbrella root by default so the user can
    say ``lgrlw lint`` once and have every direction checked. The
    explicit ``--root`` / positional argument always wins.
    """
    if explicit_root is not None:
        resolved = explicit_root.resolve()
        if not (resolved / PROJECT_MARKER).is_file():
            raise FileNotFoundError(
                f"{resolved} is not a Research-Wiki project (missing {PROJECT_MARKER})"
            )
        return resolved

    nearest = find_project_root(Path.cwd())
    cursor = nearest.parent
    candidate = nearest
    while cursor != cursor.parent:
        if (cursor / PROJECT_MARKER).is_file():
            try:
                cfg = load_config(cursor / PROJECT_MARKER)
            except (OSError, ValueError):
                break
            if cfg.monorepo:
                candidate = cursor
                break
        cursor = cursor.parent
    return candidate


__all__ = ["lint_command"]
