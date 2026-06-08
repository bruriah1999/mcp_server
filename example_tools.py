"""
tools/example_tools.py
───────────────────────
Template for adding your own enterprise tools.

This file lives in the ./tools/ directory, which is scanned by
FileSystemProvider.  Drop a new .py file here and (with reload=True)
the server picks it up automatically.

Demonstrates:
  • Basic tool with typed I/O
  • Component versioning  (version="2.0")
  • Tag-based access control  (tags={"admin"})
  • Background task  (task=True)
  • Returnable error  (ToolResult with is_error=True)
"""

from __future__ import annotations

from fastmcp import FastMCP, Context
from fastmcp.tools import ToolResult

# ── Each tool file exposes a local mcp instance.
#    FileSystemProvider discovers this automatically.
mcp = FastMCP("example-tools")


# ─────────────────────────────────────────────────────────────────────────────
# Basic tool — replaces any number of your existing REST API endpoints
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool(
    version="1.0",                    # FastMCP 3.0 component versioning
    tags={"data", "read"},
    description="Query the enterprise data API.  <CONFIGURE: replace with real logic>",
)
async def query_enterprise_data(
    endpoint: str,
    params: dict | None = None,
    ctx: Context = None,
) -> dict:
    """
    Parameters
    ----------
    endpoint : str
        API endpoint path, e.g. "/sales/monthly".
    params : dict, optional
        Query parameters forwarded to the API.
    """
    # ── <CONFIGURE>  replace with your real API call ──────────────────────
    await ctx.info(f"query_enterprise_data called: endpoint={endpoint}")
    # import httpx
    # async with httpx.AsyncClient() as client:
    #     r = await client.get(f"{BASE_URL}{endpoint}", params=params or {})
    #     r.raise_for_status()
    #     return r.json()
    return {"endpoint": endpoint, "params": params, "result": "<configure me>"}


# ─────────────────────────────────────────────────────────────────────────────
# Upgraded version — v2 with richer output schema
# FastMCP automatically selects v2 for new clients; v1 stays for legacy.
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool(
    version="2.0",
    tags={"data", "read"},
    description=(
        "Query the enterprise data API (v2) — returns structured results "
        "with metadata.  <CONFIGURE>"
    ),
)
async def query_enterprise_data(  # noqa: F811 — intentional version override
    endpoint: str,
    params: dict | None = None,
    include_metadata: bool = False,
    ctx: Context = None,
) -> dict:
    result = {"endpoint": endpoint, "data": [], "total": 0}
    if include_metadata:
        result["meta"] = {"version": "2.0", "server": "enterprise-mcp"}
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Admin-gated tool — hidden until unlock_role("admin") is called
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool(
    tags={"admin", "write"},
    description="[ADMIN] Execute a privileged write operation.  <CONFIGURE>",
)
async def admin_write_operation(
    target: str,
    payload: dict,
    ctx: Context = None,
) -> dict:
    """Only visible after the client has called unlock_role('admin')."""
    await ctx.warning(f"admin_write_operation: target={target}")
    # ── <CONFIGURE>  your privileged operation here ───────────────────────
    return {"target": target, "status": "executed", "payload": payload}


# ─────────────────────────────────────────────────────────────────────────────
# Background task — long-running operation using FastMCP 3.0 Docket
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool(
    task=True,    # ← FastMCP 3.0 background task (requires fastmcp[tasks])
    tags={"data", "async"},
    description="Trigger a long-running data export job.  <CONFIGURE>",
)
async def export_dataset(
    dataset_name: str,
    format: str = "parquet",
    ctx: Context = None,
) -> dict:
    """
    Runs as a background task — the agent receives a job ID immediately
    and can poll for completion via the progress notification.
    """
    await ctx.info(f"export_dataset started: {dataset_name} → {format}")
    # ── <CONFIGURE>  your export logic here ──────────────────────────────
    # e.g. await run_export_pipeline(dataset_name, format)
    return {
        "status": "enqueued",
        "dataset": dataset_name,
        "format": format,
        "message": "Export job queued.  <configure>",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tool with rich error handling  (FastMCP 3.4 ToolResult is_error)
# ─────────────────────────────────────────────────────────────────────────────

@mcp.tool(
    tags={"data", "validated"},
    description="Validate and submit an enterprise record.  <CONFIGURE>",
)
async def submit_record(record: dict, ctx: Context = None) -> ToolResult:
    """
    Returns a ToolResult with is_error=True on validation failure so the
    agent can inspect and correct the record rather than crashing.
    """
    # ── Validation ───────────────────────────────────────────────────────
    required_fields = ["id", "type", "timestamp"]   # <CONFIGURE>
    missing = [f for f in required_fields if f not in record]
    if missing:
        return ToolResult(
            content=[{"type": "text", "text": f"Validation failed — missing fields: {missing}"}],
            is_error=True,
        )

    # ── <CONFIGURE>  real submission logic here ───────────────────────────
    return ToolResult(
        content=[{"type": "text", "text": f"Record {record.get('id')} submitted."}],
        is_error=False,
    )
