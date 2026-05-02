# Protocol: adding a paper to the KB

This file specifies the single legal way to add a literature entry.
`lgrlw lint` enforces the resulting shape.

## v0.1 &mdash; manual entry

```bash
lgrlw add-literature --manual \
  --title  "<paper title>" \
  --authors "<First Last, Another Name, ...>" \
  --year    <yyyy> \
  --venue   "<venue or 'arXiv preprint'>" \
  [--doi     <DOI>] \
  [--arxiv   <arXiv id>] \
  [--url     <canonical URL>] \
  [--status  published|accepted|preprint] \
  [--tags    "tag1,tag2"]
```

Outputs:

- A paper card at `02_Literature/Papers/<id>.md` with YAML frontmatter
  and a body scaffold (`Summary`, `Claims`, `Methods`, `Results`, `Related
  Work`, `Notes`).
- A metadata snapshot at `01_Raw/metadata/<id>.json`.
- One line appended to `00_System/log.md`.

`<id>` is generated as
`<last-name-of-first-author>-<year>-<slugified-title-fragment>` unless
you supply `--id` explicitly.

## v0.2 &mdash; networked fetchers (not yet implemented)

```bash
lgrlw add-literature --arxiv <arxiv-id>
lgrlw add-literature --doi   <doi>
lgrlw add-literature --ss    <semantic-scholar-id>
```

Behaviour and rate-limit policy will be specified in
`docs/add-literature-protocol.md` when v0.2 lands.

## What a paper card must contain

- A valid `PaperFrontmatter` (see `src/lgrlw/schemas.py`), with
  `type: paper`.
- At minimum: `title`, `authors`, `year`, `added_on`, `source`, `status`.
- Optional but strongly encouraged: `doi`, `arxiv_id`, `venue`, `tags`.

## What a paper card must **not** contain

- Links to `research-workspaces/`.
- Your own reproduction numbers, ablations, or method claims (those belong
  in a workspace).
- Frontmatter with workspace-only `type` (`workspace_paper`, `idea`,
  `experiment`, `rebuttal`) or workspace-only `status`.

## When in doubt

If you are about to write a sentence like &ldquo;in our preliminary
experiments&rdquo; or &ldquo;we believe this method would&hellip;&rdquo;, you
are in the wrong directory. Stop and move the content to a workspace.
