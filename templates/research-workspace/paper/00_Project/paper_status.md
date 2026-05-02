---
type: workspace_paper
id: paper_template
kind: paper
title: placeholder title (replaced by `lgrlw new-workspace`)
status: drafting
created_on: 1970-01-01
---

# paper_status.md

This file carries the **authoritative lifecycle status** of the workspace.
`lgrlw lint` validates its frontmatter against `WorkspacePaperFrontmatter`.

## Status ladder

| Status | Meaning |
|---|---|
| `drafting` | Idea formation (S3). |
| `experimenting` | Running experiments (S5). |
| `writing` | Drafting the manuscript (S6). |
| `submitted` | Sent to a venue; awaiting review (S7). |
| `under_review` | Reviews in progress. |
| `major_revision` | Major revision requested; back to S5 or S6. |
| `minor_revision` | Minor revision requested. |
| `accepted` | Accepted. **Only this status unlocks `lgrlw promote`.** |
| `rejected` | Rejected; decide whether to withdraw or resubmit. |
| `withdrawn` | Explicitly withdrawn by the author. |

## Promotion fields

Once `status: accepted`, fill in the final-metadata fields in frontmatter
before running `lgrlw promote` (v0.2):

- `final_title`
- `final_authors` (list, camera-ready order)
- `venue`, `year`
- `doi` and/or `arxiv_id`

## Notes

<!-- Running notes on the status transitions. Dated. -->
