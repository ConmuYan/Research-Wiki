# Changelog

All notable changes to Research-Wiki are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic versioning.

## [Unreleased]

### Added

- Development branch for v0.2 networked literature ingestion.
- `PaperMetadata` schema and Crossref fetcher foundation with mocked HTTP
  tests.
- `lgrlw add-literature --doi` Crossref ingestion path with CLI-level
  mocked tests.
- `ArxivFetcher` using the arXiv Atom API, plus
  `lgrlw add-literature --arxiv` ingestion path with CLI-level mocked
  tests. `--manual --arxiv` still stores the id as hand-entered metadata
  without performing a network call.
- `OpenAlexFetcher` using the OpenAlex Works API, plus
  `lgrlw add-literature --openalex` ingestion path with CLI-level mocked
  tests. The fetcher honours the `OPENALEX_EMAIL` polite-pool
  environment variable, normalises `https://openalex.org/W…` URLs, and
  is mutually exclusive with `--doi` / `--arxiv` outside manual mode.
  `--manual --openalex` still stores the id as hand-entered metadata
  without performing a network call.
- `OPENALEX_ID_PATTERN` schema constraint plus mirrored `pattern`
  property in `schemas/paper.schema.json` and
  `schemas/paper_metadata.schema.json`, validating `openalex_id`
  fields end-to-end.
- `lgrlw promote` command implementing the full v0.2 promotion
  ceremony from `docs/promotion-protocol.md`. It enforces every
  precondition (`paper_status.md` frontmatter status / promotion
  fields / identifiers, `06_Promotion/final_metadata.md` URL or PDF
  reference, fully ticked `promotion_checklist.md`,
  bullet-listed `add_back_to_kb_plan.md`) and only then writes a
  paper card (`source: promoted`), metadata snapshot, BibTeX entry
  (`@inproceedings` / `@misc`) and a log line. Writes are
  rolled back on failure so promotion stays all-or-nothing.
  Taxonomy / evidence updates from `add_back_to_kb_plan.md` remain
  a manual follow-up (the command prints a reminder).
- `templates/research-workspace/paper/06_Promotion/promotion_checklist.md`
  rewritten as a real `- [ ]` task list so `lgrlw promote` can parse
  and validate completion.
- Shared `lgrlw._slug.paper_slug` helper used by both
  `lgrlw add-literature` and `lgrlw promote`, ensuring a paper id
  stays stable whether the entry was hand-registered or promoted
  from an accepted workspace.
- `lgrlw add-literature --ss` ingestion path via the Semantic Scholar
  Graph API (`https://api.semanticscholar.org/graph/v1/paper`). The
  new `SemanticScholarFetcher` accepts the full range of identifier
  forms the S2 API recognises: a bare 40-char `paperId`, a Semantic
  Scholar paper URL (with or without the human slug / query string),
  prefixed aliases (`DOI:` / `ARXIV:` / `CorpusId:` / `MAG:` / `ACL:`
  / `PMID:` / `URL:`), and bare DOIs / arXiv ids (auto-wrapped to
  `DOI:` / `ARXIV:` before the request). Respects the `S2_API_KEY`
  environment variable for the polite-pool `x-api-key` header and
  reports HTTP 429 with a hint pointing at `S2_API_KEY`. `--ss` is
  mutually exclusive with `--doi` / `--arxiv` / `--openalex` outside
  manual mode; `--manual --ss <paperId>` still records the id without
  a network call and enforces the 40-hex `paperId` format.
- `SEMANTIC_SCHOLAR_ID_PATTERN` schema constraint plus mirrored
  `pattern` property in `schemas/paper.schema.json` and
  `schemas/paper_metadata.schema.json`, validating
  `semantic_scholar_id` fields end-to-end.

### Changed

- CI now builds distributions and runs `twine check` on every test matrix
  entry.

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
