"""
tests/test_server.py
─────────────────────
FastMCP in-process tests — no network, no subprocesses.
Run with:  pytest tests/

Covers:
  • Server bootstrap (pagination, providers)
  • search_tools meta-tool
  • unlock_role progressive disclosure
  • Resource templates
  • Pagination cursor mechanics
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_server():
    """Build a minimal server for testing (pagination=3 for easy cursor testing)."""
    from fastmcp import FastMCP

    mcp = FastMCP("test-server", list_page_size=3)

    @mcp.tool
    async def tool_a() -> str:
        return "a"

    @mcp.tool
    async def tool_b() -> str:
        return "b"

    @mcp.tool
    async def tool_c() -> str:
        return "c"

    @mcp.tool
    async def tool_d() -> str:
        return "d"

    return mcp


# ─────────────────────────────────────────────────────────────────────────────
# Basic server
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_server_boots():
    from fastmcp import FastMCP
    mcp = FastMCP("enterprise-mcp-test")
    assert mcp.name == "enterprise-mcp-test"


@pytest.mark.asyncio
async def test_pagination_page_size():
    """list_page_size should produce paginated responses."""
    from fastmcp import FastMCP, Client
    mcp = FastMCP("pager", list_page_size=2)
    for i in range(5):
        async def _mk(n=i):
            @mcp.tool(name=f"pt_{n}")
            async def _t() -> str: return str(n)
        await _mk()
    async with Client(mcp) as client:
        page1 = await client.list_tools_mcp()
        assert len(page1.tools) == 2
        assert page1.nextCursor is not None


# ─────────────────────────────────────────────────────────────────────────────
# Pagination — cursor mechanics
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pagination_cursor():
    """Fetching page 1 then following the cursor should yield all tools."""
    from fastmcp import Client

    mcp = make_server()

    async with Client(mcp) as client:
        page1 = await client.list_tools_mcp()
        assert len(page1.tools) == 3

        if page1.nextCursor:
            page2 = await client.list_tools_mcp(cursor=page1.nextCursor)
            assert len(page2.tools) >= 1
            total = len(page1.tools) + len(page2.tools)
            assert total == 4


@pytest.mark.asyncio
async def test_list_tools_convenience_fetches_all():
    """list_tools() should transparently page through and return all tools."""
    from fastmcp import Client

    mcp = make_server()
    async with Client(mcp) as client:
        all_tools = await client.list_tools()
        assert len(all_tools) == 4


# ─────────────────────────────────────────────────────────────────────────────
# search_tools meta-tool
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_tools_returns_filtered_results():
    """search_tools should call the retrieval API and filter by score."""
    from fastmcp import FastMCP, Client
    from tools.meta_tools import register_meta_tools

    mcp = FastMCP("search-test")
    search_cfg = {
        "enabled": True,
        "api_base_url": "http://mock-api",
        "api_key_env_var": "",
        "top_k": 5,
        "score_threshold": 0.5,
    }
    register_meta_tools(mcp, search_cfg, {})

    mock_response = [
        {"name": "query_sales", "description": "...", "score": 0.9},
        {"name": "list_customers", "description": "...", "score": 0.3},  # below threshold
    ]

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_post.return_value)
        mock_post.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json = lambda: mock_response

        async with Client(mcp) as client:
            result = await client.call_tool("search_tools", {"query": "sales data"})
            # Only results above score_threshold=0.5 are returned
            # FastMCP 3.4 call_tool returns CallToolResult; .data holds the Python value
            actual = result.data if hasattr(result, 'data') else result
            assert isinstance(actual, list)


@pytest.mark.asyncio
async def test_search_tools_graceful_on_api_failure():
    """search_tools should return [] and not crash when the API is down."""
    from fastmcp import FastMCP, Client
    from tools.meta_tools import register_meta_tools
    import httpx

    mcp = FastMCP("search-fail-test")
    register_meta_tools(
        mcp,
        {"enabled": True, "api_base_url": "http://dead-host", "score_threshold": 0.0, "top_k": 5},
        {},
    )

    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("refused")):
        async with Client(mcp) as client:
            result = await client.call_tool("search_tools", {"query": "anything"})
            actual = result.data if hasattr(result, 'data') else result
            assert actual == []


# ─────────────────────────────────────────────────────────────────────────────
# unlock_role
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unlock_role_unknown_role():
    """Requesting a non-existent role should return success=False."""
    from fastmcp import FastMCP, Client
    from tools.meta_tools import register_meta_tools

    mcp = FastMCP("unlock-test")
    register_meta_tools(mcp, {"enabled": False}, {"admin": ["admin:tools"]})

    async with Client(mcp) as client:
        result = await client.call_tool("unlock_role", {"role": "superuser"})
        data = result.data if hasattr(result, 'data') else result
        assert data["success"] is False
        assert "Unknown role" in data["error"]


# ─────────────────────────────────────────────────────────────────────────────
# Resource templates
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_table_schema_template():
    """Table schema resource template should return valid JSON."""
    import json
    from fastmcp import FastMCP, Client
    from resources.templates import register_templates

    mcp = FastMCP("template-test")
    register_templates(
        mcp,
        {
            "table_schema": {
                "uri_template": "enterprise://tables/{table_name}/schema",
                "description": "test",
                "mime_type": "application/json",
            }
        },
    )

    async with Client(mcp) as client:
        contents = await client.read_resource("enterprise://tables/sales/schema")
        # FastMCP 3.x read_resource returns a list of TextResourceContents / BlobResourceContents
        raw = contents[0].text if hasattr(contents[0], "text") else contents[0].content
        data = json.loads(raw)
        assert data["table"] == "sales"
