# AGENTS.md — Research-Wiki repository constitution

> This file is the **top-level constitution** that LLM agents (Claude Code,
> Cursor, Windsurf, Aider, Codex, etc.) must read before operating on this
> repository.
>
> It governs the *code and docs* of the Research-Wiki project itself.
> Separately, each `literature-kb/` and `research-workspaces/<project>/`
> directory that an end-user creates will have its **own** `AGENTS.md`
> (`KB_AGENTS.md` / `PAPER_AGENTS.md`) governing that space.

---

## 0. Identity

This repository is **Research-Wiki**, the reference implementation of the
*Literature-Grounded Research Lifecycle Wiki* (LGRLW) protocol.

**Name conventions agents must use consistently:**

- **Research-Wiki** — the project and repository name; what end users see
  on GitHub. Use this in user-facing docs and marketing copy.
- **LGRLW** — the abstract protocol name. Use this when citing the
  methodology independently of its implementation (e.g., in an academic
  reference, in docs that discuss the state machine).
- **`lgrlw`** — the Python package and CLI entry point. Use this in code,
  `pip install` instructions, shell examples, and API references.

A `research-wiki` CLI alias may be added later, but `lgrlw` remains the
canonical entry point and the import name. Do not introduce a third name.

It ships:

- A Python CLI and library (`lgrlw`, under `src/lgrlw/`)
- Markdown / YAML templates (under `templates/`)
- JSON schemas (under `schemas/`)
- Documentation (under `docs/`)

Agents operating here work on *the tool itself*, not on a research direction.

---

## 1. Non-negotiable invariants

You must never break these, even if asked:

1. **Three-space separation in template output.**
   Any generated `literature-kb/` skeleton must remain writable only by
   `add-literature` and `promote`. Any generated `research-workspaces/*/`
   skeleton must never contain structures that can be confused with KB.

2. **Schema is a contract.**
   `src/lgrlw/schemas.py` (pydantic) and `schemas/*.schema.json` (JSON Schema)
   must stay in sync. If you change one, change the other in the same PR.

3. **Boundary lint must strengthen, never weaken.**
   New PRs may add lint rules; they may not silently relax existing ones.
   Relaxations require an explicit CHANGELOG entry and a test.

4. **No hidden network calls.**
   Every outbound HTTP call lives in `src/lgrlw/fetchers/` and is covered by
   a mocked test in `tests/test_fetchers.py` using `respx`.

5. **No state outside the user's project directory.**
   `lgrlw` may only read/write under the invoked project root and
   `platformdirs`-provided cache directories. Never touch `$HOME` arbitrarily.

6. **Chinese-friendly, English-first.**
   Code, docstrings, CLI help, and primary `README.md` are in English.
   `README.zh-CN.md`, `docs/*.zh-CN.md` (when present) may mirror in Chinese.

---

## 2. Expected workflow for code changes

1. Read [`docs/architecture.md`](./docs/architecture.md) and
   [`docs/boundary-rules.md`](./docs/boundary-rules.md) before touching
   anything in `src/lgrlw/lint/` or `src/lgrlw/commands/promote.py`.

2. For any new CLI command:
   - Add it to `src/lgrlw/commands/`.
   - Register it in `src/lgrlw/cli.py`.
   - Add a section to `docs/cli-reference.md`.
   - Add at least one unit test under `tests/`.

3. For any new fetcher:
   - Subclass `lgrlw.fetchers.base.BaseFetcher`.
   - Return a canonical `lgrlw.schemas.PaperMetadata`.
   - Provide a `respx`-mocked test.

4. For any new lint rule:
   - Put it in `src/lgrlw/lint/`.
   - Add a fixture under `tests/fixtures/` that is *intentionally violating*
     the rule, and a fixture that is clean.
   - The rule must be deterministic; no network, no time-dependent logic.

5. Before opening a PR, run:
   ```bash
   ruff check src tests
   ruff format --check src tests
   pytest -q
   ```

---

## 3. Style and ergonomics

- Python 3.10+; use `X | Y` unions, PEP 604 types, `list[T]` not `List[T]`.
- Public API must be type-annotated. `mypy --strict` should pass on `src/`.
- CLI output uses `rich` for human-facing messages; machine output is JSON
  behind `--json`.
- Never print secrets or API keys. Fetchers must accept keys via env vars
  (`OPENALEX_EMAIL`, `S2_API_KEY`) and document them in
  `docs/cli-reference.md`.
- Do not add emoji to code or docs unless the user explicitly requests it.

---

## 4. Things agents should *not* do here

- Do **not** invent new top-level directories. The ones documented in
  `README.md` are the full set.
- Do **not** add heavyweight dependencies (databases, ML frameworks, vector
  stores). This project is a **protocol and a small CLI**, not a platform.
- Do **not** rename `lgrlw` without an RFC issue and explicit maintainer
  approval; the name is referenced in installed entry points and user configs.
- Do **not** embed PDFs, datasets, or weights in the repository. Examples
  under `examples/` must reference upstream sources by URL / DOI / arXiv ID.
- Do **not** write anything resembling a draft research paper, hypothesis,
  or experimental claim into this repo. This repo is the *framework*; user
  research lives in user projects generated by `lgrlw init`.

---

## 5. When in doubt

When the correct action is unclear, open (or reference) a GitHub issue and
stop. It is better to leave a clean TODO comment and ask than to ship a
subtle violation of the three-space invariant.

See also:

- [`docs/architecture.md`](./docs/architecture.md)
- [`docs/lifecycle.md`](./docs/lifecycle.md)
- [`docs/boundary-rules.md`](./docs/boundary-rules.md)
- [`docs/agents-guide.md`](./docs/agents-guide.md) — for agents operating on
  *user research projects* rather than this repository.
