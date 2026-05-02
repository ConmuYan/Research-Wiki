# Architecture

Research-Wiki is a **protocol plus a small CLI**. This document describes
the deployed layout, the modules, and the invariants. For the
user-facing lifecycle narrative see [`lifecycle.md`](./lifecycle.md). For
the enforced boundaries see [`boundary-rules.md`](./boundary-rules.md).

## The three spaces

```
<project-root>/
  .lgrlw.toml                    # project marker + config
  literature-kb/                 # KB: public literature
    00_System/                   # AGENTS.md, protocol docs, log
    01_Raw/                      # bibtex/ pdf/ mineru_md/ metadata/
    02_Literature/Papers/        # one markdown card per paper
    03_Field_Structure/          # overview, problem evolution, taxonomies
    04_Concepts/                 # methods, tasks, datasets, metrics
    05_Evidence/                 # claims, evidence map, open problems
    06_Exports/                  # dated, immutable KB snapshots
  research-workspaces/           # WS: your private research projects
    <workspace-id>/
      00_Project/                # status, problem, idea, method, claims
      01_KB_Exports/             # mirrored, read-only KB snapshots
      02_Idea_and_Method/
      03_Experiments/
      04_Writing/
      05_Review/
      06_Promotion/
```

The separation is load-bearing. See [`boundary-rules.md`](./boundary-rules.md).

## Package map

```
src/lgrlw/
  __init__.py         # version + public surface
  __main__.py         # `python -m lgrlw`
  cli.py              # Typer app; registers every command
  config.py           # .lgrlw.toml reader/writer
  paths.py            # ProjectPaths, find_project_root, resolve_project
  fs.py               # sha256, copy_tree, (read|write)_frontmatter
  schemas.py          # pydantic models for frontmatter + manifests
  _resources.py       # locate bundled templates & schemas
  commands/           # one file per CLI subcommand
    init.py
    new_workspace.py
    add_literature.py
    export_pack.py
    lint.py
  export/
    pack.py           # build_export_pack -- the snapshot builder
  lint/               # one rule family per file
    structure.py
    schema.py
    boundary.py
    manifest.py
  render/
    paper_card.py     # Jinja renderer for paper card bodies
```

## Invariants (v0.1)

1. **Three-space separation.** See [`boundary-rules.md`](./boundary-rules.md).
2. **Schema is a contract.** `src/lgrlw/schemas.py` (pydantic) and
   `schemas/*.schema.json` (JSON Schema) must stay in lockstep.
3. **Boundary lint may only strengthen.** Relaxations require a test and a
   CHANGELOG entry.
4. **No network I/O in v0.1.** Fetchers (arXiv / OpenAlex / Semantic
   Scholar / Crossref) are scheduled for v0.2 under `lgrlw.fetchers`.
5. **No state outside the project root.** `lgrlw` only reads/writes under
   the invoked project directory (and, in v0.2, `platformdirs`-provided
   cache paths).

## Dependency philosophy

The runtime dependency set is deliberately tiny: Typer, Rich, pydantic,
PyYAML, python-slugify, Jinja2. No database, no vector store, no network
library in v0.1. Adding heavy dependencies requires an RFC-style issue.

## Extension points

- **New lint rule** &rarr; drop a file under `src/lgrlw/lint/`, wire it up
  in `lgrlw/lint/__init__.py`, ship a violating + clean fixture under
  `tests/fixtures/`.
- **New fetcher (v0.2)** &rarr; subclass `lgrlw.fetchers.base.BaseFetcher`,
  return a `PaperMetadata`, provide a `respx`-mocked test.
- **New template skeleton** &rarr; RFC first; template changes are a stable
  API for end users.
