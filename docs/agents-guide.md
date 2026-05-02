# Agents guide

This document is for LLM agents (Claude Code, Cursor, Windsurf, Aider,
Codex, and successors) operating on *user research projects* generated
by `lgrlw init`. The repo-root [`AGENTS.md`](../AGENTS.md) governs the
tool itself.

## The three constitutions

Every Research-Wiki project contains three `AGENTS.md`-shaped files. An
agent operating inside a given directory **must** read the nearest one
before any write:

| File | Governs |
|---|---|
| `literature-kb/00_System/KB_AGENTS.md` | All work inside the KB. |
| `research-workspaces/<id>/00_Project/PAPER_AGENTS.md` | Paper workspaces. |
| `research-workspaces/<id>/IDEA_AGENTS.md` | Idea-sandbox workspaces. |

They are consistent with each other; reading one does not excuse you
from the boundary rules expressed in the others.

## How to do each task

### "Add paper X to the KB"

```
lgrlw add-literature --manual \
  --title "..." --authors "..." --year YYYY \
  [--venue "..."] [--doi ...] [--arxiv ...] [--url ...] \
  [--status published|accepted|preprint] \
  [--tags "a,b,c"]
```

Never hand-write paper cards under `02_Literature/Papers/` if the
command is available. The command generates the correct id, frontmatter,
metadata snapshot, and log entry in one atomic step.

### "Start working on a new idea / paper"

```
lgrlw new-workspace <id> --kind paper --title "..."
# or
lgrlw new-workspace <id> --kind idea --title "..."
```

Then populate the generated workspace. Do not create workspaces by
copying old ones manually; the generated `paper_status.md` frontmatter
is the authoritative lifecycle anchor.

### "Export KB state for writing"

```
lgrlw export-pack <workspace-id>
```

The pack is dated; if you rerun the command on a later day, a new pack
is created side by side with the older one. While writing, cite
*through* the pack (e.g.
`../01_KB_Exports/paper_001_2026-05-02/02_Literature/Papers/<id>.md`),
not through the live KB. This keeps citations reproducible.

### "Verify the project before commit"

```
lgrlw lint
```

Must pass. Never commit with outstanding errors. Warnings (`manifest.file_extra`)
are advisory; resolve or leave a short note.

## How to *not* violate the boundary

- Do not open `literature-kb/` in a paper workspace's editor and type a
  sentence of the form "our method..." into a paper card.
- Do not paste a reviewer-facing argument into `05_Evidence/`.
- Do not add a `status: under_review` frontmatter to anything in the KB.
- Do not link any KB markdown to `../research-workspaces/`.
- Do not edit any file inside `06_Exports/<pack>/` after creation.

If a task seems to require breaking one of these, stop and open an issue
(or ask the human).

## Tone and provenance

- Keep prose factual. In the KB, cite the paper; in the workspace,
  distinguish "LIT" (literature) from "OUR" (your work).
- Prefer terse, structured content (tables, bullet lists with links) over
  flowing prose when the content will be machine-read again.
- Log material changes in the nearest `log.md` or `workspace_log.md`.
