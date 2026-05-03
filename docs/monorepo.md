# Multi-direction monorepos

Research-Wiki v0.3 supports two project layouts.

## Single-direction layout

This is the v0.1/v0.2 layout and remains fully supported:

```text
<project-root>/
  .lgrlw.toml
  literature-kb/
  research-workspaces/
```

Create it with:

```bash
lgrlw init ./my-direction --direction efficient-llm-inference
```

All existing commands continue to work exactly as before.

## Monorepo layout

A monorepo umbrella hosts multiple independent Research-Wiki directions in one git repository:

```text
<repo-root>/
  .lgrlw.toml                 # monorepo umbrella config
  directions/
    alpha/
      .lgrlw.toml             # normal single-direction child project
      literature-kb/
      research-workspaces/
    beta/
      .lgrlw.toml
      literature-kb/
      research-workspaces/
```

Create the umbrella and first direction with:

```bash
lgrlw init ./research-repo --direction alpha --monorepo
```

Add another direction with:

```bash
lgrlw add-direction beta --root ./research-repo
```

The umbrella `.lgrlw.toml` uses schema version `1.1.0`:

```toml
[project]
schema_version   = "1.1.0"
direction        = "alpha"
kb_name          = "literature-kb"
workspaces_name  = "research-workspaces"
monorepo         = true
directions       = ["alpha", "beta"]
```

Each child direction keeps the standard single-direction config and skeleton.

## Running project-scoped commands

Project-scoped commands accept `--direction <slug>` when `--root` points at a monorepo umbrella:

```bash
lgrlw new-workspace paper_001 --title "Beta paper" --root ./research-repo --direction beta
lgrlw add-literature --manual --title "A paper" --authors "Ada Lovelace" --year 2024 --root ./research-repo --direction beta
lgrlw export-pack paper_001 --root ./research-repo --direction beta
lgrlw promote paper_001 --root ./research-repo --direction beta
```

If you run a command from inside `directions/<slug>/`, Research-Wiki can infer that direction.

## Linting

`lgrlw lint --root ./research-repo` checks every direction listed in the umbrella config and reports paths like:

```text
directions/beta/literature-kb/03_Field_Structure/Polluted.md
```

Use `--direction <slug>` to lint only one child project:

```bash
lgrlw lint --root ./research-repo --direction beta
```

## Invariants

- Each `directions/<slug>/` child is a complete single-direction Research-Wiki project.
- KB/workspace boundary rules apply independently inside each child direction.
- Commands never write outside the selected child project, except `add-direction`, which updates the umbrella `.lgrlw.toml` and materialises `directions/<slug>/`.
- The monorepo umbrella itself is not a KB and must not contain `literature-kb/` or `research-workspaces/` directly.
