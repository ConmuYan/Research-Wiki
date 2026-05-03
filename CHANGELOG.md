# Changelog

All notable changes to Research-Wiki are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## [Unreleased]

### Added

- `lgrlw init --monorepo`, `lgrlw add-direction`, and `--direction <slug>`
  selectors on project-scoped commands add multi-direction monorepo support
  under `directions/<slug>/`. `lgrlw lint` now recursively checks every
  registered direction when invoked at a monorepo umbrella root.
- Optional Model Context Protocol server via `pip install "lgrlw[mcp]"`
  and `lgrlw mcp serve`. The server exposes typed tools for
  `init_project`, `add_direction`, `new_workspace`, `add_literature`,
  `export_pack`, `promote`, and `lint`, plus read-only resources for KB
  papers, workspaces, and project summaries.
- New documentation: `docs/monorepo.md`, `docs/mcp-server.md`, and
  `schemas/project_config.schema.json`.

## [0.2.0] - 2026-05-03

### Added — Networked literature ingestion

- `PaperMetadata` schema modelling canonical metadata returned by every
  networked fetcher, backed by a `BaseFetcher` abstract interface and
  shared `FetcherError` / `FetcherNotFoundError` hierarchy.
- `CrossrefFetcher` and `lgrlw add-literature --doi` for DOI-backed
  ingestion via the Crossref REST API. Honours the `CROSSREF_MAILTO`
  polite-pool environment variable.
- `ArxivFetcher` and `lgrlw add-literature --arxiv` for arXiv Atom-API
  ingestion, accepting both bare ids (`2310.11511`) and abstract URLs.
- `OpenAlexFetcher` and `lgrlw add-literature --openalex` for the
  OpenAlex Works endpoint, accepting bare Work ids (`W4385545131`) and
  `https://openalex.org/W…` URLs. Honours the `OPENALEX_EMAIL`
  polite-pool environment variable.
- `SemanticScholarFetcher` and `lgrlw add-literature --ss` for the
  Semantic Scholar Graph API. Accepts the full range of identifier
  forms the S2 API recognises: a bare 40-hex `paperId`, a Semantic
  Scholar paper URL (with or without human slug / query string),
  prefixed aliases (`DOI:` / `ARXIV:` / `CorpusId:` / `MAG:` / `ACL:`
  / `PMID:` / `PMCID:` / `URL:`), and bare DOIs / arXiv ids
  (auto-wrapped to `DOI:` / `ARXIV:` before the request). Honours the
  `S2_API_KEY` environment variable for the polite-pool `x-api-key`
  header and surfaces HTTP 429 with a hint pointing at `S2_API_KEY`.
- `--doi` / `--arxiv` / `--openalex` / `--ss` are mutually exclusive
  outside `--manual` mode. Under `--manual`, each identifier flag
  stores the value as hand-entered metadata without a network call
  and is still validated by the schema patterns below.
- `OPENALEX_ID_PATTERN` and `SEMANTIC_SCHOLAR_ID_PATTERN` schema
  constraints, with mirrored `pattern` properties on `openalex_id` /
  `semantic_scholar_id` in `schemas/paper.schema.json` and
  `schemas/paper_metadata.schema.json`. Every identifier is validated
  end-to-end by both pydantic and JSON Schema.
- Every fetcher ships with a `respx`-mocked CLI-level test suite
  covering the happy path, HTTP 404 / 429 / malformed JSON failures,
  polite-pool env-var forwarding, and mutual-exclusion rules.

### Added — Promotion ceremony

- `lgrlw promote <workspace>` implementing the v0.2 promotion
  ceremony from `docs/promotion-protocol.md`. Enforces every
  precondition read-only before any write:
  - `00_Project/paper_status.md` frontmatter has
    `status: accepted` plus non-null `final_title`, `final_authors`,
    `venue`, `year`, and at least one of `doi` or `arxiv_id`;
  - `06_Promotion/final_metadata.md` references a camera-ready PDF
    path or public-version URL;
  - `06_Promotion/promotion_checklist.md` has every `- [ ]`
    converted to `- [x]` and contains at least one tick;
  - `06_Promotion/add_back_to_kb_plan.md` lists at least one
    intended field-structure / evidence-map / method-taxonomy edit
    as a `- ` bullet.
- On success, promotion atomically emits:
  - a paper card at `literature-kb/02_Literature/Papers/<id>.md`
    with `source: promoted` and `status: accepted`;
  - a metadata snapshot at `literature-kb/01_Raw/metadata/<id>.json`;
  - an auto-generated BibTeX entry at
    `literature-kb/01_Raw/bibtex/<id>.bib` (`@inproceedings` when
    `venue` is set, `@misc` otherwise);
  - an audit line in `literature-kb/00_System/log.md`.
- Taxonomy / evidence updates listed in
  `06_Promotion/add_back_to_kb_plan.md` remain a deliberate manual
  follow-up; the command prints a yellow reminder but never
  auto-edits `03_Field_Structure/` or `05_Evidence/`.
