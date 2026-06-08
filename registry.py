"""
providers/registry.py
──────────────────────
Builds and returns the active FastMCP 3.0 providers based on
the PROVIDERS section of config/settings.py.

FastMCP 3.0 Provider types used here:
  • LocalProvider      — @mcp.tool decorators (built into FastMCP itself)
  • FileSystemProvider — scans a directory for tool modules
  • OpenAPIProvider    — converts an OpenAPI spec to tools
  • ProxyProvider      — transparently forwards to another MCP server
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_providers(provider_cfg: dict[str, Any]) -> dict[str, Any]:
    """
    Returns a dict of {name: provider_instance} for every enabled provider
    in the configuration.  Names are used to look up NAMESPACES in settings.
    """
    providers: dict[str, Any] = {}

    # ── FileSystemProvider ────────────────────────────────────
    fs_cfg = provider_cfg.get("filesystem", {})
    if fs_cfg.get("enabled"):
        try:
            from fastmcp.server.providers import FileSystemProvider
            providers["filesystem"] = FileSystemProvider(
                path=fs_cfg["path"],
                reload=fs_cfg.get("reload", False),
            )
            logger.info("FileSystemProvider loaded from '%s'", fs_cfg["path"])
        except ImportError as exc:
            logger.warning("FileSystemProvider unavailable: %s", exc)

    # ── OpenAPIProvider ───────────────────────────────────────
    oa_cfg = provider_cfg.get("openapi", {})
    if oa_cfg.get("enabled"):
        try:
            from fastmcp.server.providers import OpenAPIProvider
            providers["openapi"] = OpenAPIProvider(
                openapi_spec=oa_cfg["spec_url"],
                base_url=oa_cfg["base_url"],
                headers=oa_cfg.get("headers", {}),
            )
            logger.info("OpenAPIProvider loaded from '%s'", oa_cfg["spec_url"])
        except ImportError as exc:
            logger.warning("OpenAPIProvider unavailable: %s", exc)

    # ── ProxyProvider ─────────────────────────────────────────
    px_cfg = provider_cfg.get("proxy", {})
    if px_cfg.get("enabled"):
        try:
            from fastmcp import Client
            from fastmcp.server.providers import ProxyProvider
            upstream_client = Client(px_cfg["upstream_url"])
            providers["proxy"] = ProxyProvider(upstream_client)
            logger.info("ProxyProvider → '%s'", px_cfg["upstream_url"])
        except ImportError as exc:
            logger.warning("ProxyProvider unavailable: %s", exc)

    if not providers:
        logger.info(
            "No external providers enabled — server relies on @mcp.tool decorators only."
        )
    return providers
