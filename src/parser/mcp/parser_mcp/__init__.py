"""Parser MCP Server.

Exposes paper acquisition, reference parsing, and DOI operations as MCP tools.

Usage:
    uv run parser-mcp
"""

from .server import main, mcp

__all__ = ["main", "mcp"]
