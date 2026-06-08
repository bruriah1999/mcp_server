"""
tools/meta_tools.py
────────────────────
Registers the two core "meta-tools" that power scale:

1. search_tools  — FastMCP 3.1 Search Transform
   Calls your custom semantic retrieval API and returns only the
   relevant tool definitions, keeping the context window clean.

2. unlock_role   — Progressive Disclosure (FastMCP 3.0 Session State)
   Authenticated users can call this to reveal gated tool sets
   for the current session without restarting.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastmcp import FastMCP, Context

logger = logging.getLogger(__name__)


def register_meta_tools(
    mcp: FastMCP,
    search_cfg: dict[str, Any],
    role_gates: dict[str, list[str]],
) -> None:
    _register_search_tool(mcp, search_cfg)
    _register_unlock_tool(mcp, role_gates)


# ─────────────────────────────────────────────────────────────────────────────
# 1. SEARCH TRANSFORM — on-demand semantic tool discovery
# ─────────────────────────────────────────────────────────────────────────────

def _register_search_tool(mcp: FastMCP, cfg: dict[str, Any]) -> None:
    if not cfg.get("enabled"):
        return

    api_base = cfg["api_base_url"]
    api_key_var = cfg.get("api_key_env_var", "")
    top_k = cfg.get("top_k", 10)
    threshold = cfg.get("score_threshold", 0.25)
    timeout = cfg.get("timeout_seconds", 5.0)

    @mcp.tool(
        name="search_tools",
        description=(
            "Semantic search over all available enterprise tools. "
            "Instead of loading every tool at once, call this first to find "
            "the most relevant tools for your current task. "
            "Returns a list of {name, description, score} objects."
        ),
        tags={"meta", "search"},
    )
    async def search_tools(query: str, ctx: Context) -> list[dict]:
        """
        Parameters
        ----------
        query : str
            Natural-language description of what you want to do.
            Example: "execute a SQL query against the sales table"
        """
        api_key = os.getenv(api_key_var, "")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{api_base}/search",
                    json={"query": query, "top_k": top_k},
                    headers=headers,
                )
                response.raise_for_status()
                results: list[dict] = response.json()

            # Filter by relevance threshold
            filtered = [r for r in results if r.get("score", 0) >= threshold]

            await ctx.info(
                f"search_tools: '{query}' → {len(filtered)}/{len(results)} results "
                f"above threshold {threshold}"
            )
            return filtered

        except httpx.HTTPError as exc:
            await ctx.warning(f"Semantic retrieval API error: {exc}")
            # Fail gracefully — return empty rather than crashing the agent
            return []


# ─────────────────────────────────────────────────────────────────────────────
# 2. PROGRESSIVE DISCLOSURE — session-scoped role unlock
# ─────────────────────────────────────────────────────────────────────────────

def _register_unlock_tool(
    mcp: FastMCP,
    role_gates: dict[str, list[str]],
) -> None:
    if not role_gates:
        return

    # Build a human-readable list of available roles for the docstring
    role_list = ", ".join(f'"{r}"' for r in role_gates)

    @mcp.tool(
        name="unlock_role",
        description=(
            "Unlock a gated set of tools for the current session. "
            "Available roles: " + role_list + ". "
            "Requires a valid OAuth scope. Once unlocked, the new tools "
            "appear in tools/list for this session only."
        ),
        tags={"meta", "auth"},
    )
    async def unlock_role(role: str, ctx: Context) -> dict:
        """
        Parameters
        ----------
        role : str
            The role tag to unlock, e.g. "admin", "write", "sensitive".
        """
        if role not in role_gates:
            return {
                "success": False,
                "error": f"Unknown role '{role}'. Valid roles: {list(role_gates.keys())}",
            }

        required_scopes = role_gates[role]

        # Scope verification — works when OAuth auth is enabled.
        # Gracefully skips if auth is not configured.
        try:
            from fastmcp.server.auth import require_scopes
            checker = require_scopes(*required_scopes)
            await checker(ctx)
        except Exception as exc:
            return {"success": False, "error": f"Insufficient permissions: {exc}"}

        # Reveal the gated tools for this session (FastMCP 3.0 session state)
        try:
            await ctx.enable_components(tags={role})
            await ctx.info(f"unlock_role: '{role}' unlocked for session {ctx.session_id}")
            return {
                "success": True,
                "message": f"Role '{role}' unlocked. New tools are now available.",
                "unlocked_tag": role,
            }
        except AttributeError:
            # ctx.enable_components not available in this FastMCP build
            logger.warning(
                "ctx.enable_components not found — session-scoped unlock unavailable."
            )
            return {"success": False, "error": "Session state not supported in this build."}
