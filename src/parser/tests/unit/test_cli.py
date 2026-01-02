"""Unit tests for parser CLI."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from parser.cli import cli


class TestCLI:
    """Test CLI commands."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_cli_help(self, runner: CliRunner) -> None:
        """Test CLI help output."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "parse-refs" in result.output or "parser" in result.output.lower()

    def test_parse_refs_command_help(self, runner: CliRunner) -> None:
        """Test parse-refs command help."""
        result = runner.invoke(cli, ["parse-refs", "--help"])
        assert result.exit_code == 0

    def test_retrieve_command_help(self, runner: CliRunner) -> None:
        """Test retrieve command help."""
        result = runner.invoke(cli, ["retrieve", "--help"])
        assert result.exit_code == 0

    def test_doi2bib_command_help(self, runner: CliRunner) -> None:
        """Test doi2bib command help."""
        result = runner.invoke(cli, ["doi2bib", "--help"])
        assert result.exit_code == 0

    def test_verify_command_help(self, runner: CliRunner) -> None:
        """Test verify command help."""
        result = runner.invoke(cli, ["verify", "--help"])
        assert result.exit_code == 0

    def test_batch_command_help(self, runner: CliRunner) -> None:
        """Test batch command help."""
        result = runner.invoke(cli, ["batch", "--help"])
        assert result.exit_code == 0

    def test_sources_command_help(self, runner: CliRunner) -> None:
        """Test sources command help."""
        result = runner.invoke(cli, ["sources", "--help"])
        assert result.exit_code == 0


class TestParseRefsCommand:
    """Test parse-refs command."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_parse_refs_requires_file(self, runner: CliRunner) -> None:
        """Test parse-refs command requires file argument."""
        result = runner.invoke(cli, ["parse-refs"])
        # Should fail or show usage
        assert result.exit_code != 0 or "Usage" in result.output

    def test_parse_refs_with_file(
        self, runner: CliRunner, tmp_path: Path, sample_research_text: str
    ) -> None:
        """Test parse-refs command with file."""
        md_file = tmp_path / "research.md"
        md_file.write_text(sample_research_text)

        result = runner.invoke(cli, ["parse-refs", str(md_file)])
