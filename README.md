# PrimeKG
----

[![website](https://img.shields.io/badge/website-live-brightgreen)](https://zitniklab.hms.harvard.edu/projects/PrimeKG/)
[![GitHub Repo stars](https://img.shields.io/github/stars/mims-harvard/PrimeKG)](https://github.com/mims-harvard/PrimeKG/stargazers)
[![GitHub Repo forks](https://img.shields.io/github/forks/mims-harvard/PrimeKG)](https://github.com/mims-harvard/PrimeKG/network/members)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

[**Lab Website**](https://zitniklab.hms.harvard.edu/projects/PrimeKG/) | [**Nature Publication**](https://www.nature.com/articles/s41597-023-01960-3) | [**Harvard Dataverse**](https://doi.org/10.7910/DVN/IXA7BM)

## TL;DR
**Precision Medicine Knowledge Graph (PrimeKG)** presents a holistic view of diseases. PrimeKG integrates 20
high-quality biomedical resources to describe 17,080 diseases with 4,050,249 relationships representing ten major
biological scales. This fork loads PrimeKG into **Neo4j** and includes a conversational chatbot for exploring the graph with natural language.

## Table of Contents
- [Getting Started with Neo4j](#getting-started-with-neo4j)
- [Multi-hop Reasoning](#multi-hop-reasoning)
- [Chatbot](#chatbot)
- [Unique Features of PrimeKG](#unique-features-of-primekg)
- [Citing PrimeKG](#citing-primekg)
- [Data Server](#data-server)
- [License](#license)


## Getting Started with Neo4j

PrimeKG is a natural fit for a graph database. This fork loads the full knowledge graph into **Neo4j**, giving you Cypher queries, graph visualization, and a conversational chatbot out of the box.

### Quick start

```bash
cp .env.example .env   # fill in your Neo4j credentials
conda create -n primekg python=3.10 -y && conda activate primekg

# Load PrimeKG into Neo4j (~129K nodes, ~4M relationships)
pip install -r neo4j/requirements.txt
python neo4j/load_primekg_into_neo4j.py
```

The loader downloads `kg.csv` from Harvard Dataverse on first run, creates typed nodes (Gene, Disease, Drug, Effect, Anatomy, Pathway, and more), relationships, constraints, and indexes. See [`neo4j/README.md`](neo4j/README.md) for full details.

### Example Cypher queries

Once loaded, explore the graph in Neo4j Browser:

```cypher
// What genes are associated with Alzheimer's disease?
MATCH (d:Disease)-[:ASSOCIATED_WITH]->(g:Gene)
WHERE toLower(d.name) CONTAINS 'alzheimer'
RETURN d.name, g.name LIMIT 25

// What drugs target BRCA1?
MATCH (dr:Drug)-[:TARGETS]->(g:Gene {name: 'BRCA1'})
RETURN dr.name

// Find drugs that target genes associated with breast cancer
MATCH (d:Disease)-[:ASSOCIATED_WITH]->(g:Gene)<-[:TARGETS]-(dr:Drug)
WHERE toLower(d.name) CONTAINS 'breast cancer'
RETURN dr.name, g.name, d.name LIMIT 25
```

### Multi-hop reasoning

Graph databases shine when you need to traverse multiple relationship types in a single query. Here are examples with real results from PrimeKG.

**Drug repurposing: Which diabetes drugs target genes associated with Parkinson's disease?**

```cypher
MATCH (d:Disease)-[:ASSOCIATED_WITH]->(g:Gene)<-[:TARGETS]-(dr:Drug)-[:INDICATED_FOR]->(other:Disease)
WHERE toLower(d.name) = 'parkinson disease'
  AND NOT toLower(other.name) CONTAINS 'parkinson'
RETURN dr.name AS drug, other.name AS currently_indicated_for,
       collect(DISTINCT g.name) AS parkinson_genes
ORDER BY size(collect(DISTINCT g.name)) DESC LIMIT 5
```

| Drug | Currently indicated for | Parkinson-associated genes |
|------|------------------------|---------------------------|
| Dopamine | Hypotensive disorder | SOD1, SLC6A3, MAOA, DRD2, DRD1, MAOB, SLC18A2 |
| Polaprezinc | Peptic ulcer disease | SOD1, IL6, TNF, HMOX1, SOD2, NGF, GPX1 |
| Chlorpromazine | Schizophrenia | BCHE, DRD2, DRD1, ABCB1, CYP2E1, CYP2D6 |
| Imipramine | Anxiety disorder | SLC6A3, DRD2, DRD1, ABCB1, CYP2E1, CYP2D6 |

This traverses 4 node types (Disease -> Gene <- Drug -> Disease) in a single query, surfacing drug repurposing candidates that would be nearly impossible to find in a flat table.

**Disease similarity: Which other cancers share the most drug-target genes with breast cancer?**

```cypher
MATCH (dr:Drug)-[:INDICATED_FOR]->(bc:Disease)
WHERE toLower(bc.name) CONTAINS 'breast' AND toLower(bc.name) CONTAINS 'cancer'
WITH dr
MATCH (dr)-[:TARGETS]->(g:Gene)<-[:ASSOCIATED_WITH]-(other:Disease)
WHERE NOT toLower(other.name) CONTAINS 'breast'
RETURN other.name AS disease, count(DISTINCT g) AS shared_genes
ORDER BY shared_genes DESC LIMIT 5
```

| Disease | Shared genes |
|---------|-------------|
| Colorectal cancer | 28 |
| Prostate cancer | 27 |
| Uterine carcinoma | 27 |
| Liver cancer | 21 |
| Lung cancer | 19 |

**What biological processes do rheumatoid arthritis drugs act on?**

```cypher
MATCH (dr:Drug)-[:INDICATED_FOR]->(d:Disease {name: 'rheumatoid arthritis'})
MATCH (dr)-[:TARGETS]->(g:Gene)<-[:BP_INVOLVES]-(bp:BiologicalProcess)
WHERE toLower(bp.name) CONTAINS 'inflammat' OR toLower(bp.name) CONTAINS 'immune'
RETURN bp.name AS biological_process, count(DISTINCT dr) AS drug_count
ORDER BY drug_count DESC LIMIT 5
```

| Biological process | Drugs targeting it |
|-------------------|-------------------|
| Inflammatory response | 47 |
| Regulation of inflammatory response | 39 |
| Regulation of neuroinflammatory response | 30 |
| Innate immune response | 17 |
| Positive regulation of inflammatory response | 15 |

This traverses Drug -> Gene -> BiologicalProcess, revealing that RA drugs collectively target genes involved in 47 distinct inflammatory and immune processes.


## Chatbot

Ask biomedical questions in plain English and get answers backed by Cypher queries against the Neo4j graph. Built with LangChain, LangGraph, and Claude, using the [Neo4j MCP server](https://github.com/neo4j-contrib/mcp-neo4j) for graph access.

```bash
pip install -e chatbot/
primekg-chatbot
```

See [`chatbot/README.md`](chatbot/README.md) for setup and example questions.


## Unique Features of PrimeKG
 
- *Diverse coverage of diseases*: PrimeKG contains over 17,000 diseases including rare dieases. Disease nodes in PrimeKG are densely connected to other nodes in the graph and have been optimized for clinical relevance in downstream precision medicine tasks. 
- *Heterogeneous knowledge graph*: PrimeKG contains over 100,000 nodes distributed over various biological scales as depicted below. PrimeKG also contains over 4 million relationships between these nodes distributed over 29 types of edges.
- *Multimodal integration of clinical knowledge*: Disease and drug nodes in PrimeKG are augmented with clinical descriptors that come from medical authorities such as Mayo Clinic, Orphanet, Drug Bank, and so forth. 

<p align="center"><img src="https://github.com/mims-harvard/PrimeKG/blob/main/fig/schematic.png" alt="overview" width="600px" /></p>

<p align="center"><img src="https://github.com/mims-harvard/PrimeKG/blob/main/fig/PrimeKG-example.png" alt="PrimeKG-example"/></p>


## Citing PrimeKG

If you find PrimeKG useful, cite the original work:
```
@article{chandak2022building,
  title={Building a knowledge graph to enable precision medicine},
  author={Chandak, Payal and Huang, Kexin and Zitnik, Marinka},
  journal={Nature Scientific Data},
  doi={https://doi.org/10.1038/s41597-023-01960-3},
  URL={https://www.nature.com/articles/s41597-023-01960-3},
  year={2023}
}
```

## Data Server

PrimeKG is hosted on [Harvard Dataverse](https://doi.org/10.7910/DVN/IXA7BM). The Neo4j loader downloads the data automatically on first run.

## License
PrimeKG codebase and associated tools are released under the MIT license. Please note that this license specifically refers to the PrimeKG software, and is distinct from any licenses governing the PrimeKG dataset itself. For individual dataset usage, refer to the respective dataset licenses available on data website.

---

*This is a fork of [mims-harvard/PrimeKG](https://github.com/mims-harvard/PrimeKG). See the upstream repository for build pipeline documentation and data processing scripts.*
