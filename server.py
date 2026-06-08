"""
Enterprise MCP Server — Main Entry Point
=========================================
Assembles providers, transforms, middleware, and auth
from config/settings.py and starts the FastMCP 3.x server.

Usage:
    python server.py                   # production (uses settings.py)
    fastmcp dev server.py              # development with hot-reload
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP

import config.settings as cfg
from providers.registry import build_providers
from transforms.pipeline import build_transforms
from middleware.stack import register_middleware
from auth.setup import configure_auth
from resources.templates import register_templates
from tools.meta_tools import register_meta_tools
from utils.lifespan import lifespan_manager
from utils.otel import configure_otel

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# 1. Optional OpenTelemetry (must be configured before server)
# ──────────────────────────────────────────────────────────────
if cfg.OTEL["enabled"]:
    configure_otel(cfg.OTEL)


# ──────────────────────────────────────────────────────────────
# 2. Instantiate the FastMCP server
#    list_page_size drives FastMCP 3.0 native pagination.
# ──────────────────────────────────────────────────────────────
mcp = FastMCP(
    name=cfg.SERVER_NAME,
    version=cfg.SERVER_VERSION,
    instructions=cfg.SERVER_DESCRIPTION,
    list_page_size=cfg.LIST_PAGE_SIZE,   # ← FastMCP 3.0 pagination
    lifespan=lifespan_manager,
)


# ──────────────────────────────────────────────────────────────
# 3. Auth
# ──────────────────────────────────────────────────────────────
configure_auth(mcp, cfg.AUTH)


# ──────────────────────────────────────────────────────────────
# 4. Middleware
# ──────────────────────────────────────────────────────────────
register_middleware(mcp, cfg.MIDDLEWARE)


# ──────────────────────────────────────────────────────────────
# 5. Dynamic Providers  (FastMCP 3.0 — Provider Architecture)
#    Each provider is mounted with its own namespace transform.
# ──────────────────────────────────────────────────────────────
for provider_name, provider in build_providers(cfg.PROVIDERS).items():
    namespace = cfg.NAMESPACES.get(provider_name, "")
    transforms = build_transforms(
        namespace=namespace,
        role_gates=cfg.ROLE_GATES,
    )
    mcp.mount(provider, transforms=transforms)
    logger.info("Mounted provider '%s' (namespace='%s')", provider_name, namespace)


# ──────────────────────────────────────────────────────────────
# 6. Resource Templates  (parameterised URIs)
# ──────────────────────────────────────────────────────────────
register_templates(mcp, cfg.RESOURCE_TEMPLATES)


# ──────────────────────────────────────────────────────────────
# 7. Meta-tools: semantic search + admin unlock
#    search_tools  — Search Transform (FastMCP 3.1)
#    unlock_admin  — progressive disclosure via session state
# ──────────────────────────────────────────────────────────────
register_meta_tools(mcp, cfg.SEMANTIC_SEARCH, cfg.ROLE_GATES)


# ──────────────────────────────────────────────────────────────
# 8. Run
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(
        transport=cfg.TRANSPORT,
        host=cfg.HOST,
        port=cfg.PORT,
        log_level=cfg.LOG_LEVEL,
    )
