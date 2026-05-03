# Promotion protocol (v0.2)

> **Status.** Implemented in v0.2 as `lgrlw promote`. Every precondition
> in this document is enforced by the command; failure aborts before any
> KB write. Manual workarounds remain discouraged; use `lgrlw promote`.

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

| Artefact | Location | Authoring |
|---|---|---|
| Paper card with `source: promoted` | `literature-kb/02_Literature/Papers/<id>.md` | Auto-generated from `paper_status.md` frontmatter. |
| BibTeX entry | `literature-kb/01_Raw/bibtex/<id>.bib` | Auto-generated `@inproceedings` (if `venue` is set) or `@misc` (otherwise). Replace it manually if you have a curated version. |
| Metadata snapshot | `literature-kb/01_Raw/metadata/<id>.json` | Auto-generated mirror of the paper card frontmatter. |
| Taxonomy / evidence updates | per `06_Promotion/add_back_to_kb_plan.md` | **Manual follow-up.** `lgrlw promote` validates the plan exists with at least one `- ` bullet but does *not* apply edits to `03_Field_Structure/` or `05_Evidence/` automatically. The command prints a reminder. |
| Log line | `literature-kb/00_System/log.md` | Auto-appended (`promote workspace=… id=…`). |

The workspace itself is **not** deleted. It becomes a historical record.

If any single write fails mid-flight, the artefacts already written by
this run are unlinked before the error propagates, so a partial KB state
never survives a failed promotion.

## What is *not* promoted

- Manuscript draft (`04_Writing/*`).
- Experimental logs and raw numbers (`03_Experiments/*`).
- Rebuttal / review correspondence (`05_Review/*`).
- Ideation history, assumptions, design-choice notes.

These live in the workspace forever. They do not become literature even
after the paper is accepted; *the accepted paper* becomes literature,
which is a summary already.

## Pre-flight: filling in the workspace

Before running `lgrlw promote`:

1. Update `00_Project/paper_status.md` frontmatter so `status: accepted`
   and `final_title` / `final_authors` / `venue` / `year` plus one of
   `doi` / `arxiv_id` are present.
2. In `06_Promotion/final_metadata.md`, paste the camera-ready URL or
   PDF path and (optionally) the BibTeX entry the venue published.
3. In `06_Promotion/promotion_checklist.md`, change every `- [ ]` to
   `- [x]` once you have evidence for that line.
4. In `06_Promotion/add_back_to_kb_plan.md`, list each intended
   `03_Field_Structure/` / `05_Evidence/` edit as a `- ` bullet. These
   are not auto-applied; they are a TODO list you commit by hand after
   `lgrlw promote` succeeds.

Then run `lgrlw promote <workspace-id>`. The CLI prints the four
written artefact paths plus a reminder to apply the add-back plan.
