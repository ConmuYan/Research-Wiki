# PAPER_AGENTS.md &mdash; workspace constitution (paper)

> LLM agents operating inside this workspace **must read this file before
> any write**. End-users: this is the rulebook. Disagreement is fine;
> violation is not.

---

## 0. Identity

This directory is a **Research Workspace** of kind `paper`. It hosts one
research project from idea formation through manuscript submission and,
eventually, acceptance. It is *not* the KB. Nothing here is public
literature.

The governing protocol is *Literature-Grounded Research Lifecycle Wiki*
(LGRLW); the CLI is `lgrlw`. See the repo-root `AGENTS.md` and the KB's
`KB_AGENTS.md` for the adjacent constitutions.

---

## 1. Non-negotiable invariants

1. **This workspace may read the KB; it must never write into the KB.**
   The only legal path from a workspace back to the KB is
   `lgrlw promote <workspace>`, which fires only when
   `paper_status = accepted`.

2. **All grounding of KB content goes through `01_KB_Exports/`.** You
   reference papers and field-structure via an export pack snapshot, not
   by reaching into `../../literature-kb/`. This keeps the manuscript
   reproducible from a dated KB state.

3. **`paper_status.md` frontmatter is authoritative.** It carries the
   lifecycle status (`drafting` &rarr; `experimenting` &rarr; `writing`
   &rarr; `submitted` &rarr; `under_review` &rarr; `major_revision` /
   `minor_revision` &rarr; `accepted` / `rejected` / `withdrawn`).
   `lgrlw lint` validates its schema.

4. **No fabricated citations.** Every citation in `04_Writing/` must
   resolve to a paper card inside `01_KB_Exports/<pack>/02_Literature/Papers/`.

5. **No premature promotion.** Do not copy workspace content into the KB
   "just so it's easier to reference". The promotion ceremony
   (`lgrlw promote`, v0.2) is the only legal door.

---

## 2. Allowed operations

- Brainstorm, hypothesise, design methods, run experiments, analyse
  results, draft and revise the paper.
- Append to `workspace_log.md`-style notes (in the relevant subfolder)
  whenever a decision is made.
- Regenerate `01_KB_Exports/` packs as the KB advances, preferring fresh
  packs over mutating old ones.
- Separate *literature evidence* (traceable to `01_KB_Exports/`) from *my
  hypothesis* (created here and unvalidated) in every document.

## 3. Forbidden operations

- Writing into `../../literature-kb/` from here.
- Copy-pasting paragraphs from `01_KB_Exports/` into the KB.
- Putting unaccepted contribution claims inside the KB.
- Registering a fabricated paper card in `02_Literature/Papers/` to
  support a draft claim.

---

## 4. Directory map

| Path | Role |
|---|---|
| `00_Project/` | Status, research problem, finalized idea, method summary, contribution claims. |
| `01_KB_Exports/` | Dated, immutable snapshots of the KB used for grounding. |
| `02_Idea_and_Method/` | Idea history, assumptions, design choices, novelty analysis. |
| `03_Experiments/` | Plan, baselines, metrics, results, analysis. |
| `04_Writing/` | Narrative, intro, related work, method, experiments, full draft. |
| `05_Review/` | Submitted version, reviews, rebuttal, revision plan. |
| `06_Promotion/` | Acceptance record, final metadata, KB promotion checklist. |

---

## 5. Writing discipline

When drafting under `04_Writing/`, tag every paragraph mentally (or in a
hidden comment) with one of:

- **LIT** &mdash; a claim about the existing literature. Must cite a paper
  in `01_KB_Exports/<pack>/02_Literature/Papers/`.
- **OUR** &mdash; a claim about *our* method, experiments, results, or
  interpretation. Must be traceable to `02_Idea_and_Method/` or
  `03_Experiments/`.

If a paragraph mixes both, split it. Most "voice drift" in academic
writing comes from merged LIT/OUR sentences.
