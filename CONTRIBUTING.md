# Contributing to Research-Wiki

Thank you for considering a contribution. This project is a **protocol plus a
small CLI**, not a platform. Contributions that sharpen the protocol or keep
the core small and verifiable are the most valuable.

## What this repo is (and is not)

**Is:**
- A set of Markdown / YAML templates for a research knowledge base.
- A Python CLI (`lgrlw`) that creates, validates, and promotes content in
  those templates.
- A set of documented invariants (three-space separation, lint, export
  manifests).

**Is not:**
- A vector database or RAG pipeline.
- A PDF reader, OCR stack, or GPU-bound tool.
- A SaaS.
- A monorepo for your own papers.

If your contribution adds heavyweight dependencies or imports a vector store,
please open an issue first proposing it as a *plugin* instead.

---

## Development setup

```bash
git clone https://github.com/your-org/research-wiki.git
cd research-wiki
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# POSIX
source .venv/bin/activate

pip install -e ".[dev]"
pre-commit install   # optional, if you use pre-commit
```

### Before you push

```bash
ruff check src tests
ruff format --check src tests
pytest -q
```

For type checking (strongly encouraged on `src/`):

```bash
mypy src
```

---

## Commit and PR hygiene

- Prefer small, focused PRs. One lint rule or one fetcher per PR.
- Reference an issue number in the PR title when applicable.
- Update `CHANGELOG.md` under `## Unreleased` for every user-visible change.
- If you touch schemas, update both `src/lgrlw/schemas.py` (pydantic) and
  `schemas/*.schema.json` in the same commit.
- If you touch boundary/lint rules, add a *violating* fixture and a *clean*
  fixture under `tests/fixtures/` in the same commit.

Conventional Commit prefixes are welcome but not required:
`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.

---

## Where to contribute

- **New fetchers** *(v0.2 milestone)*. The `lgrlw.fetchers` subpackage is
  scheduled for v0.2. When it lands, contributions subclass
  `lgrlw.fetchers.base.BaseFetcher`, return a canonical
  `lgrlw.schemas.PaperMetadata`, and ship a `respx`-mocked unit test. Until
  then, please open an issue against the v0.2 milestone before starting
  work on a specific source.
- **New lint rules.** Add under `src/lgrlw/lint/`. Each rule must be pure and
  deterministic (no network, no clock dependence).
- **New templates.** Propose changes to `templates/` in an issue first — the
  template skeleton is a stable API for user projects.
- **Docs.** The `docs/` folder is first-class; docs PRs are welcome.
- **Agent prompts.** If you maintain a ruleset for a specific LLM agent
  (Claude Code, Cursor, Windsurf, Aider, Codex), please contribute it under
  `docs/agents/<agent-name>.md`.

---

## Issue labels

| Label | Meaning |
|---|---|
| `good first issue` | Small, self-contained; a friendly entry point. |
| `help wanted` | The maintainers would welcome outside help. |
| `protocol` | Touches the three-space invariant; needs careful review. |
| `agent-integration` | Concerns `AGENTS.md` semantics for LLM agents. |
| `fetcher` | Adds or updates an external metadata source. |
| `lint` | Adds or refines a boundary/schema/link rule. |

---

## Code of Conduct

This project follows the [Contributor Covenant v2.1](./CODE_OF_CONDUCT.md).
By participating, you are expected to uphold it.

---

## License

By contributing, you agree that your contributions will be licensed under the
[MIT License](./LICENSE).
