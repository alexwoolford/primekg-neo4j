# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PrimeKG (Precision Medicine Knowledge Graph)** is a biomedical knowledge graph integrating 20 primary data resources to describe 17,080 diseases with 4,050,249 relationships across ten biological scales (genes/proteins, diseases, drugs, anatomy, phenotypes, pathways, etc.). Published in Nature Scientific Data (2023) by the Zitnik Lab at Harvard.

The repo contains data processing scripts and Jupyter notebooks to build PrimeKG from raw data sources. The final output is a CSV edge list (`kg.csv`) with columns: `relation`, `display_relation`, `x_id`, `x_type`, `x_name`, `x_source`, `y_id`, `y_type`, `y_name`, `y_source`.

## Environment Setup

```bash
# Option 1: pip
pip install -r updated_requirements.txt

# Option 2: conda
conda env create --name PrimeKG --file=environment.yml
```

Key dependencies: pandas, numpy, scikit-learn, torch, transformers, goatools, igraph, scrapy, lxml.

The `setup.sh` and `setup_jupyter.sh` scripts assume the Harvard O2 HPC cluster (module load, specific paths). Adapt for local use.

## Build Pipeline

The KG is built in three stages:

### Stage 1: Download primary data (`datasets/primary_data_resources.sh`)

Downloads and extracts raw data from 20 biomedical databases into `datasets/data/<source>/`. Some sources (DrugBank, UMLS) require manual download with authentication. The script assumes Harvard O2 cluster paths — modify the hardcoded paths before running locally.

### Stage 2: Process each data source (`datasets/processing_scripts/*.py`)

Each script reads raw data from `datasets/data/<source>/` and outputs cleaned CSVs. Scripts are run from within the `processing_scripts/` directory (they use relative paths like `../data/`). Key scripts:

| Script | Input source | Output |
|--------|-------------|--------|
| `bgee.py` | Bgee expression data | `anatomy_gene.csv` |
| `ctd.py` | Comparative Toxicogenomics DB | `exposure_data.csv` |
| `drugbank_drug_drug.py` | DrugBank XML | `drug_drug.csv` |
| `drugbank_drug_protein.py` | DrugBank polypeptide CSVs | `drug_protein.csv` |
| `ncbigene.py` | NCBI gene2go | `protein_go_associations.csv` |
| `go.py` | Gene Ontology OBO | `go_terms_info.csv`, `go_terms_relations.csv` |
| `hpo.py` + `hpo_obo_parser.py` | HPO OBO file | `hp_terms.csv`, `hp_parents.csv`, `hp_references.csv` |
| `hpoa.py` | HPO annotations | `disease_phenotype_pos.csv`, `disease_phenotype_neg.csv` |
| `mondo.py` + `mondo_obo_parser.py` | MONDO OBO | `mondo_terms.csv`, `mondo_parents.csv`, etc. |
| `reactome.py` | Reactome pathway files | `reactome_ncbi.csv`, `reactome_terms.csv`, `reactome_relations.csv` |
| `sider.py` | SIDER side effects | `sider.csv` |
| `uberon.py` | UBERON anatomy ontology | `uberon_terms.csv`, `uberon_rels.csv`, `uberon_is_a.csv` |
| `umls.py` + `map_umls_mondo.py` | UMLS Metathesaurus | `umls_mondo.csv` |
| `omim_tools.py` | OMIM (via API) | OMIM gene/phenotype data |

### Stage 3: Build the graph (`knowledge_graph/build_graph.ipynb`)

Reads all processed CSVs, harmonizes node IDs (using MONDO for diseases, NCBI for genes, DrugBank for drugs), merges edges, removes self-loops and duplicates, and outputs three versions:
- `kg_raw.csv` — all edges before filtering
- `kg_giant.csv` — largest connected component
- `kg.csv` — final version with all features

Additional notebooks:
- `knowledge_graph/append_omim.ipynb` — extends KG with OMIM entries (added Dec 2023)
- `knowledge_graph/engineer_features.ipynb` + `mapping_mayo.ipynb` — adds clinical text features to drug/disease nodes
- `datasets/omim/omim-api.ipynb` — OMIM API wrapper (requires API key)

## Key Architecture Details

- **Node ID harmonization**: Diseases use MONDO IDs, genes/proteins use NCBI Entrez IDs, drugs use DrugBank IDs. The `umls_mondo.csv` mapping bridges UMLS CUIs to MONDO.
- **Edge schema**: Every edge is represented as a row with `(x_id, x_type, x_name, x_source, relation, display_relation, y_id, y_type, y_name, y_source)`. The `clean_edges()` function in `build_graph.ipynb` enforces this.
- **`scripts/utils.py`**: Shared utilities for reading/writing gzipped JSON and GMT files. Used by OMIM processing.
- **Feature extraction** (`datasets/feature_extraction/`): Extracts text descriptions for diseases (Mayo Clinic, Orphanet) and drugs (DrugBank). These are separate from the graph structure.

## Using PrimeKG Without Building

Download the pre-built CSV directly:
```bash
wget -O kg.csv https://dataverse.harvard.edu/api/access/datafile/6180620
```

Or use community dataloaders:
```python
# PyTDC
from tdc.resource import PrimeKG
data = PrimeKG(path='./data')

# PyKEEN
import pykeen.datasets
pykeen.datasets.has_dataset('primekg')
```

## Case Study

`case_study/autism.ipynb` demonstrates downstream analysis on the built KG.

## Neo4j and Chatbot (Fork Additions)

This fork adds two components that load PrimeKG into Neo4j and provide a conversational interface.

### Neo4j Loader (`neo4j/load_primekg_into_neo4j.py`)

Ingests `kg.csv` into a Neo4j graph database. Creates 10 node types (Gene, Disease, Drug, Effect, Anatomy, Pathway, BiologicalProcess, MolecularFunction, CellularComponent, Exposure) with unique constraints and indexes, plus 30 relationship types. Downloads `kg.csv` from Harvard Dataverse on first run. Uses batched `UNWIND` for performance. Deduplicates reverse-duplicate edges before loading.

```bash
conda activate primekg
pip install -r neo4j/requirements.txt
python neo4j/load_primekg_into_neo4j.py
```

### Chatbot (`chatbot/`)

A LangChain ReAct agent (Claude Sonnet 4) that answers biomedical questions by generating Cypher queries against the Neo4j graph. Uses the Neo4j MCP server (via `uvx mcp-neo4j-cypher`) for read-only graph access. Multi-turn CLI interface with conversation memory.

```bash
conda activate primekg
pip install -e chatbot/
primekg-chatbot
```

### Shared Configuration

Both components read from a single `.env` file at the project root (copy `.env.example` to get started). Required variables: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`. The chatbot also requires `ANTHROPIC_API_KEY`.
