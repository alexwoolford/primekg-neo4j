# Loading PrimeKG into Neo4j

Loads the PrimeKG edge-list CSV into a Neo4j graph database with typed nodes and relationships. The script downloads `kg.csv` from Harvard Dataverse if it isn't already present.

## Prerequisites

- **Neo4j** 5.x+ running locally (or remotely)
- **Python** 3.10+
- A dedicated Neo4j database named `primekg` (create via Neo4j Browser: `CREATE DATABASE primekg`)

## Setup

1. Copy the environment template and fill in your Neo4j password:

```bash
cp ../.env.example ../.env
# Edit ../.env with your Neo4j credentials
```

2. Create a conda environment and install dependencies:

```bash
conda create -n primekg python=3.10 -y
conda activate primekg
pip install -r requirements.txt
```

## Run

```bash
cd /path/to/PrimeKG
python neo4j/load_primekg_into_neo4j.py
```

On first run, the script downloads `kg.csv` (~936 MB) from Harvard Dataverse. Subsequent runs skip the download.

The script creates constraints, indexes, nodes, and relationships in batches. Expect ~10-15 minutes depending on your hardware.

## What gets loaded

**129,375 nodes** across 10 types:

| Label | Count | Source |
|-------|-------|--------|
| BiologicalProcess | 28,642 | Gene Ontology |
| Gene | 27,610 | NCBI |
| Disease | 17,080 | MONDO |
| Effect | 15,311 | HPO |
| Anatomy | 14,033 | UBERON |
| MolecularFunction | 11,169 | Gene Ontology |
| Drug | 7,957 | DrugBank |
| CellularComponent | 4,176 | Gene Ontology |
| Pathway | 2,516 | Reactome |
| Exposure | 818 | CTD |

**~4 million relationships** across 30 types, including:

| Relationship | Example | Count |
|-------------|---------|-------|
| EXPRESSES | Anatomy -> Gene | 1,518,203 |
| INTERACTS_WITH_DRUG | Drug -> Drug | 1,336,314 |
| INTERACTS_WITH | Gene -> Gene | 321,075 |
| HAS_PHENOTYPE | Disease -> Effect | 150,317 |
| ASSOCIATED_WITH | Disease -> Gene | 80,411 |
| TARGETS | Drug -> Gene | 25,468 |
| INDICATED_FOR | Drug -> Disease | 9,388 |
| ... | | |

## Verify

After loading, run in Neo4j Browser:

```cypher
MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC
```

```cypher
MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC
```
