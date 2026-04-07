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
