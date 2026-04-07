#!/usr/bin/env python3
"""
Neo4j Ingestion Script for PrimeKG (Precision Medicine Knowledge Graph)

Loads the PrimeKG edge-list CSV into a Neo4j graph database with typed nodes
and relationships. Downloads kg.csv from Harvard Dataverse if not present locally.

CONFIGURATION:
    Uses .env file for Neo4j connection settings:
    - NEO4J_URI (default: neo4j://localhost)
    - NEO4J_USER (default: neo4j)
    - NEO4J_PASSWORD
    - NEO4J_DATABASE (default: primekg)

REQUIREMENTS:
    pip install neo4j python-dotenv pandas

USAGE:
    python neo4j/load_primekg_into_neo4j.py
"""

import os
import sys
import logging
import urllib.request
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# --- Constants ---

KG_CSV_URL = "https://dataverse.harvard.edu/api/access/datafile/6180620"

NODE_BATCH_SIZE = 5000
REL_BATCH_SIZE = 2000

# Maps PrimeKG node_type -> (Neo4j label, primary key property name)
NODE_TYPE_MAP = {
    "gene/protein":       ("Gene",              "id"),
    "disease":            ("Disease",            "id"),
    "drug":               ("Drug",               "id"),
    "anatomy":            ("Anatomy",            "id"),
    "effect/phenotype":   ("Effect",             "id"),
    "pathway":            ("Pathway",            "id"),
    "exposure":           ("Exposure",           "id"),
    "biological_process": ("BiologicalProcess",  "id"),
    "molecular_function": ("MolecularFunction",  "id"),
    "cellular_component": ("CellularComponent",  "id"),
    "phenotypic_series":  ("PhenotypicSeries",   "id"),
}

# Maps PrimeKG relation -> (Neo4j relationship type, source label, target label)
RELATION_TYPE_MAP = {
    "protein_protein":              ("INTERACTS_WITH",          "Gene",              "Gene"),
    "drug_protein":                 ("TARGETS",                 "Drug",              "Gene"),
    "drug_drug":                    ("INTERACTS_WITH_DRUG",     "Drug",              "Drug"),
    "drug_disease":                 ("INDICATED_FOR",           "Drug",              "Disease"),
    "indication":                   ("INDICATED_FOR",           "Drug",              "Disease"),
    "contraindication":             ("CONTRAINDICATED_FOR",     "Drug",              "Disease"),
    "off-label use":                ("OFF_LABEL_USE",           "Drug",              "Disease"),
    "drug_effect":                  ("HAS_SIDE_EFFECT",         "Drug",              "Effect"),
    "disease_disease":              ("DISEASE_IS_A",            "Disease",           "Disease"),
    "disease_protein":              ("ASSOCIATED_WITH",         "Disease",           "Gene"),
    "disease_phenotype_positive":   ("HAS_PHENOTYPE",           "Disease",           "Effect"),
    "disease_phenotype_negative":   ("ABSENT_PHENOTYPE",        "Disease",           "Effect"),
    "phenotype_phenotype":          ("PHENOTYPE_IS_A",          "Effect",            "Effect"),
    "phenotype_protein":            ("PHENOTYPE_ASSOCIATED_WITH","Effect",           "Gene"),
    "anatomy_anatomy":              ("ANATOMY_IS_A",            "Anatomy",           "Anatomy"),
    "anatomy_protein_present":      ("EXPRESSES",               "Anatomy",           "Gene"),
    "anatomy_protein_absent":       ("NOT_EXPRESSED",            "Anatomy",           "Gene"),
    "pathway_pathway":              ("PATHWAY_IS_A",            "Pathway",           "Pathway"),
    "pathway_protein":              ("INVOLVES",                "Pathway",           "Gene"),
    "bioprocess_bioprocess":        ("BIOPROCESS_IS_A",         "BiologicalProcess", "BiologicalProcess"),
    "bioprocess_protein":           ("BP_INVOLVES",             "BiologicalProcess", "Gene"),
    "molfunc_molfunc":              ("MOLFUNC_IS_A",            "MolecularFunction", "MolecularFunction"),
    "molfunc_protein":              ("MF_INVOLVES",             "MolecularFunction", "Gene"),
    "cellcomp_cellcomp":            ("CELLCOMP_IS_A",           "CellularComponent", "CellularComponent"),
    "cellcomp_protein":             ("CC_INVOLVES",             "CellularComponent", "Gene"),
    "exposure_protein":             ("EXPOSURE_AFFECTS",        "Exposure",          "Gene"),
    "exposure_disease":             ("EXPOSURE_LINKED_TO",      "Exposure",          "Disease"),
    "exposure_exposure":            ("EXPOSURE_IS_A",           "Exposure",          "Exposure"),
    "exposure_bioprocess":          ("EXPOSURE_AFFECTS_BP",     "Exposure",          "BiologicalProcess"),
    "exposure_molfunc":             ("EXPOSURE_AFFECTS_MF",     "Exposure",          "MolecularFunction"),
    "exposure_cellcomp":            ("EXPOSURE_AFFECTS_CC",     "Exposure",          "CellularComponent"),
    # OMIM relations (added Dec 2023)
    "mim_disease":                  ("MIM_LINKED_TO_DISEASE",   "Gene",              "Disease"),
    "mim_gene":                     ("MIM_LINKED_TO_GENE",      "Gene",              "Gene"),
    "mim_phenotype":                ("MIM_ASSOCIATED_PHENOTYPE","Gene",              "Effect"),
    "mim_phenotypic_series":        ("MIM_MEMBER_OF_SERIES",    "Gene",              "PhenotypicSeries"),
    "mim_phenotypic_series_disease":("MIM_SERIES_LINKED_DISEASE","PhenotypicSeries", "Disease"),
    "phenotype_map":                ("PHENOTYPE_MAP",           "Gene",              "Gene"),
}


