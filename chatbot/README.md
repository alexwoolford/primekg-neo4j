# PrimeKG Chatbot

A conversational interface for querying the PrimeKG knowledge graph in Neo4j. Ask biomedical questions in plain English and the chatbot generates and executes Cypher queries using a ReAct agent.

Built with LangChain, LangGraph, and Claude, using the Neo4j MCP server for graph access.

## Prerequisites

- **Neo4j** loaded with PrimeKG (see [`neo4j/README.md`](../neo4j/README.md))
- **Anthropic API key**
- **uv** installed ([docs](https://docs.astral.sh/uv/getting-started/installation/)) -- used to run the Neo4j MCP server via `uvx`

## Setup

1. Ensure your `.env` at the project root has Neo4j credentials and an Anthropic API key:

```bash
cp ../.env.example ../.env
# Edit ../.env -- set NEO4J_PASSWORD and ANTHROPIC_API_KEY
```

2. Create a conda environment and install:

```bash
conda create -n primekg python=3.10 -y
conda activate primekg
pip install -e .
```

## Run

```bash
cd /path/to/PrimeKG
primekg-chatbot
```

## Example questions

- What genes are associated with Alzheimer's disease?
- What drugs target the BRCA1 gene?
- What are the side effects of Metformin?
- What pathways involve the TP53 gene?
- Which anatomical structures express the EGFR gene?
- What exposures are linked to lung cancer?
- Find drugs that target genes associated with breast cancer

## Architecture

```
User Question -> CLI -> ReAct Agent (Claude) -> Neo4j MCP Server -> Neo4j (Cypher) -> Results
```

The agent calls `get-schema` to learn the graph structure, then generates and executes Cypher queries via `read-cypher`. Multi-turn conversation is supported -- follow-up questions retain context.