# Boundary rules

The single most important invariant of Research-Wiki is **the boundary
between the KB and the workspaces**. This document states the rules in
full, including edge cases.

## The rules in one paragraph

The KB contains *public literature*, and nothing else. Workspaces contain
*your private research process*, and may *read* the KB via dated export
packs. The only legal path from a workspace back into the KB is
`lgrlw promote` after acceptance.

## What may enter the KB

| Entry path | When |
|---|---|
| `lgrlw add-literature --manual` | Any published / accepted / approved-preprint paper. |
| `lgrlw add-literature --arxiv/--doi/--ss` (v0.2) | Same; networked fetch. |
| Hand-editing `03_Field_Structure/` or `05_Evidence/` | As long as every reference resolves to a paper card already in the KB. |
| `lgrlw promote <workspace>` (v0.2) | Only if `paper_status = accepted`. |

## What must **never** enter the KB

- Unpublished ideas of the maintainer.
- Draft methods, method sketches, pseudocode for a current project.
- Experiment logs, reproduction numbers, ablation results.
- Manuscript drafts, rebuttal drafts.
- Reviewer identities, private correspondence.
- Speculative limitations you have not seen stated in the literature.
- Contribution claims not yet supported by an accepted paper.

## Enforced by `lgrlw lint`

| Rule | What it forbids |
|---|---|
| `boundary.workspace_reference_in_kb` | Any KB markdown referencing `research-workspaces/` (except `00_System/*.md`, which are KB tooling docs). |
| `boundary.workspace_frontmatter_in_kb` | KB frontmatter `type:` value in `{workspace_paper, idea, experiment, rebuttal}`. |
| `boundary.workspace_status_in_kb` | KB frontmatter `status:` value drawn from WorkspaceStatus but not PaperStatus (e.g. `drafting`, `under_review`, `rejected`). |

See [`templates/literature-kb/00_System/verification_policy.md`](../templates/literature-kb/00_System/verification_policy.md)
for the canonical rule list; the lint module lives at
[`src/lgrlw/lint/boundary.py`](../src/lgrlw/lint/boundary.py).

## Edge cases

### Reviewer-suggested literature

Reviewers often point to papers you missed. Those papers legitimately
belong in the KB once you agree with the relevance. Add them through
`lgrlw add-literature` (not by copy-pasting from the review). The
reviewer text itself never enters the KB.

### Public preprints

Preprints approved by the maintainer may enter the KB with
`status: preprint`. Use this cautiously: a preprint you once read and
forgot may not deserve a paper card.

### Your own accepted paper

Your own accepted paper is literature. Put it in the KB &mdash; but only
after acceptance, and only via `lgrlw promote`. Manual copy-paste is
forbidden because it skips the validation that there is a final venue,
final author list, and camera-ready artefact.

### An accepted paper that later gets retracted

Retractions are rare but real. Append a line to
`05_Evidence/Contradictions.md` (or a dedicated `Retractions.md` once
needed) noting the retraction notice (which is itself public
literature). Do not delete the paper card silently.

## Mental model

> The KB is the *state of the field*, not the *story that supports the
> current paper*. The two will be in tension. The KB wins.
