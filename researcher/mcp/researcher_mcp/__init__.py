"""Researcher MCP Server.

Exposes deep research operations via Gemini API as MCP tools.

Usage:
    uv run researcher-mcp
"""

from .server import main, mcp

__all__ = ["main", "mcp"]
