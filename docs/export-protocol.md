# Export protocol

Export packs are how a workspace reads from the KB without ever
mutating it. Every pack is dated, immutable, and SHA-256-verified by
`lgrlw lint`.

## Command

```
lgrlw export-pack <workspace-id>
```

## Output

### Canonical location

```
literature-kb/06_Exports/<workspace-id>_<YYYY-MM-DD>/
    02_Literature/Papers/...
    03_Field_Structure/...
    05_Evidence/...
    export_manifest.json
```

### Mirror

Simultaneously copied (bit-identical) into the workspace at:

```
research-workspaces/<workspace-id>/01_KB_Exports/<same-name>/
```

### Pack contents (v0.1 policy)

The pack includes exactly these KB subtrees:

- `02_Literature/Papers/` &mdash; every paper card
- `03_Field_Structure/`   &mdash; the user-curated field structure
- `05_Evidence/`          &mdash; claims, evidence map, open problems

Deliberately **excluded** from the pack:

- `01_Raw/` &mdash; PDFs / raw metadata are too heavy to duplicate; if you
  need them while writing, consult them in the live KB.
- `06_Exports/` &mdash; packs must not reference other packs.
- `00_System/`, `04_Concepts/` &mdash; reserved; their inclusion policy will
  be revisited in v0.2.

## Manifest schema

See [`schemas/export_manifest.schema.json`](../schemas/export_manifest.schema.json).

Concretely, every pack root contains a `export_manifest.json` with:

```json
{
  "schema_version": "1.0.0",
  "tool_version": "0.1.0",
  "workspace_id": "paper_001",
  "exported_at": "2026-05-02T09:30:00Z",
  "kb_root_relative": "literature-kb",
  "pack_dir_relative": "literature-kb/06_Exports/paper_001_2026-05-02",
  "paper_ids": ["smith-2023-selfrag", ...],
  "files": {
    "02_Literature/Papers/smith-2023-selfrag.md": "ab12...ef",
    "03_Field_Structure/Overview.md":              "cd34...01",
    ...
  }
}
```

`files` lists every file in the pack except the manifest itself, keyed
by its pack-relative POSIX path and valued by its full SHA-256 hex digest.
All manifest paths are relative-only, use POSIX `/` separators, and must
not contain absolute paths, drive letters, `.` segments, or `..` segments.

## Integrity invariants

`lgrlw lint` (see
[`src/lgrlw/lint/manifest.py`](../src/lgrlw/lint/manifest.py))
enforces:

| Rule | Check |
|---|---|
| `manifest.missing` | Every `06_Exports/<dir>/` contains `export_manifest.json`. |
| `manifest.invalid` | Manifest parses and satisfies `ExportManifest`. |
| `manifest.file_missing` | Every file listed in the manifest exists. |
| `manifest.sha256_mismatch` | Every file's digest matches the manifest. |
| `manifest.file_extra` (warn) | No pack file is *absent* from the manifest; warning findings still make `lgrlw lint` exit non-zero. |

## Immutability

Do not edit a pack after it was created. Packs are the ground truth that
anchors a paper draft to a specific KB state; silently editing them
breaks reproducibility. If the KB has advanced and you need a fresh
snapshot, just run `lgrlw export-pack <workspace-id>` again &mdash; the
pack name includes the date, so multiple snapshots coexist cleanly.

## Regenerating a pack on the same day

The pack name includes the date, not the time, so regenerating on the
same day would collide. `build_export_pack` raises `FileExistsError` to
prevent silent overwrite. If you really need to regenerate, delete the
existing pack by hand first and document why in
`research-workspaces/<id>/workspace_log.md`.
