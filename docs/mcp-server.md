# MCP server

Research-Wiki v0.3 ships an optional Model Context Protocol server so agent clients can drive `lgrlw` through typed tools instead of shell commands.

Install the optional dependency:

```bash
pip install "lgrlw[mcp]"
```

Start the stdio server:

```bash
lgrlw mcp serve --root ./my-project
```

For a monorepo, pass the umbrella root:

```bash
lgrlw mcp serve --root ./research-repo
```

## Tools

The server exposes tools that mirror the CLI backend. Every tool returns a JSON-compatible object with `ok` and path/result fields.

| Tool | Purpose |
|---|---|
| `init_project` | Create a single-direction project or a monorepo umbrella (`monorepo=true`). |
| `add_direction` | Add `directions/<slug>/` to an existing monorepo umbrella. |
| `new_workspace` | Create a paper/idea workspace under the selected project. |
| `add_literature` | Add a manual paper entry or explicitly fetch via DOI/arXiv/OpenAlex/Semantic Scholar. Optionally attaches a local PDF via `pdf_path`. |
| `export_pack` | Build an immutable KB snapshot for a workspace. |
| `promote` | Promote an accepted workspace paper into the KB. |
| `lint` | Run structure/schema/boundary/manifest lint. |

### Root and direction selection

Most tools accept:

- `root`: project root or monorepo umbrella root. If omitted, the server's `--root` value is used; if that is also omitted, the process cwd is auto-detected.
- `direction`: monorepo direction slug. Required when `root` is a monorepo umbrella unless the server can infer the child from cwd.

### Network policy

The MCP server does not perform hidden network calls. `add_literature` is offline when `mode="manual"`. It performs network I/O only when the caller explicitly chooses one of:

- `mode="doi"`
- `mode="arxiv"`
- `mode="openalex"`
- `mode="ss"`

Those modes use the same fetchers and environment variables as the CLI: `CROSSREF_MAILTO`, `OPENALEX_EMAIL`, and `S2_API_KEY`.

`add_literature` also accepts two optional PDF arguments:

- `pdf_path` (string, local filesystem path): copy the file verbatim to `literature-kb/01_Raw/pdf/<paper_id>.pdf`. Path is resolved locally; **no network fetch is performed** even if the value looks like a URL — URLs are rejected.
- `force_pdf` (bool): replace an existing archived PDF. Required even in combination with `force`.

When `pdf_path` is supplied, the tool result includes `pdf_archive` with the archived path; otherwise `pdf_archive` is `null`.

## Resources

The server exposes read-only resources for the default root passed to `lgrlw mcp serve`:

| URI | MIME type | Contents |
|---|---|---|
| `lgrlw://project/summary` | `application/json` | Subproject roots and counts of paper cards/workspaces. |
| `lgrlw://kb/papers` | `application/json` | Paper-card frontmatter records and paths. |
| `lgrlw://workspaces` | `application/json` | Workspace paths and `paper_status.md` frontmatter when present. |

For a monorepo umbrella, resources aggregate across every registered direction.

## Example client configuration

For clients that launch stdio servers with a command/args pair:

```json
{
  "command": "python",
  "args": ["-m", "lgrlw", "mcp", "serve", "--root", "/path/to/research-repo"]
}
```

Use an absolute path for `--root` in long-lived agent configurations.
