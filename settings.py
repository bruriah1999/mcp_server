"""
Enterprise MCP Server — Configuration
======================================
Fill in the values marked  <CONFIGURE>  before running.
All other defaults are production-safe starting points.
"""

from __future__ import annotations

from typing import Literal


# ──────────────────────────────────────────────────────────────
# SERVER IDENTITY
# ──────────────────────────────────────────────────────────────
SERVER_NAME: str = "Enterprise MCP"          # <CONFIGURE>  display name
SERVER_VERSION: str = "1.0.0"
SERVER_DESCRIPTION: str = (                   # <CONFIGURE>  shown in discovery
    "Enterprise-grade MCP server with semantic tool retrieval."
)

# ──────────────────────────────────────────────────────────────
# TRANSPORT
# ──────────────────────────────────────────────────────────────
TRANSPORT: Literal["http", "sse", "stdio"] = "http"
HOST: str = "0.0.0.0"
PORT: int = 8000
LOG_LEVEL: Literal["debug", "info", "warning", "error"] = "info"

# ──────────────────────────────────────────────────────────────
# PAGINATION  (FastMCP 3.0 — list_page_size)
# Controls how many tools/resources/prompts are returned per
# tools/list page.  Set to None to disable pagination entirely.
# ──────────────────────────────────────────────────────────────
LIST_PAGE_SIZE: int | None = 50   # <CONFIGURE>  raise/lower for your catalog size

# ──────────────────────────────────────────────────────────────
# SEMANTIC SEARCH TRANSFORM  (FastMCP 3.1 — Search Transforms)
# Your custom retrieval API is called whenever the LLM sends
# a search query via the `search_tools` meta-tool.
# ──────────────────────────────────────────────────────────────
SEMANTIC_SEARCH = dict(
    enabled=True,
    # <CONFIGURE>  base URL of your semantic retrieval service
    api_base_url="https://your-retrieval-service.internal/api",   # <CONFIGURE>
    api_key_env_var="SEMANTIC_API_KEY",   # env-var that holds the bearer token
    top_k=10,                             # how many tools to surface per query
    score_threshold=0.25,                 # min relevance score (0–1)
    timeout_seconds=5.0,
)

# ──────────────────────────────────────────────────────────────
# DYNAMIC PROVIDERS  (FastMCP 3.0 — Provider Architecture)
# ──────────────────────────────────────────────────────────────
PROVIDERS = dict(
    # FileSystemProvider: scan a local directory for tool modules
    filesystem=dict(
        enabled=True,
        path="./tools",        # <CONFIGURE>  where your tool .py files live
        reload=True,           # hot-reload on file change (dev-friendly)
    ),
    # OpenAPIProvider: wrap an existing REST API automatically
    openapi=dict(
        enabled=False,         # <CONFIGURE>  flip to True when ready
        spec_url="https://your-api.internal/openapi.json",  # <CONFIGURE>
        base_url="https://your-api.internal",               # <CONFIGURE>
        # Headers forwarded to every downstream request
        headers={},            # <CONFIGURE>  e.g. {"X-Api-Key": "..."}
    ),
    # ProxyProvider: transparently forward to another MCP server
    proxy=dict(
        enabled=False,         # <CONFIGURE>
        upstream_url="http://upstream-mcp-server:8000/mcp",  # <CONFIGURE>
    ),
)

# ──────────────────────────────────────────────────────────────
# RESOURCE TEMPLATES  (parameterised dynamic URIs)
# ──────────────────────────────────────────────────────────────
RESOURCE_TEMPLATES = dict(
    # Enterprise table schema — fill in your catalog identifiers
    table_schema=dict(
        uri_template="enterprise://tables/{table_name}/schema",
        description="Return the schema for a named enterprise table.",
        mime_type="application/json",
    ),
    # Semantic search results as a resource
    search_results=dict(
        uri_template="search://{query}",
        description="Live semantic search results for an arbitrary query.",
        mime_type="application/json",
    ),
    # Generic document retrieval
    document=dict(
        uri_template="docs://{doc_id}",
        description="Retrieve an enterprise document by ID.",
        mime_type="text/plain",
    ),
)

