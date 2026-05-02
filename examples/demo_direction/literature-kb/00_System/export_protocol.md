# Protocol: exporting a KB snapshot into a workspace

Export packs are how a `research-workspaces/<id>/` project consumes the KB
without ever mutating it. Every pack is dated, immutable, and hash-verified.

## Command

```bash
lgrlw export-pack <workspace-id>
```

## What is copied (v0.1 policy)

Relative to the KB root:

- `02_Literature/Papers/` &mdash; every paper card
- `03_Field_Structure/`    &mdash; the user-curated field structure
- `05_Evidence/`           &mdash; claims, evidence map, limitations, open problems

Deliberately excluded:

- `01_Raw/` (PDFs and raw metadata dumps; too heavy to duplicate)
- `06_Exports/` (packs must not reference other packs)
- `00_System/`, `04_Concepts/` (reserved for v0.2 policy tuning)

## Where it lands

1. Canonical location:
   `06_Exports/<workspace-id>_<YYYY-MM-DD>/`
2. Mirror inside the workspace:
   `../research-workspaces/<workspace-id>/01_KB_Exports/<same-name>/`

Both copies are bit-identical and content-addressed.

## Manifest

A `export_manifest.json` at the pack root lists every file with its SHA-256
digest. Fields:

- `schema_version`, `tool_version`
- `workspace_id`, `exported_at` (ISO 8601 UTC), `kb_root_relative`,
  `pack_dir_relative`
- `paper_ids` &mdash; sorted list of slugs copied in
- `files` &mdash; map of `<pack-relative POSIX path>` to `<sha256 hex>`

`lgrlw lint` recomputes every SHA-256 and fails on mismatch, missing file,
or extra file.

## Immutability

Do not edit a pack after it was created. If the KB has advanced and you
need a fresh snapshot, run `lgrlw export-pack <workspace-id>` again on a
later date &mdash; the pack name includes the date, so multiple snapshots
can coexist.
