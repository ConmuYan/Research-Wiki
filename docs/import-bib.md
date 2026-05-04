# `lgrlw import-bib` — batch BibTeX import

`lgrlw import-bib` (v0.4) turns a BibTeX file into canonical KB paper
cards in one deterministic, offline pass. It is the first command in
the `v0.3.1 → v0.6` ingestion series; `lgrlw attach-pdf` (v0.4.x),
MinerU conversion (v0.5), networked PDF fetchers (v0.5.x), and Zotero
sync (v0.6) all reuse the run-manifest schema documented here.

## Design goals

- **Deterministic.** The same `.bib` file and flags always produce the
  same set of paper cards and the same manifest.
- **Offline.** Metadata comes from the BibTeX fields. No network calls
  are made. Users who want networked metadata should run
  `lgrlw add-literature --arxiv <id>` or `--doi <id>` per entry.
- **Auditable.** Every run writes
  `literature-kb/01_Raw/imports/<run_id>/` with a copy of the source
  `.bib` and a `manifest.json` enumerating every entry's outcome.
- **Safe by default.** `--on-duplicate skip` preserves existing
  paper cards; `--on-duplicate fail` aborts the whole batch atomically
  when any entry would collide with an existing paper.

## Invocation

```text
lgrlw import-bib <bib-file> \
  [--root <project-root>] [--direction <slug>] \
  [--pdf-dir <dir>] \
  [--dry-run] \
  [--on-duplicate skip|force|fail] \
  [--default-status published|accepted|preprint] \
  [--tags "tag1,tag2"]
```

### Options

| Option | Meaning |
|---|---|
| `bib-file` | Path to the BibTeX file. Required. |
| `--root` | Existing Research-Wiki project root (auto-detect if omitted). |
| `--direction` | Monorepo direction slug when `--root` points at an umbrella. |
| `--pdf-dir` | Scan this directory for local PDFs and archive matches to `literature-kb/01_Raw/pdf/<paper_id>.pdf`. No network calls. |
| `--dry-run` | Parse and plan without creating files. Prints a summary table. |
| `--on-duplicate` | `skip` (default), `force`, or `fail`. |
| `--default-status` | Status applied to every created card. Defaults to `published`. |
| `--tags` | Comma-separated tags applied to every created card. |

### Duplicate detection

Existing KB entries are indexed by `arxiv_id`, `doi`, `openalex_id`,
`semantic_scholar_id`, and `paper_id` slug. An incoming entry is a
duplicate if any of those identifiers matches an existing record.

- `--on-duplicate skip` (default): the duplicate is recorded in the
  manifest with `status=skipped_duplicate` and the existing card is
  left untouched.
- `--on-duplicate force`: the duplicate overwrites the existing card
  (and its PDF). Equivalent to `lgrlw add-literature --force
  --force-pdf`.
- `--on-duplicate fail`: `import-bib` preflights the entire bib against
  the KB before writing anything. If any entry would be a duplicate,
  the batch aborts with a non-zero exit code and **no** files are
  created.

### PDF matching (`--pdf-dir`)

`--pdf-dir` enables deterministic filename-based matching. For each
entry, the command tries — in order — to find a `*.pdf` whose stem
matches (substring, case-insensitive):

1. `arxiv_id`;
2. `cite_key`;
3. the canonical paper-id slug (`<lastname>-<year>-<title>`).

Matches are copied verbatim to `01_Raw/pdf/<paper_id>.pdf`. No fuzzy
title matching is performed here; that lives behind
`lgrlw attach-pdf` (v0.4.x) where user confirmation makes it safe.

### Source metadata

For each entry, `import-bib` extracts:

- `title`, `authors`, `year`, `venue` (from `journal` / `booktitle` /
  `publisher`);
- `doi` (from `doi` field or DOI pattern in `url` / `note`);
- `arxiv_id` (from `eprint` + `archiveprefix=arxiv`, or `url` /
  `journal` containing an arXiv id);