- Writes are rolled back on any OSError mid-flight so promotion
  stays all-or-nothing.
- `--id` overrides the auto-generated slug; `--force` replaces an
  existing paper card / metadata / BibTeX with the same id.
- `templates/research-workspace/paper/06_Promotion/promotion_checklist.md`
  rewritten as a real GitHub-style `- [ ]` task list so
  `lgrlw promote` can parse and validate completion.

### Added — Internals

- Shared `lgrlw._slug.paper_slug(first_author, year, title)` helper
  used by both `lgrlw add-literature` and `lgrlw promote`, ensuring
  a paper id stays stable whether the entry was hand-registered,
  fetched, or promoted from an accepted workspace.
- End-to-end guide-style integration test
  (`tests/test_e2e_guide.py`) that walks the exact README Quick Start
  sequence (init → new-workspace → four `add-literature` invocations
  → export-pack → seed preconditions → promote → lint) and fails
  loudly if any step of the documented flow regresses.

### Changed

- CI now builds distributions and runs `twine check` on every test
  matrix entry.
- `lgrlw` CLI help text and `--version` both advertise the full v0.2
  command set (`init` / `new-workspace` / `add-literature` with
  `--manual` + four networked sources / `export-pack` / `promote` /
  `lint`).

### Fixed

- v0.2.0 CI was failing on every matrix entry because `lgrlw lint`
  reported `manifest.sha256_mismatch` for the demo export pack: text
  files had been authored on Windows where Python's `Path.write_text`
  silently translates `\n` into `\r\n`, so the SHA-256 digests recorded
  in `export_manifest.json` no longer matched the LF bytes git stored
  on Linux. The fix introduces a repo-wide `.gitattributes`
  (`* text=auto eol=lf` plus explicit `text eol=lf` for `*.py / *.md /
  *.yml / *.yaml / *.toml / *.json / *.bib` and `binary` for
  `*.png / *.jpg / *.pdf / *.ico`), and forces every `Path.write_text`
  / `path.open("a", ...)` call across `src/lgrlw/fs.py`,
  `src/lgrlw/export/pack.py`, `src/lgrlw/commands/add_literature.py`,
  `src/lgrlw/commands/init.py`, `src/lgrlw/config.py`, and
  `src/lgrlw/promote/run.py` to pass `newline="\n"` explicitly.
  Combined, KB export packs now have byte-identical SHA-256 hashes
  across Windows and Linux. `examples/demo_direction/` was renormalised
  to LF bytes and its export pack regenerated. The `v0.2.0` tag was
  moved forward to include this fix.

## [0.1.0] - 2026-05-02

### Added

- Initial `lgrlw` CLI with five v0.1 commands:
  - `lgrlw init`
  - `lgrlw new-workspace`
  - `lgrlw add-literature --manual`
  - `lgrlw export-pack`
  - `lgrlw lint`
- Three-space Research-Wiki project layout:
  - `literature-kb/`
  - `research-workspaces/`
  - immutable KB export packs under `literature-kb/06_Exports/` and
    mirrored into workspaces.
- Literature KB templates with KB constitution, add-literature protocol,
  export protocol, verification policy, field-structure stubs, concept
  folders, and evidence-map stubs.
- Research workspace templates for `paper` and `idea` workspaces.
- Pydantic models and JSON Schemas for paper frontmatter, workspace
  status frontmatter, and export manifests.
- Lint rule families for structure, frontmatter schema, KB/workspace
  boundary checks, and export manifest integrity.
- Export manifests with SHA-256 hashes for every copied file.
- Documentation for architecture, lifecycle, boundary rules, export
  protocol, promotion protocol (v0.2 specification), agents, and CLI.
- `examples/demo_direction/`, a metadata-only RAG demo project with a
  lint-clean export pack.
- GitHub Actions CI for ruff, formatting, pytest, and demo lint smoke.
- Wheel packaging of bundled `templates/` and `schemas/` resources.
- `CODE_OF_CONDUCT.md`.

### Changed

- `lgrlw lint` exits non-zero if **any** finding is present, including
  warning-severity findings. Release CI therefore treats warning-only
  manifests as non-clean.
- `lgrlw add-literature --manual` refuses duplicate paper IDs by default
  and permits intentional replacement only with explicit `--force`.
- `literature-kb/00_System/*.md` is exempt from the
  `boundary.workspace_reference_in_kb` text-reference rule because those
  files are KB tooling documentation that legitimately describe workspace
  paths by name.

### Not included in v0.1.0

- Network fetchers (`--arxiv`, `--doi`, OpenAlex, Semantic Scholar,
  Crossref).
- MinerU integration.
- `lgrlw promote` implementation.
- Zotero integration, MCP servers, dashboards, vector stores, or PDF
  processing pipelines.