# --- Data acquisition ---

def download_kg_csv(dest: Path) -> None:
    """Download kg.csv from Harvard Dataverse if not already present."""
    if dest.exists():
        logger.info(f"Found existing {dest}")
        return
    logger.info(f"Downloading kg.csv from Harvard Dataverse to {dest} (~936 MB) ...")
    urllib.request.urlretrieve(KG_CSV_URL, dest)
    logger.info(f"Download complete ({dest.stat().st_size / 1e6:.1f} MB)")


# --- Data preparation ---

def load_and_deduplicate(csv_path: Path) -> pd.DataFrame:
    """Load kg.csv and remove reverse-duplicate edges."""
    logger.info(f"Loading {csv_path} ...")
    kg = pd.read_csv(csv_path, low_memory=False)
    logger.info(f"Loaded {len(kg):,} rows")

    # Build canonical key: sort the two endpoints so (A->B) and (B->A) hash the same
    def _canon(row):
        a = (str(row["x_id"]), row["x_type"])
        b = (str(row["y_id"]), row["y_type"])
        return (min(a, b), max(a, b), row["relation"])

    logger.info("Deduplicating reverse edges ...")
    kg["_canon"] = kg.apply(_canon, axis=1)
    kg_dedup = kg.drop_duplicates(subset="_canon").drop(columns="_canon")
    logger.info(f"After deduplication: {len(kg_dedup):,} edges")
    return kg_dedup


