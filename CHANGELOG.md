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
