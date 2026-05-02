# IDEA_AGENTS.md &mdash; workspace constitution (idea)

> LLM agents operating inside this workspace must read this file before any
> write. This is the rulebook.

---

## 0. Identity

This directory is a **Research Workspace** of kind `idea`. It is an
isolated sandbox for pre-method exploration: reading gaps, wild
hypotheses, design-space sketches. Nothing here is committed to a paper
track yet.

Ideas that mature into a concrete research programme should be promoted
into a `paper` workspace via `lgrlw new-workspace <paper_id> --kind paper`
and the relevant content copied over; the idea sandbox then remains as a
historical record.

---

## 1. Non-negotiable invariants

1. **The KB is read-only from here.** Exactly the same rule as for paper
   workspaces: no writes into `../../literature-kb/`.
2. **No promotion to KB from an idea sandbox.** Only accepted papers
   promote. An idea, however promising, cannot leak into KB.
3. **Clearly label your hypotheses as hypotheses.** Anything that is not
   directly sourced from `00_Context/kb_exports/` should be tagged with
   "**HYPOTHESIS:**" or "**MY CLAIM:**" prefix in prose. This keeps
   downstream agents (and future-you) from treating it as fact.

---

## 2. Directory map

| Path | Role |
|---|---|
| `00_Context/` | KB exports and distilled gaps/taxonomy excerpts. |
| `01_Idea/` | Idea notes, hypotheses, design-space enumeration, novelty risk. |
| `02_Method/` | Method sketch, assumptions, expected advantages. |
| `workspace_log.md` | Dated running log of what was tried / concluded. |

---

## 3. Graduation to a paper workspace

When the idea has:

- a concrete method sketch (`02_Method/method_sketch.md`);
- at least one falsifiable hypothesis (`01_Idea/hypotheses.md`);
- identified closest prior work (`01_Idea/novelty_risk.md`);

then run:

```
lgrlw new-workspace <new_paper_id> --kind paper --title "..."
```

and copy the relevant notes into the new workspace. Leave this sandbox
intact for provenance.
