# KB_AGENTS.md &mdash; Literature KB constitution

> LLM agents (Claude Code, Cursor, Windsurf, Aider, Codex, &hellip;) operating
> inside this `literature-kb/` directory **must read this file before any
> write**. End-users: this is the rulebook. Disagreement is fine; violation
> is not.

---

## 0. Identity

This directory is the **Literature KB** of a single research direction.
It represents the *public literature world* &mdash; what the field has
published &mdash; as curated by this project's maintainer.

This KB is governed by the *Literature-Grounded Research Lifecycle Wiki*
(LGRLW) protocol. `lgrlw` is the CLI. See the repository root's
`AGENTS.md` for tooling-level rules.

---

## 1. Non-negotiable invariants

These rules are enforced by `lgrlw lint`. CI fails on any violation.

1. **No workspace content may live here.** Ideas, hypotheses, experiment
   logs, manuscript drafts, rebuttals, unaccepted contribution claims:
   those belong in `research-workspaces/<id>/`.

2. **No link may point to the workspaces tree.** A KB page that links to
   `../research-workspaces/...` is a pollution bug. Export packs are
   created *from* the KB into a workspace, never the other way around.

3. **Every paper card must declare `type: paper` in frontmatter** and must
   satisfy the `PaperFrontmatter` schema in `lgrlw.schemas`.

4. **Only these statuses are allowed on KB pages:**
   `published`, `accepted`, `preprint`.
   Workspace-only statuses (`drafting`, `under_review`, `rejected`, &hellip;)
   are forbidden here.

5. **Export packs under `06_Exports/` are immutable.** Do not edit a pack
   after it was generated; regenerate a new one instead. The manifest
   records a SHA-256 for every file and `lgrlw lint` will notice tampering.

---

## 2. What may enter this KB

- Published papers (peer-reviewed venues).
- Accepted-but-not-yet-published papers.
- Public preprints the maintainer has explicitly approved.
- Surveys, benchmark papers, dataset papers, method papers.
- The maintainer's *own* accepted papers &mdash; but only via
  `lgrlw promote`, never by manual copy.

## 3. What may **not** enter this KB

- Any current unpublished idea of the maintainer.
- Draft methods, method sketches, design notes.
- Experiment logs, reproduction numbers, ablation results.
- Manuscript drafts, rebuttal drafts.
- Unaccepted contribution claims (&ldquo;my method achieves X&rdquo; without
  an accepted paper to cite).
- Reviewer identities or private correspondence.

---

## 4. Allowed operations

An agent may:

- Add a new paper card with `lgrlw add-literature --manual` (v0.2: also
  `--arxiv` / `--doi` / `--ss` with network fetchers).
- Curate `03_Field_Structure/` (Overview, Problem Evolution, Method
  Taxonomy, Timeline, Dataset/Benchmark/Metric maps) **using only
  information already present in this KB**.
- Curate `05_Evidence/` (Evidence Map, Contradictions, Limitations Map,
  Open Problems) by linking claims to specific paper cards already in
  `02_Literature/Papers/`.
- Append entries to `00_System/log.md` that record provenance of what was
  added or updated and when.

An agent must **not**:

- Write anything whose truth depends on unpublished experiments.
- Link to, cite, or quote content from `research-workspaces/`.
- Modify an existing export pack under `06_Exports/`.
- Manually drop a paper card for the maintainer's own in-flight work.
  That path goes through `lgrlw promote` and only after acceptance.

---

## 5. Mental model

> The KB is the *state of the field*, not the *story that supports the
> current paper*. When the two diverge, the KB wins. The current paper is
> what you are trying to insert into the field, not what defines the field.

If an edit feels like it is *arguing for* something unpublished, stop. It
belongs in a workspace.
