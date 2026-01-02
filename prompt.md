# MCP Test Prompts

## Test Individual MCP Servers

### Researcher MCP
```
Use the researcher MCP to research "parallel I/O optimization" and save to ./test_mcp/research
```

### Parser MCP
```
Use the parser MCP to extract references from ./pipeline_output/phase1_research/research/research_report.md
```

### Ingestor MCP
```
Use the ingestor MCP to convert a PDF to markdown from ./pipeline_output/phase3_ingestor/pdfs/
```

### Processor MCP
```
Use the processor MCP to show stats for the database at ./pipeline_output/phase4_processor/lancedb
```

### RAG MCP
```
Use the rag MCP to search for "HDF5 parallel I/O" in the database at ./pipeline_output/phase4_processor/lancedb
```

---

## Quick All-in-One Test

```
List all available tools from the researcher, parser, ingestor, processor, and rag MCP servers
```

---

## MCP Server Commands

### Add MCP Servers
```bash
claude mcp add ingestor -- uv --directory /home/shazzadul/Illinois_Tech/Spring26/RA/Github/new/Phagocyte/src/ingestor run ingestor-mcp
claude mcp add parser -- uv --directory /home/shazzadul/Illinois_Tech/Spring26/RA/Github/new/Phagocyte/src/parser run parser-mcp
claude mcp add researcher -- uv --directory /home/shazzadul/Illinois_Tech/Spring26/RA/Github/new/Phagocyte/src/researcher run researcher-mcp
claude mcp add processor -- uv --directory /home/shazzadul/Illinois_Tech/Spring26/RA/Github/new/Phagocyte/src/processor run processor-mcp
claude mcp add rag -- uv --directory /home/shazzadul/Illinois_Tech/Spring26/RA/Github/new/Phagocyte/src/processor run rag-mcp
```

### Remove MCP Servers
```bash
claude mcp remove ingestor
claude mcp remove parser
claude mcp remove researcher
claude mcp remove processor
claude mcp remove rag
```

### List MCP Servers
```bash
claude mcp list
```

---

## Full Pipeline Run

```bash
# 1. Research a topic
uv run phagocyte research "HDF5 best practices" -o ./pipeline_output/phase1_research

# 2. Extract references from research report
uv run phagocyte parse refs ./pipeline_output/phase1_research/research/research_report.md --export-batch -o ./pipeline_output/phase2_parser

# 3. Download papers from batch file
uv run phagocyte parse batch ./pipeline_output/phase2_parser/batch.json -o ./pipeline_output/phase2_parser/papers

# 4. Convert PDFs to markdown
uv run phagocyte ingest batch ./pipeline_output/phase2_parser/papers -o ./pipeline_output/phase3_ingestor

# 5. Process into vector database
uv run phagocyte process run ./pipeline_output/phase3_ingestor -o ./pipeline_output/phase4_processor/lancedb

# 6. Search the database
uv run phagocyte process search ./pipeline_output/phase4_processor/lancedb "chunking strategies"
```
