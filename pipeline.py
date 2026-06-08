"""
transforms/pipeline.py
───────────────────────
Builds the FastMCP 3.0 Transform chain for a mounted provider.

Transforms applied (in order):
  1. PrefixTransform   — namespace all tool names (collision prevention)
  2. VersionFilter     — expose only tools at or below a version ceiling
  3. TagFilter         — hide tags that require elevated scopes by default
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_transforms(
    namespace: str,
    role_gates: dict[str, list[str]],
) -> list[Any]:
    """
    Returns an ordered list of FastMCP 3.0 Transform objects.
    Gracefully skips transforms whose classes aren't in the installed
    version of FastMCP so the codebase degrades cleanly.
    """
    transforms: list[Any] = []

    # ── 1. Namespace prefix ───────────────────────────────────
    if namespace:
        try:
            from fastmcp.server.transforms import PrefixTransform
            transforms.append(PrefixTransform(prefix=namespace))
            logger.debug("PrefixTransform added: prefix='%s'", namespace)
        except ImportError:
            logger.debug("PrefixTransform not available; skipping namespace.")

    # ── 2. Version filter — highest version only ──────────────
    try:
        from fastmcp.server.transforms import VersionFilter
        transforms.append(VersionFilter())   # defaults to "latest wins"
        logger.debug("VersionFilter added.")
    except ImportError:
        logger.debug("VersionFilter not available; skipping.")

    # ── 3. Tag-based visibility: hide privileged tools by default
    #       (revealed later via ctx.enable_components in meta_tools.py)
    gated_tags = set(role_gates.keys())
    if gated_tags:
        try:
            from fastmcp.server.transforms import TagFilter
            # Exclude gated tags from the default tool list
            transforms.append(TagFilter(exclude_tags=gated_tags))
            logger.debug("TagFilter hiding gated tags: %s", gated_tags)
        except ImportError:
            logger.debug("TagFilter not available; skipping tag-based hiding.")

    return transforms
