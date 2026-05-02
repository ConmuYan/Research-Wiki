# Verification policy

The Research-Wiki protocol is enforced by `lgrlw lint`. This document
catalogues every invariant the linter currently checks and how it fails.

## Structural

| Rule | What it checks |
|---|---|
| `structure.project_root` | `.lgrlw.toml`, `literature-kb/`, and `research-workspaces/` all exist at the project root. |

## Schema

| Rule | What it checks |
|---|---|
| `schema.paper.missing_frontmatter` | Every `02_Literature/Papers/*.md` must open with a YAML frontmatter block. |
| `schema.paper.type` | Frontmatter must declare `type: paper`. |
| `schema.paper.validation` | Frontmatter must satisfy `PaperFrontmatter` (see `src/lgrlw/schemas.py`). |
| `schema.workspace.missing_frontmatter` | Every workspace's `00_Project/paper_status.md` must have frontmatter. |
| `schema.workspace.validation` | Frontmatter must satisfy `WorkspacePaperFrontmatter`. |

## Boundary

| Rule | What it checks |
|---|---|
| `boundary.workspace_reference_in_kb` | No KB markdown may reference the `research-workspaces/` tree (except files under `00_System/`, which are KB tooling docs that legitimately name the workspace layout). |
| `boundary.workspace_frontmatter_in_kb` | KB frontmatter may not carry workspace-only `type` values (`workspace_paper`, `idea`, `experiment`, `rebuttal`). |
| `boundary.workspace_status_in_kb` | KB frontmatter may not carry workspace-only `status` values (`drafting`, `under_review`, `rejected`, &hellip;). |

## Manifest

| Rule | What it checks |
|---|---|
| `manifest.missing` | Every `06_Exports/<pack>/` must contain an `export_manifest.json`. |
| `manifest.invalid` | Manifest must satisfy `ExportManifest`. |
| `manifest.file_missing` | Every file listed in the manifest must exist in the pack. |
| `manifest.sha256_mismatch` | Every file's SHA-256 must match its manifest entry. |
| `manifest.file_extra` | Warning: files present in the pack but absent from the manifest. |

## Exit code

`lgrlw lint` exits `0` iff there are no `error`-severity findings.
Warnings do not fail CI but are displayed.

## Strengthening-only

New lint rules may be added at any time. Existing rules may only be relaxed
with an explicit CHANGELOG entry and a test covering the new behaviour. See
the repository-root `AGENTS.md` section 1.3.
