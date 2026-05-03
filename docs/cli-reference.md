# CLI reference

The `lgrlw` CLI exposes five commands. All commands respect
`-h` / `--help` for detailed usage.

```
$ lgrlw --help
```

| Command | Summary |
|---|---|
| [`lgrlw init`](#lgrlw-init) | Bootstrap a new Research-Wiki project. |
| [`lgrlw new-workspace`](#lgrlw-new-workspace) | Create a workspace (paper or idea). |
| [`lgrlw add-literature`](#lgrlw-add-literature) | Register a paper in the KB (`--manual`, `--doi`, `--arxiv`, `--openalex`, or `--ss`). |
| [`lgrlw export-pack`](#lgrlw-export-pack) | Build an immutable KB snapshot for a workspace. |
| [`lgrlw promote`](#lgrlw-promote) | Promote an accepted workspace paper into the KB. |
| [`lgrlw lint`](#lgrlw-lint) | Verify boundary, schema, and manifest invariants. |

---

## `lgrlw init`

Scaffold a new project.

```
lgrlw init <path> --direction <slug> [--force]
```

| Option | Meaning |
|---|---|
| `path` | Directory to create (parents created if missing). |
| `--direction`, `-d` | Short slug naming the research direction. |
| `--force` | Re-initialise even if `.lgrlw.toml` already exists. |

**Output.** `<path>/literature-kb/` populated from the packaged template,
an empty `<path>/research-workspaces/` with a pointer README, and
`<path>/.lgrlw.toml`.

---

## `lgrlw new-workspace`

```
lgrlw new-workspace <id> --title "..." [--kind paper|idea] [--root <project-root>]
```

| Option | Meaning |
|---|---|
| `id` | Workspace id (slug). Matches `^[a-z0-9_](?:[a-z0-9_-]*)?$`. |
| `--title` | Working title (required). |
| `--kind` | `paper` (default) or `idea`. Selects the template. |
| `--root` | Existing Research-Wiki project root (auto-detected if omitted). |

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
  [--id <slug>] [--force] [--root <project-root>]
```

DOI-backed entry via Crossref:

```
lgrlw add-literature --doi <doi> \
  [--status published|accepted|preprint] \
  [--tags "tag1,tag2"] \
  [--id <slug>] [--force] [--root <project-root>]
```

arXiv-backed entry via the arXiv Atom API:

```
lgrlw add-literature --arxiv <arxiv-id-or-url> \
  [--status published|accepted|preprint] \
  [--tags "tag1,tag2"] \
  [--id <slug>] [--force] [--root <project-root>]
```

OpenAlex-backed entry via the OpenAlex Works API:

```
lgrlw add-literature --openalex <openalex-id-or-url> \
  [--status published|accepted|preprint] \
  [--tags "tag1,tag2"] \
  [--id <slug>] [--force] [--root <project-root>]
```

Semantic Scholar-backed entry via the S2 Graph API:

```
lgrlw add-literature --ss <s2-id-or-url-or-alias> \
  [--status published|accepted|preprint] \
  [--tags "tag1,tag2"] \
  [--id <slug>] [--force] [--root <project-root>]
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
| `--root` | Existing Research-Wiki project root (auto-detected if omitted). |

**Output.**

- Paper card: `literature-kb/02_Literature/Papers/<id>.md` (frontmatter + body scaffold).
- Metadata snapshot: `literature-kb/01_Raw/metadata/<id>.json`.
- Log line: appended to `literature-kb/00_System/log.md`.

---

## `lgrlw export-pack`

```
lgrlw export-pack <workspace-id> [--root <project-root>]
```

Builds a dated KB snapshot under
`literature-kb/06_Exports/<workspace-id>_<YYYY-MM-DD>/`, simultaneously
mirrored into
`research-workspaces/<workspace-id>/01_KB_Exports/<same-name>/`. The pack
root contains `export_manifest.json` with SHA-256 for every file. See
[`export-protocol.md`](./export-protocol.md) for the full spec.

---

## `lgrlw promote`

```
lgrlw promote <workspace-id> [--id <slug>] [--force] [--root <project-root>]
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
lgrlw lint [<project-root>] [--root <project-root>]
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

## Project root semantics

- `lgrlw init <path>` creates a new project at `<path>` and does not accept `--root`.
- `lgrlw new-workspace`, `lgrlw add-literature`, `lgrlw export-pack`, and `lgrlw promote` operate on an existing project. Pass `--root <project-root>` explicitly, or omit it to auto-detect the nearest ancestor containing `.lgrlw.toml`.
- `lgrlw lint` accepts either a positional project root (`lgrlw lint <project-root>`) or `--root <project-root>` for consistency with the other project-scoped commands. Supplying both with different paths is an error.

## Global options

- `--help`, `-h` &mdash; show command help.
- `--version`, `-V` &mdash; print installed `lgrlw` version.

## Environment

Networked ingestion honours each source's polite-pool / authentication conventions:

- `CROSSREF_MAILTO` &mdash; contact email forwarded to Crossref's polite pool when `--doi` is used.
- `OPENALEX_EMAIL` &mdash; contact email forwarded to OpenAlex's polite pool when `--openalex` is used.
- `S2_API_KEY` &mdash; Semantic Scholar API key sent in the `x-api-key` header when `--ss` is used. Recommended to avoid HTTP 429 rate limits. Never printed in CLI output.
