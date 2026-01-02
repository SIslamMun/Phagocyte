#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""
Phagocyte Pipeline Orchestrator

Automates the full pipeline: Research → Parse → Acquire → Ingest → Process

Usage:
    uv run phagocyte.py "Your research topic" -a "https://artifact1.com" -a "https://artifact2.com" -o ./output
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


class PipelineFailed(Exception):
    """Raised when a pipeline step fails."""
    pass


def run_command(cmd: list[str], cwd: Path, description: str, log_file: Path | None = None) -> tuple[int, str]:
    """Run a command and return exit code and output."""
    print(f"\n{'='*60}")
    print(f"📌 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print(f"Directory: {cwd}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        output = result.stdout + result.stderr
        print(output)
        
        if log_file:
            with open(log_file, 'w') as f:
                f.write(f"Command: {' '.join(cmd)}\n")
                f.write(f"Exit Code: {result.returncode}\n")
                f.write(f"Output:\n{output}")
        
        return result.returncode, output
        
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out after 30 minutes")
        return 1, "Timeout"
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1, str(e)


def main():
    parser = argparse.ArgumentParser(
        description="Phagocyte Pipeline - Research → Parse → Ingest → Process",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python phagocyte.py "HDF5 file format best practices"
  
  # With artifacts
  python phagocyte.py "HDF5 architecture" -a "https://support.hdfgroup.org/documentation/" -a "https://github.com/HDFGroup/hdf5"
  
  # Custom output directory
  python phagocyte.py "Machine learning optimization" -o ./ml_research
  
  # Skip certain phases
  python phagocyte.py "Topic" --skip-research --skip-acquisition
        """
    )
    
    parser.add_argument("topic", help="Research topic")
    parser.add_argument("-a", "--artifact", action="append", dest="artifacts", 
                        help="Artifact URLs (can specify multiple)")
    parser.add_argument("-o", "--output", default="./pipeline_output",
                        help="Output directory (default: ./pipeline_output)")
    parser.add_argument("--skip-research", action="store_true",
                        help="Skip research phase (use existing research)")
    parser.add_argument("--skip-acquisition", action="store_true",
                        help="Skip paper acquisition")
    parser.add_argument("--skip-web", action="store_true",
                        help="Skip web crawling")
    parser.add_argument("--skip-github", action="store_true",
                        help="Skip GitHub ingestion")
    parser.add_argument("--max-pages", type=int, default=40,
                        help="Max web pages to crawl (default: 40)")
    parser.add_argument("--max-depth", type=int, default=2,
                        help="Web crawl depth (default: 2)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")
    
    args = parser.parse_args()
    
    # Setup paths
    root_dir = Path(__file__).parent.resolve()
    output_dir = Path(args.output).resolve()
    
    researcher_dir = root_dir / "researcher"
    parser_dir = root_dir / "parser"
    ingestor_dir = root_dir / "ingestor"
    processor_dir = root_dir / "processor"
    
    # Validate modules exist
    for module_dir in [researcher_dir, parser_dir, ingestor_dir, processor_dir]:
        if not module_dir.exists():
            print(f"❌ Module not found: {module_dir}")
            sys.exit(1)
    
    # Create output directories
    phase1_dir = output_dir / "phase1_research"
    phase2_dir = output_dir / "phase2_parser"
    phase3_dir = output_dir / "phase3_ingestor"
    phase4_dir = output_dir / "phase4_processor"
    
    for d in [phase1_dir, phase2_dir, phase3_dir, phase4_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    start_time = datetime.now()
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    PHAGOCYTE PIPELINE                        ║
╠══════════════════════════════════════════════════════════════╣
║  Topic: {args.topic[:50]:<52} ║
║  Output: {str(output_dir)[:51]:<51} ║
║  Started: {start_time.strftime('%Y-%m-%d %H:%M:%S'):<50} ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    errors = []
    
    # =========================================================================
    # PHASE 1: RESEARCH
    # =========================================================================
    if not args.skip_research:
        print("\n" + "🔬 PHASE 1: RESEARCH ".ljust(60, "="))
        
        # Build command
        cmd = [
            "uv", "run", "researcher", "research",
            args.topic,
            "--mode", "directed",
            "-o", str(phase1_dir)
        ]
        
        if args.artifacts:
            for artifact in args.artifacts:
                cmd.extend(["-a", artifact])
        
        if args.verbose:
            cmd.append("-v")
        
        # Unset GOOGLE_API_KEY if set (use .env instead)
        env = os.environ.copy()
        
        code, _ = run_command(
            cmd, researcher_dir,
            "Running Gemini Deep Research",
            phase1_dir / "execution.log"
        )
        
        if code != 0:
            errors.append(("Phase 1: Research", "Research failed"))
            print("⚠️ Research failed, but continuing...")
    else:
        print("\n⏭️ Skipping Phase 1: Research")
    
    # Find research report
    research_report = phase1_dir / "research" / "research_report.md"
    if not research_report.exists():
        # Try alternative location
        research_report = phase1_dir / "research_report.md"
    
    if not research_report.exists():
        print(f"❌ Research report not found at {research_report}")
        if not args.skip_research:
            sys.exit(1)
    
    # =========================================================================
    # PHASE 2: PARSER
    # =========================================================================
    print("\n" + "📚 PHASE 2: PARSER ".ljust(60, "="))
    
    # Step 2.1: Parse references (regular)
    step1_dir = phase2_dir / "step1_regular"
    step1_dir.mkdir(exist_ok=True)
    
    cmd = [
        "uv", "run", "parser", "parse-refs",
        str(research_report),
        "-o", str(step1_dir),
        "--format", "both",
        "--export-batch",
        "--export-dois"
    ]
    
    code, _ = run_command(
        cmd, parser_dir,
        "Parsing references (regex)",
        step1_dir / "execution.log"
    )
    
    # Step 2.2: Parse with agent
    step2_dir = phase2_dir / "step2_agent"
    step2_dir.mkdir(exist_ok=True)
    
    cmd = [
        "uv", "run", "parser", "parse-refs",
        str(research_report),
        "-o", str(step2_dir),
        "--agent", "claude",
        "--format", "both",
        "--export-batch",
        "--export-dois"
    ]
    
    run_command(
        cmd, parser_dir,
        "Parsing references (Claude agent)",
        step2_dir / "execution.log"
    )
    
    # Step 2.3: Acquisition
    if not args.skip_acquisition:
        step4_dir = phase2_dir / "step3_acquisition"
        step4_dir.mkdir(exist_ok=True)
        papers_dir = step4_dir / "papers"
        papers_dir.mkdir(exist_ok=True)
        
        batch_file = step1_dir / "batch.json"
        if batch_file.exists():
            cmd = [
                "uv", "run", "parser", "batch",
                str(batch_file),
                "-o", str(papers_dir),
                "-v"
            ]
            
            run_command(
                cmd, parser_dir,
                "Acquiring papers",
                step4_dir / "execution.log"
            )
    else:
        print("\n⏭️ Skipping paper acquisition")
        papers_dir = phase2_dir / "step3_acquisition" / "papers"
    
    # Step 2.4: DOI to BibTeX
    step5_dir = phase2_dir / "step4_doi2bib"
    step5_dir.mkdir(exist_ok=True)
    
    dois_file = step1_dir / "dois.txt"
    if dois_file.exists():
        cmd = [
            "uv", "run", "parser", "doi2bib",
            "-i", str(dois_file),
            "-o", str(step5_dir / "references.bib")
        ]
        
        run_command(
            cmd, parser_dir,
            "Converting DOIs to BibTeX",
            step5_dir / "execution.log"
        )
    
    # =========================================================================
    # PHASE 3: INGESTOR
    # =========================================================================
    print("\n" + "📄 PHASE 3: INGESTOR ".ljust(60, "="))
    
    # Step 3.1: PDF ingestion
    pdfs_dir = phase3_dir / "pdfs"
    pdfs_dir.mkdir(exist_ok=True)
    
    if papers_dir.exists() and any(papers_dir.glob("*.pdf")):
        cmd = [
            "uv", "run", "ingestor", "batch",
            str(papers_dir),
            "-o", str(pdfs_dir),
            "--recursive",
            "-v"
        ]
        
        run_command(
            cmd, ingestor_dir,
            "Ingesting PDFs",
            phase3_dir / "pdfs_execution.log"
        )
    else:
        print("⚠️ No PDFs found to ingest")
    
    # Step 3.2: GitHub ingestion
    if not args.skip_github and args.artifacts:
        github_dir = phase3_dir / "github"
        github_dir.mkdir(exist_ok=True)
        
        for artifact in args.artifacts:
            if "github.com" in artifact:
                cmd = [
                    "uv", "run", "ingestor", "ingest",
                    artifact,
                    "-o", str(github_dir),
                    "-v"
                ]
                
                run_command(
                    cmd, ingestor_dir,
                    f"Ingesting GitHub: {artifact}",
                    phase3_dir / "github_execution.log"
                )
    
    # Step 3.3: Web crawling
    if not args.skip_web and args.artifacts:
        web_dir = phase3_dir / "web"
        web_dir.mkdir(exist_ok=True)
        
        for artifact in args.artifacts:
            if "github.com" not in artifact:
                cmd = [
                    "uv", "run", "ingestor", "crawl",
                    artifact,
                    "-o", str(web_dir),
                    "--max-depth", str(args.max_depth),
                    "--max-pages", str(args.max_pages),
                    "-v"
                ]
                
                run_command(
                    cmd, ingestor_dir,
                    f"Crawling: {artifact}",
                    phase3_dir / "web_execution.log"
                )
    
    # =========================================================================
    # PHASE 4: PROCESSOR
    # =========================================================================
    print("\n" + "🔮 PHASE 4: PROCESSOR ".ljust(60, "="))
    
    # Prepare input directory
    input_dir = phase4_dir / "input"
    input_dir.mkdir(exist_ok=True)
    
    # Copy research
    research_input = input_dir / "research"
    research_input.mkdir(exist_ok=True)
    if research_report.exists():
        shutil.copy(research_report, research_input)
    thinking_steps = phase1_dir / "research" / "thinking_steps.md"
    if thinking_steps.exists():
        shutil.copy(thinking_steps, research_input)
    
    # Copy papers
    papers_input = input_dir / "papers"
    papers_input.mkdir(exist_ok=True)
    for md_file in pdfs_dir.rglob("*.md"):
        shutil.copy(md_file, papers_input)
    
    # Copy websites
    websites_input = input_dir / "websites"
    websites_input.mkdir(exist_ok=True)
    web_source = phase3_dir / "web"
    if web_source.exists():
        for md_file in web_source.rglob("*.md"):
            shutil.copy(md_file, websites_input)
    
    # Copy codebases
    codebases_input = input_dir / "codebases"
    codebases_input.mkdir(exist_ok=True)
    github_source = phase3_dir / "github"
    if github_source.exists():
        for item in github_source.iterdir():
            if item.is_dir():
                shutil.copytree(item, codebases_input / item.name, dirs_exist_ok=True)
    
    # Process into LanceDB
    lancedb_dir = phase4_dir / "lancedb"
    
    cmd = [
        "uv", "run", "processor", "process",
        str(input_dir),
        "-o", str(lancedb_dir),
        "--text-profile", "low",
        "--code-profile", "low",
        "--table-mode", "separate",
        "--full"
    ]
    
    run_command(
        cmd, processor_dir,
        "Processing documents into LanceDB",
        phase4_dir / "process_execution.log"
    )
    
    # Show stats
    cmd = ["uv", "run", "processor", "stats", str(lancedb_dir)]
    run_command(cmd, processor_dir, "Database statistics", None)
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    end_time = datetime.now()
    duration = end_time - start_time
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    PIPELINE COMPLETE                         ║
╠══════════════════════════════════════════════════════════════╣
║  Duration: {str(duration).split('.')[0]:<49} ║
║  Output: {str(output_dir)[:51]:<51} ║
╠══════════════════════════════════════════════════════════════╣
║  Phase 1: Research report generated                          ║
║  Phase 2: References parsed and papers acquired              ║
║  Phase 3: Documents converted to markdown                    ║
║  Phase 4: Vector database created in LanceDB                 ║
╚══════════════════════════════════════════════════════════════╝

To search the knowledge base:
  cd processor && uv run processor search {lancedb_dir} "your query" -k 5
    """)
    
    if errors:
        print("\n⚠️ Warnings/Errors encountered:")
        for phase, msg in errors:
            print(f"  - {phase}: {msg}")
    
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
