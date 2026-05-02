# Promotion protocol (v0.2, specified now)

> **Status.** The promotion *ceremony* is specified here and in
> `templates/research-workspace/paper/06_Promotion/`. The *command*
> `lgrlw promote` ships in v0.2. Until then, no manual workaround is
> endorsed; the boundary lint rules still apply.

Promotion is the only legal path from a workspace back into the KB. It
fires exactly once per paper, when the paper is accepted.

## Preconditions

All of these must be true before `lgrlw promote <workspace-id>` is
allowed to proceed:

1. `research-workspaces/<id>/00_Project/paper_status.md` has
   `status: accepted` in frontmatter.
2. The same frontmatter has non-null `final_title`, `final_authors`,
   `venue`, `year`.
3. At least one of `doi` or `arxiv_id` is present.
4. A camera-ready PDF or public-version URL is referenced from
   `06_Promotion/final_metadata.md`.
5. `06_Promotion/promotion_checklist.md` has every box ticked.

If any precondition fails, `lgrlw promote` exits non-zero and prints the
offending item; nothing is written.

## Effects

On success, promotion is *atomic* (all-or-nothing) and produces:

| Artefact | Location |
|---|---|
| Paper card with `source: promoted` | `literature-kb/02_Literature/Papers/<id>.md` |
| BibTeX entry (v0.2) | `literature-kb/01_Raw/bibtex/<id>.bib` |
| Metadata snapshot | `literature-kb/01_Raw/metadata/<id>.json` |
| Taxonomy / evidence updates | per `06_Promotion/add_back_to_kb_plan.md` |
| Log line | `literature-kb/00_System/log.md` |

The workspace itself is **not** deleted. It becomes a historical record.

## What is *not* promoted

- Manuscript draft (`04_Writing/*`).
- Experimental logs and raw numbers (`03_Experiments/*`).
- Rebuttal / review correspondence (`05_Review/*`).
- Ideation history, assumptions, design-choice notes.

These live in the workspace forever. They do not become literature even
after the paper is accepted; *the accepted paper* becomes literature,
which is a summary already.

## What *may* be manually promoted (v0.1 workaround)

If you urgently need to register your own accepted paper in the KB
before v0.2 ships, you can:

1. `lgrlw add-literature --manual --status accepted --title ... --venue
   ... --year ... --doi ... --arxiv ...`.
2. Immediately append a note to `literature-kb/00_System/log.md` marking
   the entry as `manually promoted (promote-v0.2 unavailable)`.

This is a deliberate, auditable escape hatch, not a normal flow.
`lgrlw lint` will still pass because manual entries are legitimate
literature entries; but you carry the responsibility of filling in the
field-structure / evidence-map updates that `lgrlw promote` would have
produced automatically.
