"""Tests for the optional Research-Wiki MCP server."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typer.testing import CliRunner

from lgrlw.cli import app
from lgrlw.fs import read_frontmatter, write_frontmatter


@pytest.mark.asyncio
async def test_mcp_stdio_exposes_tools_and_resources(
    tmp_path: Path,
    runner: CliRunner,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    default_root = tmp_path / "default_repo"
    init_result = runner.invoke(
        app, ["init", str(default_root), "--direction", "alpha", "--monorepo"]
    )
    assert init_result.exit_code == 0, init_result.output

    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo_root / "src") + os.pathsep + env.get("PYTHONPATH", "")
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "lgrlw", "mcp", "serve", "--root", str(default_root)],
        cwd=repo_root,
        env=env,
    )

    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()

        tools = await session.list_tools()
        tool_names = {tool.name for tool in tools.tools}
        assert {
            "init_project",
            "add_direction",
            "new_workspace",
            "add_literature",
            "export_pack",
            "promote",
            "lint",
            "import_bib",
            "attach_pdf",
        }.issubset(tool_names)

        created_root = tmp_path / "created_by_mcp"
        assert_ok(
            await session.call_tool(
                "init_project",
                {"root": str(created_root), "direction": "gamma"},
            )
        )
        assert (created_root / ".lgrlw.toml").is_file()

        assert_ok(await session.call_tool("add_direction", {"direction": "beta"}))
        beta = default_root / "directions" / "beta"
        assert (beta / ".lgrlw.toml").is_file()

        assert_ok(
            await session.call_tool(
                "new_workspace",
                {"name": "paper_001", "title": "MCP Paper", "direction": "beta"},
            )
        )
        assert (beta / "research-workspaces" / "paper_001").is_dir()

        assert_ok(
            await session.call_tool(
                "add_literature",
                {
                    "mode": "manual",
                    "title": "Tool-Using Agents",
                    "authors": "Ada Lovelace",
                    "year": 2024,
                    "paper_id": "lovelace-2024-tool-agents",
                    "direction": "beta",
                },
            )
        )
        assert (
            beta / "literature-kb" / "02_Literature" / "Papers" / "lovelace-2024-tool-agents.md"
        ).is_file()

        assert_ok(
            await session.call_tool(
                "export_pack",
                {"workspace": "paper_001", "direction": "beta"},
            )
        )
        assert any((beta / "literature-kb" / "06_Exports").iterdir())

        _prepare_accepted_workspace(beta / "research-workspaces" / "paper_001")
        assert_ok(
            await session.call_tool(
                "promote",
                {
                    "workspace": "paper_001",
                    "paper_id": "lovelace-2025-promoted-paper",
                    "direction": "beta",
                },
            )
        )
        assert (
            beta / "literature-kb" / "02_Literature" / "Papers" / "lovelace-2025-promoted-paper.md"
        ).is_file()

        bib_file = tmp_path / "mcp_refs.bib"
        bib_file.write_text(
            "@article{bengio2013rep,\n"
            "  author = {Yoshua Bengio},\n"
            "  title  = {Representation Learning: A Review and New Perspectives},\n"
            "  year   = {2013},\n"
            "  eprint = {1206.5538},\n"
            "  archiveprefix = {arXiv},\n"
            "}\n",
            encoding="utf-8",
        )
        import_result = await session.call_tool(
            "import_bib",
            {
                "bib_path": str(bib_file),
                "direction": "beta",
                "on_duplicate": "skip",
            },
        )
        assert_ok(import_result)
        import_payload = json.loads(import_result.content[0].text)
        assert import_payload["counts"]["imported"] == 1
        assert import_payload["manifest_path"]
        expected_bengio = (
            beta
            / "literature-kb"
            / "02_Literature"
            / "Papers"
            / "bengio-2013-representation-learning-a-review-and-new-perspec.md"
        )
        assert expected_bengio.is_file()

        # attach_pdf: explicit mode + scan mode.
        bengio_pdf = tmp_path / "bengio.pdf"
        bengio_pdf.write_bytes(b"%PDF-1.4\nbengio explicit\n")
        attach_explicit = await session.call_tool(
            "attach_pdf",
            {
                "paper_id": "bengio-2013-representation-learning-a-review-and-new-perspec",
                "pdf_path": str(bengio_pdf),
                "direction": "beta",
            },
        )
        assert_ok(attach_explicit)
        attach_explicit_payload = json.loads(attach_explicit.content[0].text)
        assert attach_explicit_payload["mode"] == "explicit"
        assert attach_explicit_payload["outcomes"][0]["status"] == "archived"
        assert (
            beta
            / "literature-kb"
            / "01_Raw"
            / "pdf"
            / "bengio-2013-representation-learning-a-review-and-new-perspec.pdf"
        ).is_file()

        inbox = beta / "literature-kb" / "01_Raw" / "pdf" / "_incoming"
        inbox.mkdir(parents=True, exist_ok=True)
        (inbox / "lovelace-2024-tool-agents.pdf").write_bytes(b"%PDF-1.4\nscanned\n")
        attach_scan_result = await session.call_tool(
            "attach_pdf",
            {"scan_incoming": True, "move": True, "direction": "beta"},
        )
        assert_ok(attach_scan_result)
        attach_scan_payload = json.loads(attach_scan_result.content[0].text)
        assert attach_scan_payload["mode"] == "scan"
        assert attach_scan_payload["counts"]["archived"] == 1
        assert (
            beta / "literature-kb" / "01_Raw" / "pdf" / "lovelace-2024-tool-agents.pdf"
        ).is_file()
        assert not (inbox / "lovelace-2024-tool-agents.pdf").exists()

        lint_result = await session.call_tool("lint", {})
        assert_ok(lint_result)

        resources = await session.list_resources()
        resource_uris = {str(resource.uri) for resource in resources.resources}
        assert "lgrlw://project/summary" in resource_uris
        assert "lgrlw://kb/papers" in resource_uris
        assert "lgrlw://workspaces" in resource_uris

        papers = await session.read_resource("lgrlw://kb/papers")
        paper_payload = json.loads(papers.contents[0].text)
        paper_ids = {item["frontmatter"]["id"] for item in paper_payload if item["frontmatter"]}
        assert "lovelace-2024-tool-agents" in paper_ids
        assert "lovelace-2025-promoted-paper" in paper_ids

        workspaces = await session.read_resource("lgrlw://workspaces")
        workspace_payload = json.loads(workspaces.contents[0].text)
        assert any(item["workspace"] == "paper_001" for item in workspace_payload)


def assert_ok(result: object) -> None:
    assert not getattr(result, "isError", False), result


def _prepare_accepted_workspace(workspace: Path) -> None:
    status_path = workspace / "00_Project" / "paper_status.md"
    fm, body = read_frontmatter(status_path)
    assert fm is not None
    fm.update(
        {
            "status": "accepted",
            "final_title": "Promoted Paper",
            "final_authors": ["Ada Lovelace"],
            "venue": "ICLR",
            "year": 2025,
            "doi": "10.1234/promoted.paper",
        }
    )
    write_frontmatter(status_path, fm, body)

    promotion_dir = workspace / "06_Promotion"
    promotion_dir.mkdir(parents=True, exist_ok=True)
    (promotion_dir / "final_metadata.md").write_text(
        "# Final metadata\n\nCamera-ready: https://example.org/promoted.pdf\n",
        encoding="utf-8",
        newline="\n",
    )
    (promotion_dir / "promotion_checklist.md").write_text(
        "# Checklist\n\n- [x] Final metadata verified\n",
        encoding="utf-8",
        newline="\n",
    )
    (promotion_dir / "add_back_to_kb_plan.md").write_text(
        "# Add back plan\n\n- Update field structure with the accepted result\n",
        encoding="utf-8",
        newline="\n",
    )
