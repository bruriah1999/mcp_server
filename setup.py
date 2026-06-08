"""
auth/setup.py
──────────────
Configures authentication on the FastMCP server based on
config/settings.py  →  AUTH.

Supports:
  • JWT Bearer tokens
  • OAuth 2.1 proxy (WorkOS / Azure / GitHub / Google / etc.)
  • No-op passthrough (when AUTH.enabled = False)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def configure_auth(mcp: FastMCP, cfg: dict[str, Any]) -> None:
    if not cfg.get("enabled"):
        logger.info("Auth disabled (AUTH.enabled = False). All requests accepted.")
        return

    provider_name = cfg.get("provider", "jwt")

    if provider_name == "jwt":
        _configure_jwt(mcp, cfg.get("jwt", {}))
    elif provider_name == "oauth":
        _configure_oauth(mcp, cfg.get("oauth", {}))
    elif provider_name == "bearer":
        _configure_bearer(mcp, cfg)
    else:
        logger.warning("Unknown auth provider '%s'; auth disabled.", provider_name)


# ─────────────────────────────────────────────────────────────────────────────
# JWT
# ─────────────────────────────────────────────────────────────────────────────

def _configure_jwt(mcp: FastMCP, jwt_cfg: dict) -> None:
    secret = os.getenv(jwt_cfg.get("secret_env_var", "JWT_SECRET"), "")
    if not secret:
        logger.warning(
            "JWT secret env var '%s' is not set. Auth will fail for all requests.",
            jwt_cfg.get("secret_env_var"),
        )
        return

    try:
        from fastmcp.server.auth import JWTVerifier
        mcp.auth = JWTVerifier(
            secret=secret,
            algorithm=jwt_cfg.get("algorithm", "HS256"),
            audience=jwt_cfg.get("audience"),
        )
        logger.info("JWT auth configured (algorithm=%s).", jwt_cfg.get("algorithm"))
    except ImportError:
        logger.warning("JWTVerifier not found; JWT auth unavailable.")


# ─────────────────────────────────────────────────────────────────────────────
# OAuth 2.1 Proxy
# ─────────────────────────────────────────────────────────────────────────────

def _configure_oauth(mcp: FastMCP, oauth_cfg: dict) -> None:
    client_id = os.getenv(oauth_cfg.get("client_id_env_var", "OAUTH_CLIENT_ID"), "")
    client_secret = os.getenv(
        oauth_cfg.get("client_secret_env_var", "OAUTH_CLIENT_SECRET"), ""
    )
    if not client_id or not client_secret:
        logger.warning(
            "OAuth client_id / client_secret not set in environment. Auth skipped."
        )
        return

    try:
        from fastmcp.server.auth import OAuthProxy
        mcp.auth = OAuthProxy(
            client_id=client_id,
            client_secret=client_secret,
            authorization_url=oauth_cfg.get("authorization_url", ""),
            token_url=oauth_cfg.get("token_url", ""),
            scopes=oauth_cfg.get("scopes", []),
        )
        logger.info("OAuth proxy auth configured.")
    except ImportError:
        logger.warning("OAuthProxy not found; OAuth auth unavailable.")


# ─────────────────────────────────────────────────────────────────────────────
# Static Bearer token (simple dev/internal use)
# ─────────────────────────────────────────────────────────────────────────────

def _configure_bearer(mcp: FastMCP, cfg: dict) -> None:
    token = os.getenv("BEARER_TOKEN", "")
    if not token:
        logger.warning("BEARER_TOKEN env var not set; bearer auth skipped.")
        return

    try:
        from fastmcp.server.auth import BearerTokenVerifier
        mcp.auth = BearerTokenVerifier(token=token)
        logger.info("Static bearer token auth configured.")
    except ImportError:
        logger.warning("BearerTokenVerifier not found; bearer auth unavailable.")
