"""Ingestor MCP Server.

Exposes document ingestion and media conversion operations as MCP tools.

Usage:
    uv run ingestor-mcp
"""

from .server import main, mcp

__all__ = ["main", "mcp"]
