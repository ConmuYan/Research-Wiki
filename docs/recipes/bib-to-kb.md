# Recipe: BibTeX to KB with agents

This recipe describes how a Research-Wiki user can drive an MCP-capable
agent (Claude Code, Cursor, Windsurf, ...) to turn a BibTeX file plus an
optional local directory of PDFs into canonical KB paper cards, without
the agent touching Research-Wiki files directly.

It is a **reference workflow**, not a shipped command. The intent is to
describe how the v0.3 MCP surface already suffices to express the
workflow, which deterministic pieces will be promoted into core
commands in later versions (`lgrlw import-bib` in v0.4,
`lgrlw attach-pdf` in v0.4.x, MinerU and networked PDF fetchers in
v0.5+), and where the safety boundaries sit.

## Scope

The recipe covers:

- parsing a `.bib` file and deciding the best metadata source per entry
  (`arxiv` > `doi` > `manual`);
- creating paper cards through the MCP `add_literature` tool so the
  Research-Wiki schema, slug, and audit log stay canonical;
- attaching local PDFs through the new `--pdf` option added in v0.3.1;
- running `lint` through MCP after every batch.

It does **not** cover:

- downloading PDFs from the network (v0.5.x, behind explicit
  `--allow-network-pdf`);
- converting PDFs to Markdown (v0.5 MinerU plugin);
- filling the six paper-card sections with LLM-generated drafts — an
  agent may do that in the body of the card, but it must never touch
  the YAML frontmatter and must flag the card as needing human review.

## Metadata source priority

For each BibTeX entry, the agent should pick exactly one metadata
source, in order of preference:

1. `arxiv` — when the entry carries an arXiv id (e.g. `eprint =
   {2310.11511}` or `archiveprefix = {arXiv}`);
2. `doi` — when the entry carries a DOI;
3. `openalex` / `ss` — when the bib entry carries an OpenAlex Work id or
   a Semantic Scholar paper id;
4. `manual` — fallback; the agent must ensure `title`, `authors`, and
   `year` are all present.

The agent calls the MCP `add_literature` tool with exactly one of
`mode="arxiv" | "doi" | "openalex" | "ss" | "manual"`. This mirrors the
CLI contract: no hidden fallback, one network source per call.

## PDF source priority

Independently from the metadata source, each paper may have its PDF
resolved from any of:

1. a user-provided explicit local path (`pdf_path` tool argument);
2. a user-provided `--pdf-dir` scanned by the agent;
3. a staging directory at `literature-kb/01_Raw/pdf/_incoming/` (v0.4.x);
4. networked download from arXiv or an Open-Access URL (v0.5.x,
   requires explicit `--allow-network-pdf`);
5. no PDF — the card is created metadata-only and the agent records
   `pdf_status: missing` in its own import manifest.

Today (v0.3.1) only options 1 and 5 are supported by the MCP tool. The
agent is free to implement 2 itself by iterating entries and resolving
a local filename match before each `add_literature` call.

## MCP tools used

- `add_literature(mode, ..., pdf_path=, force_pdf=, root=, direction=)`
  — creates the paper card, the metadata JSON, the log entry, and
  (optionally) the archived PDF;
- `lint(root=, direction=)` — runs every lint family after the batch.

Read-only resources that are useful to the agent before it starts:

- `lgrlw://kb/papers` — list existing papers so duplicates are skipped;
- `lgrlw://project/summary` — detect monorepo / direction layout;
- `lgrlw://workspaces` — only relevant if a workspace triggered the
  import.

## Recommended agent workflow

1. **Parse.** Read `.bib`, normalise each entry to an intermediate
   dictionary with `cite_key`, `title`, `authors`, `year`, optional
   `doi`, `arxiv_id`, `openalex_id`, `ss_id`, `venue`, `tags`, and a
   chosen `mode`.
2. **Plan.** Read `lgrlw://kb/papers`, drop entries whose identifiers
   already exist in the KB. Summarise the plan to the user: N new, M
   skipped, K ambiguous. Ask for confirmation before any write.
3. **Match PDFs.** For each planned entry, look for a local PDF in the
   user-specified directory using these filename heuristics in order:
   1. filename contains the arXiv id;
   2. filename contains the BibTeX cite key;
   3. fuzzy title match above a 0.85 normalised-similarity threshold.
   Record the resolved path (or `null`) per entry.
4. **Create cards.** For each entry call
   `add_literature(mode=..., ..., pdf_path=<resolved or null>, root=,
   direction=)`. Record the returned `paper_id`, `paper_card`,
   `metadata_json`, and `pdf_archive` in a local import manifest.
5. **Lint.** Call `lint(root=, direction=)` once. If any `error`
   severity finding appears, surface it and stop; do not continue to
   body-section drafting.
6. *(Optional, agent-only)* Draft the six body sections of each paper
   card — Summary / Claims / Methods / Results / Related Work / Notes —
   by reading the metadata JSON and (when available) the source PDF or
   MinerU output. Never touch the YAML frontmatter. Mark every card as
   machine-assisted in the agent's own import manifest.

## Example call (Claude Code)

```text
Use the research-wiki MCP to import refs.bib into the `rag-evaluation`
direction. For every entry:
- pick metadata mode arxiv > doi > manual;
- attach a PDF from ./papers/ if the filename matches the arxiv id or
  cite key;
- skip papers already in the KB;
- after the batch, run lint and report all findings.
Do not edit YAML frontmatter. Do not download PDFs over the network.
```

The agent is expected to respect that instruction, use the MCP tools
described above, and return a concise summary plus the import manifest.

## What lives where today

| Step | Today (v0.3.1) | Later |
| --- | --- | --- |
| BibTeX parsing | agent | `lgrlw import-bib` (v0.4) |
| Duplicate detection | agent reads `lgrlw://kb/papers` | `lgrlw import-bib` (v0.4) |
| Local PDF attach | MCP `add_literature` `pdf_path` | `lgrlw attach-pdf` (v0.4.x) |
| Inbox / fuzzy match | agent | `lgrlw attach-pdf --scan-incoming` (v0.4.x) |
| Networked PDF fetch | not supported | v0.5.x, explicit opt-in |
| PDF → Markdown | not supported | `lgrlw[mineru]` (v0.5) |
| Section drafting | agent only | remains agent territory |
| Safe section write-back | agent `Edit` tool with strict rules | future `update_paper_sections` MCP tool |

## Safety checklist for agents

- Never create paper cards by hand. Always call `add_literature`.
- Never modify YAML frontmatter on existing paper cards.
- Never commit PDFs unless the user explicitly authorises it; treat
  `literature-kb/01_Raw/pdf/` as local-only by default.
- Never download PDFs unless the user has opted into the v0.5.x
  network-download surface.
- Always run `lint` at the end of a batch, and fail the batch on any
  `error` severity finding.
- Always surface skipped / failed entries; do not silently drop them.
