"""Unit tests for researcher CLI."""

import pytest
from click.testing import CliRunner

from researcher.cli import cli


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
        assert "research" in result.output.lower() or "gemini" in result.output.lower()

    def test_cli_version(self, runner: CliRunner) -> None:
        """Test CLI version output."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_research_command_help(self, runner: CliRunner) -> None:
        """Test research command help."""
        result = runner.invoke(cli, ["research", "--help"])
        assert result.exit_code == 0
        assert "QUERY" in result.output

    def test_research_requires_topic(self, runner: CliRunner) -> None:
        """Test that research command requires topic."""
        result = runner.invoke(cli, ["research"])
        # Should fail without topic argument
        assert result.exit_code != 0 or "Usage" in result.output

    def test_research_modes(self, runner: CliRunner) -> None:
        """Test research mode options are available."""
        result = runner.invoke(cli, ["research", "--help"])
        assert "undirected" in result.output or "mode" in result.output.lower()

    def test_research_output_option(self, runner: CliRunner) -> None:
        """Test research output option is available."""
        result = runner.invoke(cli, ["research", "--help"])
        assert "--output" in result.output or "-o" in result.output

    def test_research_artifact_option(self, runner: CliRunner) -> None:
        """Test research artifact option is available."""
        result = runner.invoke(cli, ["research", "--help"])
        assert "--artifact" in result.output or "-a" in result.output


class TestCLIOutput:
    """Test CLI output formatting."""

    @pytest.fixture
    def runner(self) -> CliRunner:
        """Create CLI test runner."""
        return CliRunner()

    def test_help_contains_description(self, runner: CliRunner) -> None:
        """Test help contains module description."""
        result = runner.invoke(cli, ["--help"])
        # Should mention research or Gemini
        assert "research" in result.output.lower() or "gemini" in result.output.lower()
