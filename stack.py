"""
middleware/stack.py
────────────────────
Registers all configured middleware on the FastMCP server.

Middleware applied:
  • LoggingMiddleware         — structured request/response logs
  • RateLimitingMiddleware    — per-client request throttling
  • ResponseLimitingMiddleware— caps tool response sizes (FastMCP 2.13+)
  • CachingMiddleware         — response caching for expensive tools
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_middleware(mcp: FastMCP, cfg: dict[str, Any]) -> None:
    """Attach all enabled middleware to *mcp* in the correct order."""

    # Order matters: logging wraps everything; caching sits inside rate limiting.
    if cfg.get("logging", {}).get("enabled"):
        _add_logging_middleware(mcp, cfg["logging"])

    if cfg.get("rate_limiting", {}).get("enabled"):
        _add_rate_limiting_middleware(mcp, cfg["rate_limiting"])

    if cfg.get("response_limiting", {}).get("enabled"):
        _add_response_limiting_middleware(mcp, cfg["response_limiting"])

    if cfg.get("caching", {}).get("enabled"):
        _add_caching_middleware(mcp, cfg["caching"])


# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

def _add_logging_middleware(mcp: FastMCP, cfg: dict) -> None:
    include_payloads = cfg.get("include_payloads", False)

    try:
        from fastmcp.server.middleware import Middleware, CallNext, MCPRequest, MCPResponse

        class StructuredLoggingMiddleware(Middleware):
            async def __call__(
                self, request: MCPRequest, call_next: CallNext
            ) -> MCPResponse:
                start = time.perf_counter()
                logger.info(
                    "MCP request: method=%s",
                    request.method,
                    extra={"payload": request.params if include_payloads else None},
                )
                response = await call_next(request)
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "MCP response: method=%s elapsed_ms=%.1f",
                    request.method,
                    elapsed_ms,
                )
                return response

        mcp.add_middleware(StructuredLoggingMiddleware())
        logger.info("LoggingMiddleware registered.")
    except ImportError:
        logger.debug("FastMCP middleware API unavailable; skipping LoggingMiddleware.")


# ─────────────────────────────────────────────────────────────────────────────
# Rate Limiting
# ─────────────────────────────────────────────────────────────────────────────

def _add_rate_limiting_middleware(mcp: FastMCP, cfg: dict) -> None:
    rpm = cfg.get("requests_per_minute", 60)
    window = 60.0  # seconds

    try:
        from fastmcp.server.middleware import Middleware, CallNext, MCPRequest, MCPResponse

        class RateLimitingMiddleware(Middleware):
            def __init__(self) -> None:
                # {client_id: [timestamp, ...]}
                self._buckets: dict[str, list[float]] = defaultdict(list)

            async def __call__(
                self, request: MCPRequest, call_next: CallNext
            ) -> MCPResponse:
                client_id = getattr(request, "client_id", "default")
                now = time.monotonic()
                bucket = self._buckets[client_id]
                # Evict timestamps outside the rolling window
                self._buckets[client_id] = [t for t in bucket if now - t < window]
                if len(self._buckets[client_id]) >= rpm:
                    raise PermissionError(
                        f"Rate limit exceeded: {rpm} requests/{window:.0f}s per client."
                    )
                self._buckets[client_id].append(now)
                return await call_next(request)

        mcp.add_middleware(RateLimitingMiddleware())
        logger.info("RateLimitingMiddleware registered: %d rpm.", rpm)
    except ImportError:
        logger.debug("FastMCP middleware API unavailable; skipping RateLimitingMiddleware.")


# ─────────────────────────────────────────────────────────────────────────────
# Response Size Limiting  (FastMCP 2.13 ResponseLimitingMiddleware)
# ─────────────────────────────────────────────────────────────────────────────

def _add_response_limiting_middleware(mcp: FastMCP, cfg: dict) -> None:
    max_bytes = cfg.get("max_bytes", 512 * 1024)

    try:
        from fastmcp.server.middleware import ResponseLimitingMiddleware
        mcp.add_middleware(ResponseLimitingMiddleware(max_bytes=max_bytes))
        logger.info("ResponseLimitingMiddleware registered: max=%d bytes.", max_bytes)
    except ImportError:
        logger.debug("ResponseLimitingMiddleware not found; skipping.")


# ─────────────────────────────────────────────────────────────────────────────
# Response Caching  (FastMCP 2.13 CachingMiddleware / custom)
# ─────────────────────────────────────────────────────────────────────────────

def _add_caching_middleware(mcp: FastMCP, cfg: dict) -> None:
    ttl = cfg.get("ttl_seconds", 60)

    # Try the built-in CachingMiddleware first
    try:
        from fastmcp.server.middleware import CachingMiddleware
        mcp.add_middleware(CachingMiddleware(ttl=ttl))
        logger.info("CachingMiddleware registered: ttl=%ds.", ttl)
        return
    except ImportError:
        pass

    # Fallback: simple in-process dict cache
    try:
        from fastmcp.server.middleware import Middleware, CallNext, MCPRequest, MCPResponse
        import hashlib

        class SimpleCachingMiddleware(Middleware):
            def __init__(self) -> None:
                self._cache: dict[str, tuple[float, Any]] = {}

            async def __call__(
                self, request: MCPRequest, call_next: CallNext
            ) -> MCPResponse:
                # Only cache tools/call; pass through everything else
                if getattr(request, "method", "") != "tools/call":
                    return await call_next(request)
                key = hashlib.md5(
                    str(request.params).encode(), usedforsecurity=False
                ).hexdigest()
                now = time.monotonic()
                if key in self._cache:
                    cached_at, cached_response = self._cache[key]
                    if now - cached_at < ttl:
                        return cached_response
                response = await call_next(request)
                self._cache[key] = (now, response)
                return response

        mcp.add_middleware(SimpleCachingMiddleware())
        logger.info("SimpleCachingMiddleware (fallback) registered: ttl=%ds.", ttl)
    except ImportError:
        logger.debug("FastMCP middleware API unavailable; skipping CachingMiddleware.")