- `openalex_id` (from `openalex` field or `W\d+` in `url`);
- `semantic_scholar_id` (from `semantic_scholar` / similar fields, or
  40-hex ids in a Semantic Scholar URL).

The first identifier present among `arxiv_id` → `doi` →
`openalex_id` → `semantic_scholar_id` is recorded as the entry's
`mode` in the manifest (informational; v0.4 never fetches over the
network).

Entries missing `title`, `authors`, or `year` are recorded as
`status=skipped_error` and surface a non-zero exit code from the CLI.

## Output

### Created files

For each non-skipped, non-error entry `import-bib` creates the same
artifacts that `lgrlw add-literature --manual` creates:

- `literature-kb/02_Literature/Papers/<paper_id>.md`
- `literature-kb/01_Raw/metadata/<paper_id>.json`
- Optional `literature-kb/01_Raw/pdf/<paper_id>.pdf` when
  `--pdf-dir` resolves a local PDF.
- A log line in `literature-kb/00_System/log.md`.

### Manifest

`literature-kb/01_Raw/imports/<run_id>/manifest.json` captures the
entire run:

```json
{
  "schema_version": "1.0.0",
  "run_id": "20260504_143000_123456_bib_import",
  "started_at": "2026-05-04T14:30:00.123456+00:00",
  "source_bib": "…/literature-kb/01_Raw/imports/…/source.bib",
  "dry_run": false,
  "on_duplicate": "skip",
  "pdf_dir": null,
  "direction": null,
  "entries": [
    {
      "cite_key": "asai2023selfrag",
      "mode": "arxiv",
      "arxiv_id": "2310.11511",
      "doi": null,
      "title": "Self-RAG…",
      "authors": ["Akari Asai", "Zeqiu Wu"],
      "year": 2023,
      "paper_id": "asai-2023-self-rag",
      "pdf_source": "local",
      "pdf_archive": "…/literature-kb/01_Raw/pdf/asai-2023-self-rag.pdf",
      "status": "imported",
      "error": null
    }
  ],
  "counts": {
    "imported": 1,
    "skipped_duplicate": 0,
    "skipped_error": 0,
    "would_import": 0,
    "would_skip_duplicate": 0,
    "total": 1
  }
}
```

The source `.bib` is archived alongside the manifest at
`<run_id>/source.bib` so future reproductions can point at an
immutable copy.

See [`schemas/import_manifest.schema.json`](../schemas/import_manifest.schema.json)
for the complete JSON Schema.

## MCP tool

The same orchestrator is exposed through MCP as `import_bib` and
accepts matching parameters (`bib_path`, `pdf_dir`, `dry_run`,
`on_duplicate`, `default_status`, `tags`, `root`, `direction`). The
tool result mirrors the manifest and carries a `counts` summary.

See [`mcp-server.md`](./mcp-server.md) for the full MCP reference.

## Installation

`bibtexparser` ships as an optional extra so the core `lgrlw` install
stays small:

```text
pip install "lgrlw[bib]"
# or, alongside MCP:
pip install "lgrlw[bib,mcp]"
```

## Exit code

- `0` — every bib entry was either imported or deliberately skipped as
  a duplicate.
- `1` — at least one entry was `skipped_error`, or the batch aborted
  (`--on-duplicate fail`, BibTeX parse error, monorepo resolution
  error).

The manifest is always written on non-abort exits so users can audit
what happened and retry individual entries with `lgrlw
add-literature`.

## Limitations (v0.4)

- Does not fetch metadata over the network. `--prefer-network` is
  planned for v0.5 once the fetcher infrastructure is generalised to
  batch contexts.
- Does not download PDFs. `--allow-network-pdf` ships in v0.5.x with
  an explicit whitelist of arXiv / Open-Access sources.
- Does not draft paper-card body sections. That remains an agent task
  (see [`recipes/bib-to-kb.md`](./recipes/bib-to-kb.md)).
