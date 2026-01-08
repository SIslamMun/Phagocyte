"""Adapters wrapping LlamaIndex chunkers with tree-sitter AST parsing."""

from pathlib import Path
from typing import Any

from llama_index.core import Document
from llama_index.core.node_parser import CodeSplitter, MarkdownNodeParser

from ..types import Chunk, ContentType
from .base import BaseChunker


class LlamaIndexCodeAdapter(BaseChunker):
    """Uses LlamaIndex CodeSplitter with tree-sitter for true AST-based chunking.

    This provides semantic code chunking that:
    - Respects function/class/method boundaries
    - Never splits mid-statement
    - Preserves docstrings with their functions
    - Supports 165+ languages via tree-sitter
    """

    content_types = [
        ContentType.CODE_CPP,
        ContentType.CODE_PYTHON,
        ContentType.CODE_SHELL,
        ContentType.CODE_JAVA,
        ContentType.CODE_JS,
        ContentType.CODE_TS,
        ContentType.CODE_GO,
        ContentType.CODE_RUST,
        ContentType.CODE_OTHER,
    ]

    # Map file extensions to tree-sitter language names
    LANGUAGE_MAP: dict[str, str] = {
        # Python
        ".py": "python",
        ".pyw": "python",
        ".pyi": "python",
        # JavaScript/TypeScript
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        # Systems languages
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".hxx": "cpp",
        ".rs": "rust",
        ".go": "go",
        # JVM languages
        ".java": "java",
        ".kt": "kotlin",
        ".scala": "scala",
        # Other
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".cs": "c_sharp",
        ".lua": "lua",
        ".pl": "perl",
        ".hs": "haskell",
        ".ex": "elixir",
        ".exs": "elixir",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
    }

    # Default chunking parameters optimized for code
    default_chunk_lines = 40
    default_chunk_overlap_lines = 15
    default_max_chars = 4000  # ~1024 tokens

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        chunk_lines: int | None = None,
        chunk_overlap_lines: int | None = None,
    ):
        """Initialize code chunker.

        Args:
            chunk_size: Max characters per chunk (overrides default_max_chars)
            chunk_overlap: Not used for CodeSplitter (uses lines instead)
            chunk_lines: Target lines per chunk
            chunk_overlap_lines: Overlap lines between chunks
        """
        super().__init__(chunk_size, chunk_overlap)
        self.chunk_lines = chunk_lines or self.default_chunk_lines
        self.chunk_overlap_lines = chunk_overlap_lines or self.default_chunk_overlap_lines
        self.max_chars = chunk_size or self.default_max_chars

    def chunk(
        self,
        content: str,
        source_file: Path,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Chunk code using AST-based splitting via tree-sitter.

        Args:
            content: Source code content
            source_file: Path to source file
            metadata: Optional additional metadata

        Returns:
            List of Chunk objects with semantically coherent code
        """
        ext = source_file.suffix.lower()
        language = self.LANGUAGE_MAP.get(ext, "python")

        try:
            # Create AST-based splitter
            splitter = CodeSplitter(
                language=language,
                chunk_lines=self.chunk_lines,
                chunk_lines_overlap=self.chunk_overlap_lines,
                max_chars=self.max_chars,
            )

            # Create LlamaIndex document
            doc = Document(text=content, metadata={"source": str(source_file)})

            # Get AST-based nodes
            nodes = splitter.get_nodes_from_documents([doc])

            # Convert to our Chunk type
            chunks = []
            for _i, node in enumerate(nodes):
                content_type = self._get_content_type(ext)

                chunk = Chunk.create(
                    content=node.get_content(),
                    source_file=source_file,
                    source_type=content_type,
                    language=language,
                    **(metadata or {}),
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            # Fallback to simple splitting if tree-sitter fails for this language
            return self._fallback_chunk(content, source_file, metadata, str(e))

    def _fallback_chunk(
        self,
        content: str,
        source_file: Path,
        metadata: dict[str, Any] | None,
        error: str,
    ) -> list[Chunk]:
        """Fallback chunking when tree-sitter parsing fails."""
        # Simple line-based splitting
        lines = content.split("\n")
        chunks = []
        current_chunk_lines: list[str] = []
        current_size = 0

        for line in lines:
            line_size = len(line) + 1  # +1 for newline
            if current_size + line_size > self.max_chars and current_chunk_lines:
                # Save current chunk
                chunk_content = "\n".join(current_chunk_lines)
                chunk = Chunk.create(
                    content=chunk_content,
                    source_file=source_file,
                    source_type=self._get_content_type(source_file.suffix.lower()),
                    language=source_file.suffix.lstrip("."),
                    **(metadata or {}),
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                overlap_lines = current_chunk_lines[-self.chunk_overlap_lines:]
                current_chunk_lines = overlap_lines
                current_size = sum(len(line) + 1 for line in current_chunk_lines)

            current_chunk_lines.append(line)
            current_size += line_size

        # Save remaining content
        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines)
            chunk = Chunk.create(
                content=chunk_content,
                source_file=source_file,
                source_type=self._get_content_type(source_file.suffix.lower()),
                language=source_file.suffix.lstrip("."),
                **(metadata or {}),
            )
            chunks.append(chunk)

        return chunks

    def _get_content_type(self, ext: str) -> ContentType:
        """Get ContentType from file extension."""
        ext_map = {
            ".cpp": ContentType.CODE_CPP,
            ".cc": ContentType.CODE_CPP,
            ".c": ContentType.CODE_CPP,
            ".h": ContentType.CODE_CPP,
            ".hpp": ContentType.CODE_CPP,
            ".py": ContentType.CODE_PYTHON,
            ".pyw": ContentType.CODE_PYTHON,
            ".sh": ContentType.CODE_SHELL,
            ".bash": ContentType.CODE_SHELL,
            ".java": ContentType.CODE_JAVA,
            ".js": ContentType.CODE_JS,
            ".ts": ContentType.CODE_TS,
            ".go": ContentType.CODE_GO,
            ".rs": ContentType.CODE_RUST,
        }
        return ext_map.get(ext, ContentType.CODE_OTHER)

    def supports(self, content_type: ContentType) -> bool:
        return content_type in self.content_types


class MarkdownCodeBlockExtractor(BaseChunker):
    """Extracts fenced code blocks from markdown as separate code chunks.

    This chunker finds all fenced code blocks (```language ... ```) in markdown
    documents and creates code chunks with appropriate language metadata.
    This is essential for processing GitHub repo markdown that contains
    embedded source code.
    """

    # Language aliases to normalize
    LANGUAGE_ALIASES: dict[str, str] = {
        "py": "python",
        "python3": "python",
        "js": "javascript",
        "ts": "typescript",
        "sh": "bash",
        "shell": "bash",
        "zsh": "bash",
        "c++": "cpp",
        "cxx": "cpp",
        "rs": "rust",
        "rb": "ruby",
        "yml": "yaml",
        "dockerfile": "docker",
    }

    # Map languages to ContentType
    LANGUAGE_TO_CONTENT_TYPE: dict[str, ContentType] = {
        "python": ContentType.CODE_PYTHON,
        "javascript": ContentType.CODE_JS,
        "typescript": ContentType.CODE_TS,
        "java": ContentType.CODE_JAVA,
        "cpp": ContentType.CODE_CPP,
        "c": ContentType.CODE_CPP,
        "go": ContentType.CODE_GO,
        "rust": ContentType.CODE_RUST,
        "bash": ContentType.CODE_SHELL,
        "shell": ContentType.CODE_SHELL,
    }

    # Minimum code block size to include (skip tiny snippets)
    MIN_CODE_BLOCK_SIZE = 50  # characters

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        min_block_size: int | None = None,
    ):
        """Initialize code block extractor.

        Args:
            chunk_size: Max characters per chunk
            chunk_overlap: Not used for this chunker
            min_block_size: Minimum code block size to include
        """
        super().__init__(chunk_size, chunk_overlap)
        self.min_block_size = min_block_size or self.MIN_CODE_BLOCK_SIZE

    def chunk(
        self,
        content: str,
        source_file: Path,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Extract fenced code blocks from markdown content.

        Args:
            content: Markdown content with fenced code blocks
            source_file: Path to source file
            metadata: Optional additional metadata

        Returns:
            List of Chunk objects for each code block
        """
        import re

        chunks = []

        # Pattern to match fenced code blocks with optional language
        # Handles both ``` and ~~~ style fences
        code_block_pattern = re.compile(
            r'^(?P<fence>`{3,}|~{3,})(?P<lang>\w*)\s*\n'
            r'(?P<code>.*?)'
            r'^(?P=fence)\s*$',
            re.MULTILINE | re.DOTALL
        )

        # Also extract file path hints from markdown headers like ### `path/to/file.py`
        file_path_pattern = re.compile(r'^#{1,6}\s+`([^`]+)`\s*$', re.MULTILINE)

        # Track current file path context from headers
        current_file_path: str | None = None
        last_header_pos = 0

        # Find all file path headers
        file_path_headers = {m.start(): m.group(1) for m in file_path_pattern.finditer(content)}

        for match in code_block_pattern.finditer(content):
            code = match.group('code').strip()
            lang = match.group('lang').lower() if match.group('lang') else ""

            # Skip small code blocks (likely examples, not actual source)
            if len(code) < self.min_block_size:
                continue

            # Normalize language
            lang = self.LANGUAGE_ALIASES.get(lang, lang)

            # Skip non-code blocks (like output, logs, etc.)
            if lang in {'', 'text', 'output', 'log', 'console', 'plaintext', 'txt'}:
                continue

            # Find the most recent file path header before this code block
            block_start = match.start()
            for header_pos in sorted(file_path_headers.keys(), reverse=True):
                if header_pos < block_start:
                    current_file_path = file_path_headers[header_pos]
                    break

            # Determine content type
            content_type = self.LANGUAGE_TO_CONTENT_TYPE.get(lang, ContentType.CODE_OTHER)

            # Calculate approximate line numbers in original markdown
            lines_before = content[:match.start()].count('\n')
            code_lines = code.count('\n') + 1

            # Use title field to store original file path if available
            title = current_file_path if current_file_path else None

            chunk = Chunk.create(
                content=code,
                source_file=source_file,
                source_type=content_type,
                language=lang,
                title=title,
                start_line=lines_before + 1,
                end_line=lines_before + code_lines,
                **(metadata or {}),
            )
            chunks.append(chunk)

        return chunks

    def supports(self, content_type: ContentType) -> bool:
        """This chunker works on markdown content."""
        return content_type in [ContentType.MARKDOWN, ContentType.WEBSITE, ContentType.TEXT]


class LlamaIndexMarkdownAdapter(BaseChunker):
    """Uses LlamaIndex's MarkdownNodeParser for markdown and paper documents.

    Provides header-hierarchy aware splitting that respects markdown structure.
    Now also used for papers since they come from the ingestor with proper structure.
    """

    content_types = [
        ContentType.MARKDOWN,
        ContentType.WEBSITE,
        ContentType.BOOK,
        ContentType.YOUTUBE,
        ContentType.PAPER,
        ContentType.TEXT,
    ]

    default_chunk_size = 4000  # ~1024 tokens
    default_chunk_overlap = 500  # ~128 tokens

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        extract_code_blocks: bool = True,
    ):
        """Initialize markdown chunker.

        Args:
            chunk_size: Max characters per chunk
            chunk_overlap: Overlap between chunks
            extract_code_blocks: Also extract fenced code blocks as separate code chunks
        """
        super().__init__(chunk_size, chunk_overlap)
        self.extract_code_blocks = extract_code_blocks
        self._code_extractor = MarkdownCodeBlockExtractor() if extract_code_blocks else None

    def chunk(
        self,
        content: str,
        source_file: Path,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Chunk markdown/paper using header-based splitting.

        Also extracts fenced code blocks as separate code chunks if extract_code_blocks=True.
        """
        chunks = []

        # First, extract code blocks as separate code chunks
        if self.extract_code_blocks and self._code_extractor:
            code_chunks = self._code_extractor.chunk(content, source_file, metadata)
            chunks.extend(code_chunks)

        # Then, process the text content (including code blocks as text for context)
        try:
            # Create LlamaIndex document
            doc = Document(text=content, metadata={"source": str(source_file)})

            # Parse with markdown-aware parser
            parser = MarkdownNodeParser()
            nodes = parser.get_nodes_from_documents([doc])

            for _i, node in enumerate(nodes):
                # Extract section path from metadata if available
                section_path = None
                if hasattr(node, "metadata"):
                    headers = []
                    for key in ["Header_1", "Header_2", "Header_3"]:
                        if key in node.metadata:
                            headers.append(node.metadata[key])
                    if headers:
                        section_path = " > ".join(headers)

                # Extract citations for papers
                citations = []
                node_content = node.get_content()
                if self._get_content_type(source_file) == ContentType.PAPER:
                    citations = self._extract_citations(node_content)

                chunk = Chunk.create(
                    content=node_content,
                    source_file=source_file,
                    source_type=self._get_content_type(source_file),
                    section_path=section_path,
                    citations=citations if citations else None,
                    **(metadata or {}),
                )
                chunks.append(chunk)

            return chunks

        except ImportError:
            # Fallback to simple markdown splitting if LlamaIndex not available
            text_chunks = self._fallback_chunk(content, source_file, metadata)
            chunks.extend(text_chunks)
            return chunks

    def _extract_citations(self, text: str) -> list[str]:
        """Extract citation references from text."""
        import re

        # Match common citation patterns: [1], [ref-1], [[1]], etc.
        patterns = [
            r"\[(\d+)\]",  # [1]
            r"\[\[(\d+)\]\]",  # [[1]]
            r"\[ref-(\d+)\]",  # [ref-1]
        ]

        citations = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            citations.update(matches)

        return sorted(list(citations), key=lambda x: int(x) if x.isdigit() else x)

    def _fallback_chunk(
        self,
        content: str,
        source_file: Path,
        metadata: dict[str, Any] | None = None,
    ) -> list[Chunk]:
        """Fallback to header-based splitting without LlamaIndex."""
        import re

        # Split on headers
        header_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

        sections = []
        last_end = 0
        current_path: list[str] = []

        for match in header_pattern.finditer(content):
            # Save content before this header
            if last_end < match.start():
                section_text = content[last_end : match.start()].strip()
                if section_text:
                    sections.append(
                        {
                            "content": section_text,
                            "path": " > ".join(current_path) if current_path else None,
                        }
                    )

            # Update path based on header level
            level = len(match.group(1))
            title = match.group(2).strip()

            # Trim path to current level
            current_path = current_path[: level - 1]
            current_path.append(title)

            last_end = match.end()

        # Add remaining content
        if last_end < len(content):
            section_content = content[last_end:].strip()
            if section_content:
                sections.append(
                    {
                        "content": section_content,
                        "path": " > ".join(current_path) if current_path else None,
                    }
                )

        # Convert sections to chunks
        chunks = []
        for section in sections:
            section_text_content: str = section["content"] or ""

            # Further split if section is too large
            if len(section_text_content) > self.chunk_size:
                # Simple character-based splitting for oversized sections
                for i in range(0, len(section_text_content), self.chunk_size - self.chunk_overlap):
                    sub_content = section_text_content[i:i + self.chunk_size]
                    chunk = Chunk.create(
                        content=sub_content,
                        source_file=source_file,
                        source_type=self._get_content_type(source_file),
                        section_path=section["path"],
                        **(metadata or {}),
                    )
                    chunks.append(chunk)
            else:
                chunk = Chunk.create(
                    content=section_text_content,
                    source_file=source_file,
                    source_type=self._get_content_type(source_file),
                    section_path=section["path"],
                    **(metadata or {}),
                )
                chunks.append(chunk)

        return chunks

    def _get_content_type(self, source_file: Path) -> ContentType:
        """Determine content type from file path."""
        path_str = str(source_file).lower()
        if "paper" in path_str:
            return ContentType.PAPER
        elif "website" in path_str:
            return ContentType.WEBSITE
        elif "book" in path_str:
            return ContentType.BOOK
        elif "youtube" in path_str:
            return ContentType.YOUTUBE
        return ContentType.MARKDOWN

    def supports(self, content_type: ContentType) -> bool:
        return content_type in self.content_types
