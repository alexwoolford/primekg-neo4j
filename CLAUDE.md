# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PrimeKG (Precision Medicine Knowledge Graph)** is a biomedical knowledge graph integrating 20 primary data resources to describe 17,080 diseases with 4,050,249 relationships across ten biological scales (genes/proteins, diseases, drugs, anatomy, phenotypes, pathways, etc.). Published in Nature Scientific Data (2023) by the Zitnik Lab at Harvard.

This fork loads PrimeKG into Neo4j and provides a conversational chatbot for querying the graph. The pre-built CSV (`kg.csv`) is downloaded automatically from Harvard Dataverse -- there is no build pipeline in this repo. See [mims-harvard/PrimeKG](https://github.com/mims-harvard/PrimeKG) for the upstream build scripts.

## Neo4j Loader (`neo4j/load_primekg_into_neo4j.py`)

Ingests `kg.csv` into a Neo4j graph database. Creates 10 node types (Gene, Disease, Drug, Effect, Anatomy, Pathway, BiologicalProcess, MolecularFunction, CellularComponent, Exposure) with unique constraints and indexes, plus 30 relationship types. Downloads `kg.csv` from Harvard Dataverse on first run. Uses batched `UNWIND` for performance. Deduplicates reverse-duplicate edges before loading.

```bash
conda activate primekg
pip install -r neo4j/requirements.txt
python neo4j/load_primekg_into_neo4j.py
```

### Key Architecture Details

- **Edge schema**: Every edge in `kg.csv` is a row with `(x_id, x_type, x_name, x_source, relation, display_relation, y_id, y_type, y_name, y_source)`.
- **Node ID harmonization**: Diseases use MONDO IDs, genes/proteins use NCBI Entrez IDs, drugs use DrugBank IDs.
- **Deduplication**: The loader removes reverse-duplicate edges (where A->B and B->A represent the same relationship) and normalizes edge direction before inserting.

## Chatbot (`chatbot/`)

A LangChain ReAct agent (Claude Sonnet 4) that answers biomedical questions by generating Cypher queries against the Neo4j graph. Uses the Neo4j MCP server (via `uvx mcp-neo4j-cypher`) for read-only graph access. Multi-turn CLI interface with conversation memory.

```bash
conda activate primekg
pip install -e chatbot/
primekg-chatbot
```

## Shared Configuration

Both components read from a single `.env` file at the project root (copy `.env.example` to get started). Required variables: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`. The chatbot also requires `ANTHROPIC_API_KEY`.
