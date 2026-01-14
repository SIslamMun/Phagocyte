"""
Universal Document Filter

Multi-tier filtering system:
TIER 1: Filename patterns (navigation, deprecated, etc.)
TIER 2: Content quality (length, link density)
TIER 3: Structure analysis (TOC detection) - OPTIONAL

Universal across all websites/topics/languages.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class FilterResult:
    """Result of filtering a single document."""
    filepath: str
    filename: str
    keep: bool
    reason: str

    # Metrics
    line_count: int = 0
    word_count: int = 0
    link_count: int = 0
    link_ratio: float = 0.0


class UniversalFilter:
    """Basic universal filter - removes only obvious low-quality pages."""

    # ========================================================================
    # TIER 1: Filename/URL Patterns (Universal across all sites)
    # ========================================================================

    REMOVE_FILENAME_PATTERNS = [
        # Navigation/index (case-insensitive)
        r'index\.html?$',
        r'index_html\.md$',
        r'toc\.html?$',
        r'contents\.html?$',
        r'sitemap\.html?$',
        r'search\.html?$',
        r'_crawl\.html?$',
        r'_crawl_html\.md$',
        r'doxygen_crawl',
        r'_listing\.html?$',
        r'hierarchy\.html?$',
        r'namespace.*\.html?$',
        r'namespace.*_html\.md$',
        r'annotated\.html?$',
        r'files\.html?$',
        r'files_html\.md$',
        r'modules\.html?$',
        r'classes\.html?$',
        r'members.*\.html?$',
        r'globals.*\.html?$',

        # Legal/meta
        r'license\.html?$',
        r'copyright\.html?$',
        r'legal\.html?$',
        r'terms\.html?$',
        r'privacy\.html?$',
        r'404\.html?$',
        r'error\.html?$',
        r'error.*_html\.md$',

        # Deprecated
        r'deprecated\.html?$',
        r'deprecated_html\.md$',
        r'obsolete\.html?$',
        r'legacy\.html?$',

        # Downloads/releases
        r'download.*\.html?$',
        r'downloads?_latest',
        r'release.*\.html?$',
    ]

    # ========================================================================
    # TIER 2: Content Quality Thresholds
    # ========================================================================

    MIN_LINES = 30          # Pages with fewer lines likely stubs
    MIN_WORDS = 100         # Pages with fewer words likely stubs
    MAX_LINK_RATIO = 0.6    # If >60% of words are links, it's navigation
    DENSE_CONTENT_WORDS = 300  # Pages with this many words are kept regardless of line count

    # ========================================================================
    # TIER 3: Structure Analysis (Optional TOC Detection)
    # ========================================================================

    # TOC detection thresholds (disabled by default)
    TOC_LINE_LINK_PCT = 0.70        # If >70% of lines have links → TOC
    TOC_LINK_WORDS_PCT = 0.35       # If >35% of words are link text → TOC
    TOC_MAX_PARAGRAPHS = 10         # TOC pages have few paragraphs
    TOC_LIST_LINES_PCT = 0.60       # If >60% of lines are lists → TOC
    TOC_STRONG_SIGNAL_PCT = 0.80    # If >80% lines have links → definitely TOC

    def __init__(
        self,
        min_lines: int = None,
        min_words: int = None,
        max_link_ratio: float = None,
        dense_content_words: int = None,
        detect_toc: bool = False,
    ):
        """
        Initialize filter with configurable thresholds.

        Args:
            min_lines: Minimum lines (default: 30)
            min_words: Minimum words (default: 100)
            max_link_ratio: Maximum link ratio (default: 0.6)
            dense_content_words: Word count to bypass line check (default: 300)
            detect_toc: Enable TIER 3 TOC detection (default: False)
        """
        self.min_lines = min_lines if min_lines is not None else self.MIN_LINES
        self.min_words = min_words if min_words is not None else self.MIN_WORDS
        self.max_link_ratio = max_link_ratio if max_link_ratio is not None else self.MAX_LINK_RATIO
        self.dense_content_words = dense_content_words if dense_content_words is not None else self.DENSE_CONTENT_WORDS
        self.detect_toc = detect_toc

    def check_filename_patterns(self, filename: str) -> Tuple[bool, str]:
        """
        Check if filename matches removal patterns.

        Args:
            filename: Filename or path to check

        Returns:
            (should_keep, reason) - False if should be removed
        """
        filename_lower = filename.lower()

        for pattern in self.REMOVE_FILENAME_PATTERNS:
            if re.search(pattern, filename_lower, re.IGNORECASE):
                return (False, f"Filename pattern: {pattern}")

        return (True, "Filename OK")

    def analyze_content(self, content: str) -> Tuple[int, int, int, float]:
        """
        Analyze content and extract basic metrics.

        Args:
            content: Markdown content

        Returns:
            (line_count, word_count, link_count, link_ratio)
        """
        # Count non-empty lines
        lines = [l for l in content.split('\n') if l.strip()]
        line_count = len(lines)

        # Strip markdown links for word counting
        # Replace [text](url) with text
        text_only = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        # Remove images
        text_only = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', '', text_only)

        words = text_only.split()
        word_count = len(words)

        # Count links
        link_matches = re.findall(r'\]\([^\)]+\)', content)
        link_count = len(link_matches)

        # Calculate link ratio
        link_ratio = link_count / max(word_count, 1)

        return line_count, word_count, link_count, link_ratio

    def check_content_quality(
        self,
        line_count: int,
        word_count: int,
        link_ratio: float
    ) -> Tuple[bool, str]:
        """
        Check if content meets quality thresholds.

        Args:
            line_count: Number of lines
            word_count: Number of words
            link_ratio: Ratio of links to words

        Returns:
            (should_keep, reason) - False if should be removed
        """
        # PRIORITY 1: Check word count (primary quality indicator)
        if word_count < self.min_words:
            return (False, f"Too few words: {word_count} < {self.min_words}")

        # PRIORITY 2: Dense content exception
        # If page has substantial words (e.g., tables), ignore line count
        if word_count >= self.dense_content_words:
            # Still check link ratio
            if link_ratio > self.max_link_ratio:
                return (False, f"Too many links: {link_ratio:.1%} > {self.max_link_ratio:.1%}")
            return (True, f"Quality OK (dense content: {word_count} words)")

        # PRIORITY 3: Line count check (for pages with modest word counts)
        if line_count < self.min_lines:
            return (False, f"Too few lines: {line_count} < {self.min_lines}")

        # PRIORITY 4: Link ratio check
        if link_ratio > self.max_link_ratio:
            return (False, f"Too many links: {link_ratio:.1%} > {self.max_link_ratio:.1%}")

        return (True, "Quality OK")

    def check_toc_structure(self, content: str) -> Tuple[bool, str]:
        """
        Check if page is a TOC/navigation page based on structure (TIER 3).

        Universal patterns that work for ANY documentation site:
        1. High line-link density (>70% lines contain links)
        2. High link-word percentage (>35% words are link text)
        3. Low paragraph count (<10 paragraphs)
        4. High list percentage (>60% lines are lists)

        Args:
            content: Document content

        Returns:
            (should_keep, reason) - False if should be removed as TOC
        """
        if not self.detect_toc:
            return (True, "TOC detection disabled")

        lines = content.split('\n')
        lines = [l for l in lines if l.strip()]
        total_lines = len(lines)

        if total_lines == 0:
            return (True, "Empty file")

        # Count lines with links
        lines_with_links = len([l for l in lines if '](' in l])
        lines_with_links_pct = lines_with_links / total_lines

        # Count link words vs content words
        links = re.findall(r'\[([^\]]+)\]\([^\)]+\)', content)
        link_text = ' '.join([match for match in links])
        link_words = len(link_text.split())

        content_no_links = re.sub(r'\[([^\]]+)\]\([^\)]+\)', '', content)
        content_words = len(content_no_links.split())

        total_words = link_words + content_words
        link_words_pct = link_words / max(total_words, 1)

        # Count paragraphs (substantial text blocks, not lists/headers)
        paragraph_count = 0
        in_paragraph = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                in_paragraph = False
            elif re.match(r'^\s*[-*+#]', line) or '|' in line:
                in_paragraph = False
            else:
                if not in_paragraph:
                    paragraph_count += 1
                    in_paragraph = True

        # Count list lines
        list_lines = len([l for l in lines if re.match(r'^\s*[-*+]\s+', l)])
        list_lines_pct = list_lines / total_lines

        # Apply heuristics

        # Heuristic 1: Strong signal (>80% lines have links)
        if lines_with_links_pct > self.TOC_STRONG_SIGNAL_PCT:
            return (False, f"TOC: {lines_with_links_pct:.1%} lines have links")

        # Heuristic 2: Medium signal (>70% lines with links + few paragraphs)
        if lines_with_links_pct > self.TOC_LINE_LINK_PCT and paragraph_count < self.TOC_MAX_PARAGRAPHS:
            return (False, f"TOC: {lines_with_links_pct:.1%} lines with links, {paragraph_count} paragraphs")

        # Heuristic 3: Link-heavy content (>35% words are links + few paragraphs)
        if link_words_pct > self.TOC_LINK_WORDS_PCT and paragraph_count < self.TOC_MAX_PARAGRAPHS:
            return (False, f"TOC: {link_words_pct:.1%} words are link text, {paragraph_count} paragraphs")

        # Heuristic 4: List-heavy structure (>60% lists + >60% links)
        if list_lines_pct > self.TOC_LIST_LINES_PCT and lines_with_links_pct > 0.60:
            return (False, f"TOC: {list_lines_pct:.1%} list lines, {lines_with_links_pct:.1%} with links")

        return (True, "Not a TOC page")

    def filter_file(self, filepath: Path) -> FilterResult:
        """
        Filter a single markdown file.

        Args:
            filepath: Path to markdown file

        Returns:
            FilterResult with decision and metrics
        """
        filename = filepath.name

        # TIER 1: Check filename patterns
        keep1, reason1 = self.check_filename_patterns(filename)
        if not keep1:
            return FilterResult(
                filepath=str(filepath),
                filename=filename,
                keep=False,
                reason=f"[TIER1] {reason1}",
            )

        # Read content
        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            return FilterResult(
                filepath=str(filepath),
                filename=filename,
                keep=False,
                reason=f"[ERROR] Cannot read file: {e}",
            )

        # TIER 2: Analyze content
        line_count, word_count, link_count, link_ratio = self.analyze_content(content)

        keep2, reason2 = self.check_content_quality(line_count, word_count, link_ratio)
        if not keep2:
            return FilterResult(
                filepath=str(filepath),
                filename=filename,
                keep=False,
                reason=f"[TIER2] {reason2}",
                line_count=line_count,
                word_count=word_count,
                link_count=link_count,
                link_ratio=link_ratio,
            )

        # TIER 3: Check TOC structure (if enabled)
        keep3, reason3 = self.check_toc_structure(content)
        if not keep3:
            return FilterResult(
                filepath=str(filepath),
                filename=filename,
                keep=False,
                reason=f"[TIER3] {reason3}",
                line_count=line_count,
                word_count=word_count,
                link_count=link_count,
                link_ratio=link_ratio,
            )

        # Keep the file
        return FilterResult(
            filepath=str(filepath),
            filename=filename,
            keep=True,
            reason="Quality document",
            line_count=line_count,
            word_count=word_count,
            link_count=link_count,
            link_ratio=link_ratio,
        )

    def filter_directory(
        self,
        directory: Path,
        pattern: str = "*.md",
    ) -> Dict[str, FilterResult]:
        """
        Filter all markdown files in a directory.

        Args:
            directory: Directory to scan
            pattern: File pattern (default: *.md)

        Returns:
            Dict mapping filepath to FilterResult
        """
        results = {}

        for filepath in directory.rglob(pattern):
            if filepath.is_file():
                result = self.filter_file(filepath)
                results[str(filepath)] = result

        return results

    def generate_report(self, results: Dict[str, FilterResult]) -> str:
        """
        Generate a text report of filtering results.

        Args:
            results: Dict of filepath to FilterResult

        Returns:
            Formatted report string
        """
        total = len(results)
        kept = sum(1 for r in results.values() if r.keep)
        removed = total - kept

        lines = [
            "=" * 80,
            "Universal Filter Report - Basic Quality Check",
            "=" * 80,
            f"Total files: {total}",
            f"Kept: {kept} ({kept/total*100:.1f}%)",
            f"Removed: {removed} ({removed/total*100:.1f}%)",
            "",
            "Removal breakdown by reason:",
            "-" * 80,
        ]

        # Count reasons
        reason_counts: Dict[str, int] = {}
        for result in results.values():
            if not result.keep:
                # Extract the tier and basic reason
                reason = result.reason.split(':')[0] if ':' in result.reason else result.reason
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

        for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"  {reason}: {count} files")

        # Statistics
        lines.extend([
            "",
            "Average metrics (for all files):",
            "-" * 80,
        ])

        all_results = list(results.values())
        results_with_metrics = [r for r in all_results if r.line_count > 0]

        if results_with_metrics:
            avg_lines = sum(r.line_count for r in results_with_metrics) / len(results_with_metrics)
            avg_words = sum(r.word_count for r in results_with_metrics) / len(results_with_metrics)
            avg_links = sum(r.link_count for r in results_with_metrics) / len(results_with_metrics)
            avg_link_ratio = sum(r.link_ratio for r in results_with_metrics) / len(results_with_metrics)

            lines.extend([
                f"  Average lines: {avg_lines:.1f}",
                f"  Average words: {avg_words:.1f}",
                f"  Average links: {avg_links:.1f}",
                f"  Average link ratio: {avg_link_ratio:.1%}",
            ])

        lines.append("=" * 80)

        return "\n".join(lines)
