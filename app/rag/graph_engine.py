import json
import re
from collections import deque
from typing import Any
import networkx as nx
from sqlalchemy import select
from app.core.config import get_settings
from app.core.database import KGEntity, KGRelation, SessionLocal
from app.kg.entity_resolver import CANONICAL_SPECS

settings = get_settings()


class SupplyChainKnowledgeGraph:
    """Mesin graf pengetahuan NetworkX untuk traversal multi-hop, shortest path, dan PageRank."""

    def __init__(self, tenant_id: str | None = None) -> None:
        self.tenant_id = tenant_id or settings.default_tenant_id
        self.graph = nx.MultiDiGraph()
        self.entities: dict[str, dict[str, Any]] = {}
        self.relations: list[dict[str, Any]] = []
        self.pagerank_scores: dict[str, float] = {}
        self._load_graph()

    def _load_graph(self) -> None:
        entities_list: list[dict[str, Any]] = []
        relations_list: list[dict[str, Any]] = []

        try:
            with SessionLocal() as session:
                ent_rows = (
                    session.execute(
                        select(KGEntity).where(KGEntity.tenant_id == self.tenant_id)
                    )
                    .scalars()
                    .all()
                )
                rel_rows = (
                    session.execute(
                        select(KGRelation).where(KGRelation.tenant_id == self.tenant_id)
                    )
                    .scalars()
                    .all()
                )
                for e in ent_rows:
                    entities_list.append(
                        {
                            "entity_id": e.entity_id,
                            "entity_name": e.entity_name,
                            "entity_type": e.entity_type,
                            "canonical_code": e.canonical_code,
                            "description": e.description or "",
                            "source_doc_id": e.source_doc_id,
                        }
                    )
                for r in rel_rows:
                    relations_list.append(
                        {
                            "relation_id": r.relation_id,
                            "subject_id": r.subject_id,
                            "predicate": r.predicate,
                            "object_id": r.object_id,
                            "confidence": float(r.confidence),
                            "evidence_quote": r.evidence_quote,
                            "source_doc_id": r.source_doc_id,
                        }
                    )
        except Exception:
            entities_list = []

        # Fallback ke snapshot kurasi lokal jika database belum terisi
        if not entities_list:
            snapshot_path = settings.curated_data_dir / "kg_snapshot.json"
            if snapshot_path.exists():
                with snapshot_path.open("r", encoding="utf-8") as f:
                    snap = json.load(f)
                entities_list = snap.get("entities", [])
                relations_list = snap.get("relations", [])

        for ent in entities_list:
            eid = ent["entity_id"]
            self.entities[eid] = ent
            self.graph.add_node(
                eid,
                label=ent["entity_name"],
                entity_type=ent["entity_type"],
                canonical_code=ent.get("canonical_code") or "",
                source_doc_id=ent.get("source_doc_id") or "",
            )

        for rel in relations_list:
            subj = rel["subject_id"]
            obj = rel["object_id"]
            if subj in self.entities and obj in self.entities:
                self.relations.append(rel)
                self.graph.add_edge(
                    subj,
                    obj,
                    key=rel["relation_id"],
                    relation_id=rel["relation_id"],
                    predicate=rel["predicate"],
                    confidence=rel["confidence"],
                    evidence_quote=rel["evidence_quote"],
                    source_doc_id=rel["source_doc_id"],
                )

        self._compute_pagerank()

    def _compute_pagerank(self) -> None:
        if self.graph.number_of_nodes() == 0:
            self.pagerank_scores = {}
            return
        simple_dg = nx.DiGraph()
        for node, attrs in self.graph.nodes(data=True):
            simple_dg.add_node(node, **attrs)
        for u, v, data in self.graph.edges(data=True):
            weight = float(data.get("confidence", 1.0))
            if simple_dg.has_edge(u, v):
                simple_dg[u][v]["weight"] += weight
            else:
                simple_dg.add_edge(u, v, weight=weight)
        scores = nx.pagerank(simple_dg, alpha=0.85, weight="weight")
        self.pagerank_scores = {k: round(float(v), 5) for k, v in scores.items()}

    def get_top_central_entities(self, top_n: int = 8) -> list[dict[str, Any]]:
        ranked = sorted(self.pagerank_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_n
        ]
        results = []
        for eid, score in ranked:
            ent = self.entities.get(eid, {})
            results.append(
                {
                    "entity_id": eid,
                    "entity_name": ent.get("entity_name", eid),
                    "entity_type": ent.get("entity_type", "CONCEPT"),
                    "canonical_code": ent.get("canonical_code"),
                    "pagerank_score": score,
                    "in_degree": self.graph.in_degree(eid),
                    "out_degree": self.graph.out_degree(eid),
                }
            )
        return results

    def extract_seed_entities(self, query: str) -> list[str]:
        """Menghubungkan kode/nama entitas dalam kueri pengguna ke canonical entity_id."""
        q_lower = query.lower()
        matched_ids: list[str] = []

        # 1. Cocokkan kode resmi & alias kanonik
        for spec in CANONICAL_SPECS:
            if spec.entity_id not in self.entities:
                continue
            code_pattern = rf"\b{re.escape(spec.canonical_code.lower())}\b"
            if re.search(code_pattern, q_lower):
                if spec.entity_id not in matched_ids:
                    matched_ids.append(spec.entity_id)
                continue
            for alias in spec.aliases:
                if len(alias) >= 5 and alias in q_lower:
                    if spec.entity_id not in matched_ids:
                        matched_ids.append(spec.entity_id)
                    break

        # 2. Cocokkan token bermakna pada seluruh nama entitas graf
        query_tokens = {
            tok
            for tok in re.findall(r"[a-z0-9\-]{4,}", q_lower)
            if tok
            not in {
                "yang",
                "untuk",
                "dengan",
                "dari",
                "pada",
                "jika",
                "akan",
                "atau",
                "risiko",
                "biaya",
            }
        }
        for eid, ent in self.entities.items():
            if eid in matched_ids:
                continue
            ent_name_lower = ent["entity_name"].lower()
            if any(tok in ent_name_lower for tok in query_tokens):
                matched_ids.append(eid)

        # Fallback ke entitas dengan PageRank tertinggi jika kueri bersifat umum
        if not matched_ids and self.pagerank_scores:
            top_ids = [
                eid
                for eid, _ in sorted(
                    self.pagerank_scores.items(), key=lambda x: x[1], reverse=True
                )[:3]
            ]
            matched_ids.extend(top_ids)

        return matched_ids[:8]

    def traverse_multi_hop(
        self,
        seed_entity_ids: list[str],
        max_hops: int = 3,
        max_triples: int = 35,
    ) -> dict[str, Any]:
        """Menelusuri subgraf multi-hop (downstream & upstream) serta shortest paths antar seed."""
        visited_nodes: set[str] = set()
        collected_triples: list[dict[str, Any]] = []
        seen_rel_ids: set[str] = set()

        queue: deque[tuple[str, int]] = deque()
        for sid in seed_entity_ids:
            if sid in self.graph:
                visited_nodes.add(sid)
                queue.append((sid, 0))

        while queue and len(collected_triples) < max_triples:
            curr_id, depth = queue.popleft()
            if depth >= max_hops:
                continue

            # Outgoing edges (downstream impact: Supplier -> Component -> Product)
            for _, nbr_id, edge_data in self.graph.out_edges(curr_id, data=True):
                rel_id = edge_data["relation_id"]
                if rel_id not in seen_rel_ids:
                    seen_rel_ids.add(rel_id)
                    collected_triples.append(
                        {
                            "hop": depth + 1,
                            "direction": "OUTGOING",
                            "subject_id": curr_id,
                            "subject_name": self.entities[curr_id]["entity_name"],
                            "subject_code": self.entities[curr_id].get(
                                "canonical_code"
                            ),
                            "predicate": edge_data["predicate"],
                            "object_id": nbr_id,
                            "object_name": self.entities[nbr_id]["entity_name"],
                            "object_code": self.entities[nbr_id].get("canonical_code"),
                            "confidence": edge_data["confidence"],
                            "evidence_quote": edge_data["evidence_quote"],
                            "source_doc_id": edge_data["source_doc_id"],
                        }
                    )
                if nbr_id not in visited_nodes:
                    visited_nodes.add(nbr_id)
                    queue.append((nbr_id, depth + 1))

            # Incoming edges (upstream dependency & governance rules)
            for pred_id, _, edge_data in self.graph.in_edges(curr_id, data=True):
                rel_id = edge_data["relation_id"]
                if rel_id not in seen_rel_ids and len(collected_triples) < max_triples:
                    seen_rel_ids.add(rel_id)
                    collected_triples.append(
                        {
                            "hop": depth + 1,
                            "direction": "INCOMING",
                            "subject_id": pred_id,
                            "subject_name": self.entities[pred_id]["entity_name"],
                            "subject_code": self.entities[pred_id].get(
                                "canonical_code"
                            ),
                            "predicate": edge_data["predicate"],
                            "object_id": curr_id,
                            "object_name": self.entities[curr_id]["entity_name"],
                            "object_code": self.entities[curr_id].get("canonical_code"),
                            "confidence": edge_data["confidence"],
                            "evidence_quote": edge_data["evidence_quote"],
                            "source_doc_id": edge_data["source_doc_id"],
                        }
                    )
                if pred_id not in visited_nodes:
                    visited_nodes.add(pred_id)
                    queue.append((pred_id, depth + 1))

        # Shortest paths antar pasangan seed entities (undirected projection)
        undirected = self.graph.to_undirected()
        shortest_paths: list[str] = []
        valid_seeds = [s for s in seed_entity_ids if s in undirected]
        for i in range(len(valid_seeds)):
            for j in range(i + 1, len(valid_seeds)):
                src, dst = valid_seeds[i], valid_seeds[j]
                try:
                    path_ids = nx.shortest_path(undirected, source=src, target=dst)
                    if 2 <= len(path_ids) <= 5:
                        labels = [self.entities[nid]["entity_name"] for nid in path_ids]
                        shortest_paths.append(" <-> ".join(labels))
                except nx.NetworkXNoPath:
                    continue

        # Payload siap Cytoscape.js untuk Executive War Room UI
        cytoscape_nodes = [
            {
                "data": {
                    "id": nid,
                    "label": self.entities[nid]["entity_name"],
                    "type": self.entities[nid]["entity_type"],
                    "code": self.entities[nid].get("canonical_code") or "",
                    "pagerank": self.pagerank_scores.get(nid, 0.0),
                    "is_seed": nid in seed_entity_ids,
                }
            }
            for nid in visited_nodes
            if nid in self.entities
        ]
        cytoscape_edges = [
            {
                "data": {
                    "id": f"{t['subject_id']}_{t['predicate']}_{t['object_id']}",
                    "source": t["subject_id"],
                    "target": t["object_id"],
                    "label": t["predicate"],
                    "source_doc_id": t["source_doc_id"],
                }
            }
            for t in collected_triples
        ]

        return {
            "seed_entities": [
                {
                    "entity_id": sid,
                    "entity_name": self.entities[sid]["entity_name"],
                    "canonical_code": self.entities[sid].get("canonical_code"),
                }
                for sid in valid_seeds
            ],
            "visited_node_count": len(visited_nodes),
            "triples": collected_triples,
            "shortest_paths": shortest_paths[:10],
            "cytoscape": {
                "nodes": cytoscape_nodes,
                "edges": cytoscape_edges,
            },
        }
