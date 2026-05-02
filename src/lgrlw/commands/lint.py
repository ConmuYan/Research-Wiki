"""``lgrlw lint`` -- verify structure, schema, boundary, and manifest invariants."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from lgrlw.lint import format_findings, run_all
from lgrlw.paths import resolve_project
from lgrlw.schemas import LintSeverity

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
) -> None:
    """Run every invariant check and exit non-zero on any finding."""
    if project_root is not None and root is not None and project_root.resolve() != root.resolve():
        console.print("[red]error[/red] provide either positional project root or --root, not both")
        raise typer.Exit(code=1)

    paths = resolve_project(root or project_root)
    findings = run_all(paths)

    if not findings:
        console.print("[green]lint[/green] all checks passed")
        return

    errors = sum(1 for f in findings if f.severity == LintSeverity.error.value)
    warnings = sum(1 for f in findings if f.severity == LintSeverity.warning.value)
    typer.echo(format_findings(findings, project_root=paths.root))

    summary = f"summary: {errors} error(s), {warnings} warning(s)"
    console.print(f"[red]{summary}[/red]" if errors else f"[yellow]{summary}[/yellow]")
    raise typer.Exit(code=1)


__all__ = ["lint_command"]
