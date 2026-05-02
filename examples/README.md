# examples/

A small, hand-seeded Research-Wiki project that lives inside this
repository so the README, tests, and new users can all point at the
same concrete example.

## `demo_direction/`

Simulated research direction: **retrieval-augmented generation (RAG)**.

Contents:

- `.lgrlw.toml` &mdash; project config (direction =
  `retrieval-augmented-generation`).
- `literature-kb/` &mdash; three real literature entries added via
  `lgrlw add-literature --manual`: Lewis et al. 2020 (RAG),
  Karpukhin et al. 2020 (DPR), Asai et al. 2023 (Self-RAG). These are
  *metadata-only* records; we do not ship PDFs.
- `literature-kb/03_Field_Structure/Overview.md` &mdash; hand-curated
  one-page overview that links to the three paper cards, illustrating
  what field-structure curation looks like.
- `research-workspaces/paper_001/` &mdash; a paper workspace, created
  via `lgrlw new-workspace`, with a working title that would plausibly
  build on the three KB papers.
- `literature-kb/06_Exports/paper_001_<date>/` and its mirror under
  `research-workspaces/paper_001/01_KB_Exports/` &mdash; a dated export
  pack produced by `lgrlw export-pack`.

## Try it

From the repository root (after `pip install -e ".[dev]"`):

```bash
lgrlw lint examples/demo_direction
# -> lint all checks passed
```

To rebuild the export pack (for instance after adding another paper
with `lgrlw add-literature --manual`), delete the existing pack first
(packs are immutable) and rerun:

```bash
lgrlw export-pack paper_001 --root examples/demo_direction
```

## Intentionally *not* included

- No PDFs, datasets, or model weights. The project is a protocol, not a
  corpus; examples cite upstream sources by URL / DOI / arXiv id.
- No manuscript, no experimental results, no contribution claims. A
  workspace full of drafts is not the right showcase for a template;
  the `paper_001/04_Writing/`, `03_Experiments/`, `05_Review/`,
  `06_Promotion/` subtrees contain only the stub files emitted by
  `lgrlw new-workspace`.