def extract_nodes(kg: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Extract unique nodes per type from both sides of the edge list."""
    x = kg[["x_id", "x_type", "x_name", "x_source"]].rename(
        columns={"x_id": "node_id", "x_type": "node_type", "x_name": "name", "x_source": "source"}
    )
    y = kg[["y_id", "y_type", "y_name", "y_source"]].rename(
        columns={"y_id": "node_id", "y_type": "node_type", "y_name": "name", "y_source": "source"}
    )
    nodes = pd.concat([x, y]).drop_duplicates(subset=["node_id", "node_type"])
    nodes["node_id"] = nodes["node_id"].astype(str)

    by_type = {}
    for ntype, group in nodes.groupby("node_type"):
        by_type[ntype] = group.reset_index(drop=True)
        logger.info(f"  {ntype}: {len(group):,} nodes")
    return by_type


# --- Neo4j ingestion ---

class PrimeKGIngester:
    """Loads PrimeKG data into Neo4j."""

    def __init__(self, uri: str, username: str, password: str, database: str):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            self.driver.verify_connectivity()
            self.database = database
            logger.info(f"Connected to Neo4j at {uri} (database: {database})")
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            sys.exit(1)

    def close(self):
        self.driver.close()

    def run_query(self, query: str, parameters: dict | None = None) -> list:
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return list(result)

    # -- Clear --

    def clear_database(self):
        """Delete all nodes and relationships in batches."""
        logger.info("Clearing database ...")
        while True:
            result = self.run_query(
                "MATCH (n) WITH n LIMIT 50000 DETACH DELETE n RETURN count(*) AS deleted"
            )
            deleted = result[0]["deleted"] if result else 0
            if deleted == 0:
                break
            logger.info(f"  Deleted {deleted} nodes ...")
        logger.info("Database cleared.")

    # -- Schema --

    def create_constraints_and_indexes(self):
        logger.info("Creating constraints and indexes ...")

        statements = []

        # Unique constraints on id per label
        for ntype, (label, key) in NODE_TYPE_MAP.items():
            statements.append(
                f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.{key} IS UNIQUE"
            )

        # Name indexes on major labels
        for label in ["Gene", "Disease", "Drug", "Anatomy", "Effect", "Pathway", "Exposure"]:
            statements.append(
                f"CREATE INDEX {label.lower()}_name IF NOT EXISTS "
                f"FOR (n:{label}) ON (n.name)"
            )

        for stmt in statements:
            try:
                self.run_query(stmt)
                logger.info(f"  {stmt.split('IF NOT EXISTS')[0].strip()}")
            except Exception as e:
                logger.warning(f"  Skipped (may already exist): {e}")

    # -- Node loading --

    def load_nodes(self, nodes_by_type: dict[str, pd.DataFrame]):
        logger.info("Loading nodes ...")
        for ntype, df in nodes_by_type.items():
            if ntype not in NODE_TYPE_MAP:
                logger.warning(f"  Unknown node type '{ntype}', skipping {len(df)} nodes")
                continue
            label, key = NODE_TYPE_MAP[ntype]
            self._load_node_batch(label, key, df)

    def _load_node_batch(self, label: str, key: str, df: pd.DataFrame):
        query = (
            f"UNWIND $data AS row "
            f"MERGE (n:{label} {{{key}: row.node_id}}) "
            f"ON CREATE SET n.name = row.name, n.source = row.source"
        )
        records = df[["node_id", "name", "source"]].to_dict("records")
        total = len(records)
        for i in range(0, total, NODE_BATCH_SIZE):
            batch = records[i : i + NODE_BATCH_SIZE]
            self.run_query(query, {"data": batch})
            loaded = min(i + NODE_BATCH_SIZE, total)
            if loaded % 20000 == 0 or loaded == total:
                logger.info(f"  {label}: {loaded:,}/{total:,}")
        logger.info(f"  {label}: done ({total:,} nodes)")

    # -- Relationship loading --

    def load_relationships(self, kg: pd.DataFrame):
        logger.info("Loading relationships ...")
        for relation, group in kg.groupby("relation"):
            if relation not in RELATION_TYPE_MAP:
                logger.warning(f"  Unknown relation '{relation}', skipping {len(group)} edges")
                continue
            neo4j_type, src_label, tgt_label = RELATION_TYPE_MAP[relation]

            # After deduplication some edges may have x/y swapped.
            # Normalize: if x_type maps to tgt_label instead of src_label, swap x<->y.
            group = group.copy()
            x_labels = group["x_type"].map(lambda t: NODE_TYPE_MAP.get(t, (None,))[0])
            needs_swap = x_labels != src_label
            if needs_swap.any():
                swapped = group.loc[needs_swap]
                group.loc[needs_swap, "x_id"] = swapped["y_id"].values
                group.loc[needs_swap, "y_id"] = swapped["x_id"].values
                group.loc[needs_swap, "x_type"] = swapped["y_type"].values
                group.loc[needs_swap, "y_type"] = swapped["x_type"].values
                group.loc[needs_swap, "x_name"] = swapped["y_name"].values
                group.loc[needs_swap, "y_name"] = swapped["x_name"].values
                group.loc[needs_swap, "x_source"] = swapped["y_source"].values
                group.loc[needs_swap, "y_source"] = swapped["x_source"].values

            self._load_rel_batch(neo4j_type, src_label, "id", tgt_label, "id", group)

    def _load_rel_batch(
        self,
        rel_type: str,
        src_label: str,
        src_key: str,
        tgt_label: str,
        tgt_key: str,
        df: pd.DataFrame,
    ):
        query = (
            f"UNWIND $data AS row "
            f"MATCH (a:{src_label} {{{src_key}: row.x_id}}) "
            f"MATCH (b:{tgt_label} {{{tgt_key}: row.y_id}}) "
            f"CREATE (a)-[r:{rel_type} {{displayRelation: row.display_relation}}]->(b)"
        )
        records = df[["x_id", "y_id", "display_relation"]].copy()
        records["x_id"] = records["x_id"].astype(str)
        records["y_id"] = records["y_id"].astype(str)
        records = records.to_dict("records")
        total = len(records)
        for i in range(0, total, REL_BATCH_SIZE):
            batch = records[i : i + REL_BATCH_SIZE]
            self.run_query(query, {"data": batch})
            loaded = min(i + REL_BATCH_SIZE, total)
            if loaded % 20000 == 0 or loaded == total:
                logger.info(f"  {rel_type}: {loaded:,}/{total:,}")
        logger.info(f"  {rel_type}: done ({total:,} relationships)")

    # -- Verification --

    def verify(self):
        logger.info("Verifying load ...")

        results = self.run_query(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY count DESC"
        )
        logger.info("Node counts:")
        total_nodes = 0
        for r in results:
            logger.info(f"  {r['label']}: {r['count']:,}")
            total_nodes += r["count"]
        logger.info(f"  TOTAL: {total_nodes:,}")

        results = self.run_query(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS count ORDER BY count DESC"
        )
        logger.info("Relationship counts:")
        total_rels = 0
        for r in results:
            logger.info(f"  {r['type']}: {r['count']:,}")
            total_rels += r["count"]
        logger.info(f"  TOTAL: {total_rels:,}")


# --- Main ---

def main():
    load_dotenv()

    uri = os.getenv("NEO4J_URI", "neo4j://localhost")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "")
    database = os.getenv("NEO4J_DATABASE", "primekg")
    kg_csv_path = Path(os.getenv("KG_CSV_PATH", "kg.csv"))

    if not password:
        logger.error("NEO4J_PASSWORD not set in .env")
        sys.exit(1)

    # Step 1: Download data
    download_kg_csv(kg_csv_path)

    # Step 2: Parse and deduplicate
    kg = load_and_deduplicate(kg_csv_path)

    # Step 3: Extract nodes
    nodes_by_type = extract_nodes(kg)

    # Step 4: Load into Neo4j
    ingester = PrimeKGIngester(uri, user, password, database)
    try:
        ingester.clear_database()
        ingester.create_constraints_and_indexes()
        ingester.load_nodes(nodes_by_type)
        ingester.load_relationships(kg)
        ingester.verify()
    finally:
        ingester.close()

    logger.info("Done.")


if __name__ == "__main__":
    main()
