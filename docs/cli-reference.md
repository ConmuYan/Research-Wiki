# CLI reference

The `lgrlw` CLI exposes eight top-level commands. All commands respect
`-h` / `--help` for detailed usage.

```
$ lgrlw --help
```

| Command | Summary |
|---|---|
| [`lgrlw init`](#lgrlw-init) | Bootstrap a new Research-Wiki project. |
| [`lgrlw new-workspace`](#lgrlw-new-workspace) | Create a workspace (paper or idea). |
| [`lgrlw add-literature`](#lgrlw-add-literature) | Register a paper in the KB (`--manual`, `--doi`, `--arxiv`, `--openalex`, or `--ss`). |
| [`lgrlw import-bib`](#lgrlw-import-bib) | Batch-create paper cards from a BibTeX file (v0.4). |
| [`lgrlw attach-pdf`](#lgrlw-attach-pdf) | Archive a local PDF against an existing KB paper (v0.4.x). |
| [`lgrlw convert-pdf`](#lgrlw-convert-pdf) | Render archived PDFs to Markdown via a backend plugin (v0.5). |
| [`lgrlw export-pack`](#lgrlw-export-pack) | Build an immutable KB snapshot for a workspace. |
| [`lgrlw promote`](#lgrlw-promote) | Promote an accepted workspace paper into the KB. |
| [`lgrlw lint`](#lgrlw-lint) | Verify boundary, schema, and manifest invariants. |
| [`lgrlw add-direction`](#lgrlw-add-direction) | Add a direction to a monorepo umbrella. |
| [`lgrlw mcp serve`](#lgrlw-mcp-serve) | Run the optional MCP server over stdio. |

---

## `lgrlw init`

Scaffold a new project.

```
lgrlw init <path> --direction <slug> [--monorepo] [--force]
```

| Option | Meaning |
|---|---|
| `path` | Directory to create (parents created if missing). |
| `--direction`, `-d` | Short slug naming the research direction. |
| `--monorepo` | Create a v0.3 umbrella root with the first child project under `directions/<slug>/`. |
| `--force` | Re-initialise even if `.lgrlw.toml` already exists. |

**Output.** Without `--monorepo`, `<path>/literature-kb/` is populated from
the packaged template, `<path>/research-workspaces/` is created, and
`<path>/.lgrlw.toml` marks the project. With `--monorepo`, the umbrella root
gets `.lgrlw.toml` with `monorepo = true`, and the first child project is
created at `<path>/directions/<slug>/`.

---

## `lgrlw new-workspace`

```
lgrlw new-workspace <id> --title "..." [--kind paper|idea] [--root <project-root>] [--direction <slug>]
```

| Option | Meaning |
|---|---|
| `id` | Workspace id (slug). Matches `^[a-z0-9_](?:[a-z0-9_-]*)?$`. |
| `--title` | Working title (required). |
| `--kind` | `paper` (default) or `idea`. Selects the template. |
| `--root` | Existing Research-Wiki project root (auto-detected if omitted). |
| `--direction` | Monorepo direction slug when `--root` points at a monorepo umbrella. |

**Output.** `research-workspaces/<id>/` populated from the matching
template. For `--kind paper`, `00_Project/paper_status.md` has frontmatter
rendered from the supplied title and `status: drafting`.

---

## `lgrlw add-literature`

Manual entry:

```
lgrlw add-literature --manual \
  --title "<title>" \
  --authors "<First Last, Another Name, ...>" \
  --year <yyyy> \
  [--venue "..."] [--doi ...] [--arxiv ...] [--openalex ...] [--ss ...] [--url ...] \
  [--status published|accepted|preprint] \
  [--tags "tag1,tag2"] \
  [--id <slug>] [--force] [--root <project-root>] [--direction <slug>]
```

DOI-backed entry via Crossref:

```
lgrlw add-literature --doi <doi> \
  [--status published|accepted|preprint] \
  [--tags "tag1,tag2"] \
  [--id <slug>] [--force] [--root <project-root>] [--direction <slug>]
```

arXiv-backed entry via the arXiv Atom API:

```
lgrlw add-literature --arxiv <arxiv-id-or-url> \
  [--status published|accepted|preprint] \
  [--tags "tag1,tag2"] \
  [--id <slug>] [--force] [--root <project-root>] [--direction <slug>]
```

OpenAlex-backed entry via the OpenAlex Works API:

```
lgrlw add-literature --openalex <openalex-id-or-url> \
  [--status published|accepted|preprint] \
  [--tags "tag1,tag2"] \
  [--id <slug>] [--force] [--root <project-root>] [--direction <slug>]
```

Semantic Scholar-backed entry via the S2 Graph API:

```
lgrlw add-literature --ss <s2-id-or-url-or-alias> \
  [--status published|accepted|preprint] \
  [--tags "tag1,tag2"] \
  [--id <slug>] [--force] [--root <project-root>] [--direction <slug>]
```

The `--ss` value can be any of:

- a canonical 40-char Semantic Scholar `paperId` (lowercase hex);
- a Semantic Scholar paper URL, e.g.
  `https://www.semanticscholar.org/paper/Self-Rag/649def34f8be52c8b66281af98ae884c09aef38b`;
- an S2 prefixed alias such as `DOI:10.xxxx/yyyy`, `ARXIV:2310.11511`,
  `CorpusId:263336427`, `MAG:...`, `ACL:...`, `PMID:...`, `URL:...`;
- a bare DOI or arXiv id (auto-wrapped to `DOI:` / `ARXIV:`).

The fetcher always stores the canonical 40-hex `paperId` returned by the
API in `semantic_scholar_id`.

| Option | Meaning |
|---|---|
| `--manual` | Create a hand-entered record. With `--manual`, `--doi` / `--arxiv` / `--openalex` / `--ss` are stored as metadata and do not trigger a network fetch. |
| `--doi` | Without `--manual`, fetch metadata from Crossref for the DOI. With `--manual`, store the DOI on the hand-entered record. |
| `--arxiv` | Without `--manual`, fetch metadata from the arXiv Atom API for the given id or abs URL. With `--manual`, store the arXiv id on the hand-entered record. |
| `--openalex` | Without `--manual`, fetch metadata from the OpenAlex Works endpoint for the given Work id (e.g. `W4385545131`) or `https://openalex.org/W…` URL. With `--manual`, store the OpenAlex id on the hand-entered record. |
| `--ss` | Without `--manual`, fetch metadata from the Semantic Scholar Graph API. With `--manual`, store the 40-hex `paperId` on the hand-entered record (manual mode enforces the 40-hex format; prefixed aliases are only accepted by the fetch path). `--doi`, `--arxiv`, `--openalex`, and `--ss` are mutually exclusive outside manual mode. |
| `--title` / `--authors` / `--year` | Mandatory for manual; rejected in DOI/arXiv/OpenAlex/SS fetch modes. |
| `--venue` | Free-form for manual entries (e.g. "ICLR 2024", "arXiv preprint"); rejected in DOI/arXiv/OpenAlex/SS fetch modes. |
| `--url` | Canonical URL for manual entries; rejected in DOI/arXiv/OpenAlex/SS fetch modes. |
| `--status` | One of `published` / `accepted` / `preprint`. |
| `--tags` | Comma-separated tags. |
| `--id` | Override the auto-generated slug. |
| `--force` | Replace an existing paper card and metadata with the same id. Without this flag, duplicate ids fail. |
| `--pdf` | Optional path to a local `.pdf` file. The file is copied verbatim to `literature-kb/01_Raw/pdf/<id>.pdf`; no network call is made and the source file is not modified. Works with every mode (`--manual`, `--doi`, `--arxiv`, `--openalex`, `--ss`). |
| `--force-pdf` | Replace an existing archived PDF with the same paper id. Required even together with `--force`; `--force` alone will not overwrite PDFs. |
| `--root` | Existing Research-Wiki project root (auto-detected if omitted). |
| `--direction` | Monorepo direction slug when `--root` points at a monorepo umbrella. |

**Output.**

- Paper card: `literature-kb/02_Literature/Papers/<id>.md` (frontmatter + body scaffold).
- Metadata snapshot: `literature-kb/01_Raw/metadata/<id>.json`.
- Archived PDF (only if `--pdf` was given): `literature-kb/01_Raw/pdf/<id>.pdf`.
- Log line: appended to `literature-kb/00_System/log.md`.

---

## `lgrlw import-bib`

Batch-create KB paper cards from a BibTeX file. Offline, deterministic,
and auditable: every invocation writes a manifest under
`literature-kb/01_Raw/imports/<run_id>/`.

```
lgrlw import-bib <bib-file> \
  [--root <project-root>] [--direction <slug>] \
  [--pdf-dir <dir>] \
  [--dry-run] \
  [--on-duplicate skip|force|fail] \
  [--default-status published|accepted|preprint] \
  [--tags "tag1,tag2"]
```

| Option | Meaning |
|---|---|
| `bib-file` | Path to the BibTeX file. |
| `--pdf-dir` | Scan this directory for local PDFs. Matched by arXiv id, cite key, or paper-id slug (substring, case-insensitive). Matches are archived under `01_Raw/pdf/<paper_id>.pdf`. |
| `--dry-run` | Parse and plan without writing anything. |
| `--on-duplicate skip\|force\|fail` | How to treat entries whose identifiers already exist in the KB. `fail` aborts the whole batch before any write. |
| `--default-status` | Publication status applied to every card (`published` / `accepted` / `preprint`). |
| `--tags` | Comma-separated tags applied to every card. |
| `--root` / `--direction` | Project-root / monorepo-direction selectors. |

Requires the optional `bib` extra:

```
pip install "lgrlw[bib]"
```

See [`import-bib.md`](./import-bib.md) for the full protocol, manifest
schema, and exit-code semantics.

---

## `lgrlw attach-pdf`

Archive a local PDF against an existing KB paper. Two modes:

```
# explicit: paper-id + PDF path
lgrlw attach-pdf ./papers/self-rag.pdf --id asai-2023-self-rag \
  [--force-pdf] [--move] [--root <project-root>] [--direction <slug>]

# scan: walk a directory and auto-match by filename
lgrlw attach-pdf --scan-dir ./downloads [--force-pdf] [--move] \
  [--root <project-root>] [--direction <slug>]

# scan-incoming: shortcut for literature-kb/01_Raw/pdf/_incoming/
lgrlw attach-pdf --scan-incoming [--force-pdf] [--move] \
  [--root <project-root>] [--direction <slug>]
```

| Option | Meaning |
|---|---|
| `pdf` (positional) | Local PDF path. Required in explicit mode, rejected in scan mode. |
| `--id <paper-id>` | KB paper id. Required in explicit mode. |
| `--scan-dir <dir>` | Scan the directory for `*.pdf` files (non-recursive). |
| `--scan-incoming` | Shortcut for scanning `literature-kb/01_Raw/pdf/_incoming/`. Mutually exclusive with `--scan-dir`. |
| `--force-pdf` | Replace an existing archived PDF for the same paper id. |
| `--move` | Delete the source PDF after a successful archive (non-fatal on failure). |
| `--root` / `--direction` | Project-root / monorepo selectors. |

**Matcher (scan modes).** Filename (stem, lowercased) is matched against
existing KB papers in this order: paper-id substring → arXiv id → DOI
(flattened to alphanumerics). No fuzzy title matching in v0.4.x.

**Output.**

- Copies the PDF to `literature-kb/01_Raw/pdf/<paper_id>.pdf`.
- Appends an `attach-pdf` line to `literature-kb/00_System/log.md`.
- Returns a status table; exit code is non-zero only when at least one
  entry is `skipped_error`. `unmatched` scan results are informational.

---

## `lgrlw convert-pdf`

Render archived PDFs under `literature-kb/01_Raw/pdf/` into Markdown
under `literature-kb/01_Raw/mineru_md/<paper_id>/`. The backend is
pluggable:

- `stub` (default, zero-dependency): writes a deterministic placeholder
  Markdown file recording the source PDF. Use this to wire up agent
  workflows that fill the body in later.
- `mineru` (optional): requires `pip install "lgrlw[mineru]"` and
  delegates to MinerU's `magic-pdf` library for a full extraction.

```
lgrlw convert-pdf <paper-id> [--backend stub|mineru] [--force] \
  [--root <project-root>] [--direction <slug>]

lgrlw convert-pdf --all [--backend stub|mineru] [--force] \
  [--root <project-root>] [--direction <slug>]
```

| Option | Meaning |
|---|---|
| `paper-id` | KB paper id. Mutually exclusive with `--all`. |
| `--all` | Convert every paper that has an archived PDF under `01_Raw/pdf/`. |
| `--backend` | Converter backend; `stub` default, `mineru` needs the optional extra. |
| `--force` | Replace an existing output directory for the same paper id. |
| `--root` / `--direction` | Standard project-root / monorepo selectors. |

**Output.**

- Creates `literature-kb/01_Raw/mineru_md/<paper_id>/<paper_id>.md`
  (and, for `mineru`, any extracted assets alongside it).
- Appends a `convert-pdf` line to `literature-kb/00_System/log.md`.
- Exit code is non-zero if any paper reports `skipped_error`.

---

## `lgrlw export-pack`

```
lgrlw export-pack <workspace-id> [--root <project-root>] [--direction <slug>]
```

Builds a dated KB snapshot under
`literature-kb/06_Exports/<workspace-id>_<YYYY-MM-DD>/`, simultaneously
mirrored into
`research-workspaces/<workspace-id>/01_KB_Exports/<same-name>/`. The pack
root contains `export_manifest.json` with SHA-256 for every file. See
[`export-protocol.md`](./export-protocol.md) for the full spec.

Pass `--direction <slug>` when operating from a monorepo umbrella.

---

## `lgrlw promote`

```
lgrlw promote <workspace-id> [--id <slug>] [--force] [--root <project-root>] [--direction <slug>]
```

Promote an accepted workspace paper into the KB. The full protocol
lives in [`promotion-protocol.md`](./promotion-protocol.md); the CLI
enforces every precondition before writing anything.

| Option | Meaning |
|---|---|
| `workspace` | Workspace id (directory under `research-workspaces/`). |
| `--id` | Override the auto-generated `<lastname>-<year>-<title>` slug. |
| `--force` | Replace an existing paper card / metadata / BibTeX entry with the same id. Without this flag, duplicates fail. |
| `--root` | Existing Research-Wiki project root (auto-detected if omitted). |
| `--direction` | Monorepo direction slug when `--root` points at a monorepo umbrella. |

**Preconditions enforced.**

- `00_Project/paper_status.md` frontmatter has `status: accepted` and
  non-null `final_title`, `final_authors`, `venue`, `year`, plus at
  least one of `doi` or `arxiv_id`.
- `06_Promotion/final_metadata.md` references a camera-ready PDF path
  or public-version URL.
- `06_Promotion/promotion_checklist.md` has every `- [ ]` ticked into
  `- [x]` and contains at least one tick.
- `06_Promotion/add_back_to_kb_plan.md` lists at least one intended
  field-structure / evidence-map / method-taxonomy edit as a `- `
  bullet (the command does *not* apply these automatically; it prints
  a follow-up reminder).

**Outputs (atomic).**

- Paper card: `literature-kb/02_Literature/Papers/<id>.md`
  (`source: promoted`, `status: accepted`).
- Metadata snapshot: `literature-kb/01_Raw/metadata/<id>.json`.
- BibTeX entry: `literature-kb/01_Raw/bibtex/<id>.bib`
  (auto-generated `@inproceedings` if `venue` is set, `@misc`
  otherwise; replace it manually if you have a curated version).
- Log line: appended to `literature-kb/00_System/log.md`.

If any precondition fails or any single write fails, no artefacts are
left on disk. The workspace is never modified.

---

## `lgrlw lint`

```
lgrlw lint [<project-root>] [--root <project-root>] [--direction <slug>]
```

Runs every invariant check:

- `structure.*` &mdash; the project root has `.lgrlw.toml`, `literature-kb/`,
  `research-workspaces/`.
- `schema.*` &mdash; every paper card and every `paper_status.md` satisfies
  its pydantic schema.
- `boundary.*` &mdash; no workspace content / reference / status value
  leaked into the KB.
- `manifest.*` &mdash; every export pack has a valid manifest and every
  recorded SHA-256 matches.

Exits `0` iff there are no findings. Warnings such as
`manifest.file_extra` are reported and also produce a non-zero exit code.

When invoked at a monorepo umbrella root without `--direction`, `lint`
recursively checks every direction listed in the umbrella `.lgrlw.toml` and
renders findings with `directions/<slug>/...` paths. With `--direction`, only
that subproject is checked.

---

## `lgrlw add-direction`

```
lgrlw add-direction <slug> [--root <monorepo-root>] [--force]
```

Adds a child project under `directions/<slug>/` to an existing monorepo
umbrella and appends the slug to the umbrella `.lgrlw.toml` `directions`
array.

| Option | Meaning |
|---|---|
| `slug` | New direction slug. Matches the same slug grammar as paper ids (`^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$`). |
| `--root` | Monorepo umbrella root (auto-detected if omitted). |
| `--force` | Re-materialise `directions/<slug>/` if it already exists. |

---

## `lgrlw mcp serve`

```
lgrlw mcp serve [--root <project-root-or-monorepo-root>]
```

Runs the optional Model Context Protocol server over stdio. Install it with:

```
pip install "lgrlw[mcp]"
```

The server exposes tools mirroring the CLI (`init_project`,
`new_workspace`, `add_literature`, `export_pack`, `promote`, `lint`,
`add_direction`) and read-only resources for the default project's summary,
paper cards, and workspaces. See [`mcp-server.md`](./mcp-server.md).

## Project root semantics

- `lgrlw init <path>` creates either a single-direction project or, with `--monorepo`, an umbrella root and the first `directions/<slug>/` child project.
- `lgrlw new-workspace`, `lgrlw add-literature`, `lgrlw export-pack`, and `lgrlw promote` operate on an existing single-direction project. In a monorepo, pass the umbrella `--root` plus `--direction <slug>` (or run from inside `directions/<slug>/`).
- `lgrlw lint` accepts either a positional project root (`lgrlw lint <project-root>`) or `--root <project-root>` for consistency with the other project-scoped commands. Supplying both with different paths is an error. A monorepo umbrella is linted recursively unless `--direction` is provided.

## Global options

- `--help`, `-h` &mdash; show command help.
- `--version`, `-V` &mdash; print installed `lgrlw` version.

## Environment

Networked ingestion honours each source's polite-pool / authentication conventions:

- `CROSSREF_MAILTO` &mdash; contact email forwarded to Crossref's polite pool when `--doi` is used.
- `OPENALEX_EMAIL` &mdash; contact email forwarded to OpenAlex's polite pool when `--openalex` is used.
- `S2_API_KEY` &mdash; Semantic Scholar API key sent in the `x-api-key` header when `--ss` is used. Recommended to avoid HTTP 429 rate limits. Never printed in CLI output.