# ──────────────────────────────────────────────────────────────
# SESSION STATE
# ──────────────────────────────────────────────────────────────
SESSION = dict(
    # Redis URL for persistent / distributed sessions.
    # Set to "memory://" for in-process (single instance) sessions.
    backend="memory://",          # <CONFIGURE>  e.g. "redis://redis:6379/0"
    ttl_seconds=3600,
)

# ──────────────────────────────────────────────────────────────
# AUTHENTICATION
# ──────────────────────────────────────────────────────────────
AUTH = dict(
    enabled=False,                # <CONFIGURE>  flip to True for production
    provider="jwt",               # <CONFIGURE>  "jwt" | "oauth" | "bearer"
    # For JWT verification
    jwt=dict(
        secret_env_var="JWT_SECRET",   # <CONFIGURE>
        algorithm="HS256",
        audience=None,                 # <CONFIGURE>  e.g. "enterprise-mcp"
    ),
    # For OAuth 2.1 proxy (WorkOS / Azure / GitHub / etc.)
    oauth=dict(
        client_id_env_var="OAUTH_CLIENT_ID",         # <CONFIGURE>
        client_secret_env_var="OAUTH_CLIENT_SECRET", # <CONFIGURE>
        authorization_url="",                        # <CONFIGURE>
        token_url="",                                # <CONFIGURE>
        scopes=["read:tools"],                       # <CONFIGURE>
    ),
)

# ──────────────────────────────────────────────────────────────
# ROLE-BASED ACCESS  (tags → required scopes)
# ──────────────────────────────────────────────────────────────
ROLE_GATES: dict[str, list[str]] = {
    # tag on the tool : list of OAuth scopes that unlock it
    "admin":      ["admin:tools"],        # <CONFIGURE>
    "write":      ["write:tools"],        # <CONFIGURE>
    "sensitive":  ["sensitive:access"],   # <CONFIGURE>
}

# ──────────────────────────────────────────────────────────────
# MIDDLEWARE
# ──────────────────────────────────────────────────────────────
MIDDLEWARE = dict(
    rate_limiting=dict(
        enabled=True,
        requests_per_minute=60,   # <CONFIGURE>
    ),
    response_limiting=dict(
        enabled=True,
        max_bytes=512 * 1024,     # 512 KB  <CONFIGURE>
    ),
    logging=dict(
        enabled=True,
        include_payloads=False,   # <CONFIGURE>  True adds latency but full traces
    ),
    caching=dict(
        enabled=True,
        ttl_seconds=60,           # <CONFIGURE>  how long to cache tool responses
    ),
)

# ──────────────────────────────────────────────────────────────
# BACKGROUND TASKS  (FastMCP 3.0 — Docket integration)
# ──────────────────────────────────────────────────────────────
BACKGROUND_TASKS = dict(
    enabled=False,                # <CONFIGURE>  True requires fastmcp[tasks]
    broker_url="memory://",       # <CONFIGURE>  "redis://redis:6379/0" for prod
)

# ──────────────────────────────────────────────────────────────
# OPENTELEMETRY
# ──────────────────────────────────────────────────────────────
OTEL = dict(
    enabled=False,                         # <CONFIGURE>
    endpoint="http://otel-collector:4318", # <CONFIGURE>  OTLP/HTTP endpoint
    service_name=SERVER_NAME,
)

# ──────────────────────────────────────────────────────────────
# TOOL NAMESPACING  (Transform layer)
# Each provider can be mounted under its own namespace prefix
# to prevent collisions when you combine many providers.
# ──────────────────────────────────────────────────────────────
NAMESPACES: dict[str, str] = {
    "filesystem": "",          # <CONFIGURE>  e.g. "fs" → tools become "fs_my_tool"
    "openapi":    "api",       # <CONFIGURE>
    "proxy":      "upstream",  # <CONFIGURE>
}

# ──────────────────────────────────────────────────────────────
# COMPONENT VERSIONING
# ──────────────────────────────────────────────────────────────
VERSIONING = dict(
    enabled=True,
    default_version="1.0",
    # FastMCP automatically selects the highest version for each
    # component name; older versions remain accessible for clients
    # that pin a specific version.
)
