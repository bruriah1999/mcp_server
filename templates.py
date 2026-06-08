"""
resources/templates.py
───────────────────────
Registers FastMCP 3.0 Resource Templates — parameterised URIs
that let the LLM access dynamic data without pre-enumerating
every possible endpoint.

URI syntax:  enterprise://tables/{table_name}/schema
             search://{query}
             docs://{doc_id}

Add new templates in config/settings.py  →  RESOURCE_TEMPLATES
and implement the corresponding handler function below.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_templates(mcp: FastMCP, template_cfg: dict[str, Any]) -> None:
    """Register all enabled resource templates on *mcp*."""

    _register_table_schema_template(mcp, template_cfg.get("table_schema", {}))
    _register_search_results_template(mcp, template_cfg.get("search_results", {}))
    _register_document_template(mcp, template_cfg.get("document", {}))


# ─────────────────────────────────────────────────────────────────────────────
# Template 1 — Table schema
#   URI:  enterprise://tables/{table_name}/schema
# ─────────────────────────────────────────────────────────────────────────────

def _register_table_schema_template(mcp: FastMCP, cfg: dict) -> None:
    if not cfg:
        return

    uri_template = cfg.get("uri_template", "enterprise://tables/{table_name}/schema")
    mime_type = cfg.get("mime_type", "application/json")

    @mcp.resource(
        uri=uri_template,
        description=cfg.get(
            "description",
            "Return the column schema for a named enterprise table.",
        ),
        mime_type=mime_type,
    )
    async def get_table_schema(table_name: str) -> str:
        """
        Parameters
        ----------
        table_name : str
            Logical name of the enterprise table, e.g. "sales_transactions".

        Implementation note
        -------------------
        Replace the stub below with a real call to your catalog / metadata API.
        """
        # ── <CONFIGURE>  replace with your actual catalog lookup ─────────────
        schema = await _fetch_table_schema(table_name)
        # ────────────────────────────────────────────────────────────────────
        return json.dumps(schema, ensure_ascii=False, indent=2)


async def _fetch_table_schema(table_name: str) -> dict:
    """Stub — replace with your catalog/metadata service call."""
    # Example return shape — your real implementation goes here
    return {
        "table": table_name,
        "columns": [],            # <CONFIGURE>  populate from your catalog
        "description": "",        # <CONFIGURE>
        "row_count_estimate": 0,  # <CONFIGURE>
    }


# ─────────────────────────────────────────────────────────────────────────────
# Template 2 — Semantic search results
#   URI:  search://{query}
# ─────────────────────────────────────────────────────────────────────────────

def _register_search_results_template(mcp: FastMCP, cfg: dict) -> None:
    if not cfg:
        return

    uri_template = cfg.get("uri_template", "search://{query}")

    @mcp.resource(
        uri=uri_template,
        description=cfg.get("description", "Live semantic search results for a query."),
        mime_type=cfg.get("mime_type", "application/json"),
    )
    async def get_search_results(query: str) -> str:
        """
        Parameters
        ----------
        query : str
            Free-text search query.

        Implementation note
        -------------------
        Replace the stub below with a call to your retrieval service.
        """
        # ── <CONFIGURE>  replace with your retrieval API call ────────────────
        results = await _call_retrieval_api(query)
        # ────────────────────────────────────────────────────────────────────
        return json.dumps(results, ensure_ascii=False)


async def _call_retrieval_api(query: str) -> list[dict]:
    """Stub — replace with your semantic retrieval service call."""
    return [{"query": query, "results": [], "note": "replace with real implementation"}]


# ─────────────────────────────────────────────────────────────────────────────
# Template 3 — Document retrieval
#   URI:  docs://{doc_id}
# ─────────────────────────────────────────────────────────────────────────────

def _register_document_template(mcp: FastMCP, cfg: dict) -> None:
    if not cfg:
        return

    uri_template = cfg.get("uri_template", "docs://{doc_id}")

    @mcp.resource(
        uri=uri_template,
        description=cfg.get("description", "Retrieve an enterprise document by ID."),
        mime_type=cfg.get("mime_type", "text/plain"),
    )
    async def get_document(doc_id: str) -> str:
        """
        Parameters
        ----------
        doc_id : str
            Unique document identifier, e.g. "POL-2024-07".

        Implementation note
        -------------------
        Replace the stub below with your document store call.
        """
        # ── <CONFIGURE>  replace with your document store lookup ─────────────
        content = await _fetch_document(doc_id)
        # ────────────────────────────────────────────────────────────────────
        return content


async def _fetch_document(doc_id: str) -> str:
    """Stub — replace with your document store call."""
    return f"Document '{doc_id}' content goes here.  <CONFIGURE>"
