"""Typer application exposing the ``lgrlw`` CLI.

The CLI is intentionally small:

* ``lgrlw init``              - scaffold a new project
* ``lgrlw new-workspace``     - create a paper/idea workspace
* ``lgrlw add-literature``    - register a manual / DOI / arXiv / OpenAlex / S2 literature entry
* ``lgrlw export-pack``       - snapshot the KB for a workspace
* ``lgrlw promote``           - promote an accepted workspace paper into the KB
* ``lgrlw lint``              - verify the three-space invariants
"""

from __future__ import annotations

from typing import Annotated

import typer

from lgrlw import __version__
from lgrlw.commands.add_literature import add_literature_command
from lgrlw.commands.export_pack import export_pack_command
from lgrlw.commands.init import init_command
from lgrlw.commands.lint import lint_command
from lgrlw.commands.new_workspace import new_workspace_command
from lgrlw.commands.promote import promote_command


def _show_version(value: bool) -> None:
    """Eager callback for ``--version`` / ``-V``."""
    if value:
        typer.echo(f"lgrlw {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="lgrlw",
    help=(
        "Research-Wiki - Literature-Grounded Research Lifecycle Wiki. "
        f"v{__version__} (init / new-workspace / add-literature / export-pack / promote / lint). "
        "add-literature supports --manual / --doi / --arxiv / --openalex / --ss."
    ),
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)

app.command("init", help="Bootstrap a new Research-Wiki project.")(init_command)
app.command(
    "new-workspace",
    help="Create a new workspace under research-workspaces/.",
)(new_workspace_command)
app.command(
    "add-literature",
    help="Register a paper in the KB (--manual / --doi / --arxiv / --openalex / --ss).",
)(add_literature_command)
app.command(
    "export-pack",
    help="Build an immutable, dated KB snapshot for a workspace.",
)(export_pack_command)
app.command(
    "promote",
    help="Promote an accepted workspace paper into the KB (paper card + metadata + BibTeX).",
)(promote_command)
app.command(
    "lint",
    help="Verify three-space boundary, frontmatter schema, and manifest invariants.",
)(lint_command)


@app.callback()
def _main(
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=_show_version,
            is_eager=True,
            help="Print the installed lgrlw version and exit.",
        ),
    ] = False,
) -> None:
    """Top-level callback. Currently only hosts the ``--version`` eager option."""


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["app", "main"]
