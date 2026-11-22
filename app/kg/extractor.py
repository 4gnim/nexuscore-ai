import json
import re
import time
from typing import Any
import pandas as pd
from pydantic import BaseModel, Field
from app.core.config import get_settings
from app.core.database import KGEntity, KGRelation, SessionLocal, init_db
from app.core.llm_router import invoke_structured_with_failover
from app.kg.entity_resolver import CANONICAL_SPECS, make_relation_id, resolve_entity

settings = get_settings()


class ExtractedEntity(BaseModel):
    name: str = Field(..., description="Nama entitas sesuai teks dokumen")
    entity_type: str = Field(
        default="CONCEPT",
        description="Tipe entitas: ORGANIZATION, SUPPLIER, COMPONENT, PRODUCT, PORT_HUB, WAREHOUSE, POLICY, REGULATION, ROLE, RISK_EVENT",
    )
    code: str | None = Field(default=None, description="Kode resmi jika ada")
    description: str = Field(default="", description="Ringkasan singkat peran entitas")


class ExtractedRelation(BaseModel):
    subject: str = Field(..., description="Nama atau kode entitas subjek")
    predicate: str = Field(..., description="Relasi UPPER_SNAKE_CASE")
    object: str = Field(..., description="Nama atau kode entitas objek")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    evidence_quote: str = Field(
        default="", description="Kutipan kalimat singkat dari dokumen"
    )


class DocumentExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)


KG_SCHEMA_EXAMPLE = """{
  "entities": [
    {"name": "FormosaSilicon Foundry Corp", "entity_type": "SUPPLIER", "code": "SUP-001", "description": "Primary semiconductor foundry"}
  ],
  "relations": [
    {"subject": "SUP-001", "predicate": "SHIPS_THROUGH", "object": "Port of Kaohsiung", "confidence": 0.98, "evidence_quote": "shipping exclusively through Port of Kaohsiung"}
  ]
}"""

EXTRACTION_SYSTEM_PROMPT = """Anda adalah Principal Knowledge Graph Architect untuk ApexGlobal Manufacturing Corp.
Ekstrak seluruh entitas penting dan relasi faktual (subject)-[predicate]->(object) dari dokumen korporat.
Pertahankan kode resmi (SUP-001..SUP-008, CMP-001..CMP-010, PRD-001..PRD-006, WH-ID, COV-FIN-01, SOP-SC-04, SOP-LOG-09, TAR-2026-88, ESG-2026-03, GOV-SEC-01, SupplyChainDirector) bila ada.
Gunakan predikat UPPER_SNAKE_CASE (SUPPLIES, SHIPS_THROUGH, BACKUP_FOR, USED_IN_PRODUCT, EXPOSED_TO_RISK, GOVERNED_BY, TRIGGERS_BREACH, REQUIRES_APPROVAL_FROM, EXEMPTS_TARIFF, REROUTES_VIA)."""


def _normalize_predicate(predicate: str) -> str:
    clean = re.sub(r"[^A-Z0-9_]", "_", predicate.upper().strip())
    return re.sub(r"_+", "_", clean).strip("_") or "RELATED_TO"


def _seed_canonical_and_bom_backbone(
    entities_map: dict[str, dict[str, Any]],
    relations_map: dict[str, dict[str, Any]],
    tenant_id: str,
) -> None:
    """Memastikan seluruh node kanonik & relasi struktural BOM/Supplier terhubung utuh di KG."""
    for spec in CANONICAL_SPECS:
        if spec.entity_id not in entities_map:
            entities_map[spec.entity_id] = {
                "entity_id": spec.entity_id,
                "tenant_id": tenant_id,
                "entity_name": spec.canonical_name,
                "entity_type": spec.entity_type,
                "canonical_code": spec.canonical_code,
                "description": f"Canonical master entity ({spec.canonical_code})",
                "source_doc_id": "MASTER-ERP",
            }

    bom_path = settings.cleaned_data_dir / "bom.parquet"
    comp_path = settings.cleaned_data_dir / "components.parquet"
    if bom_path.exists() and comp_path.exists():
        bom_df = pd.read_parquet(bom_path)
        comp_df = pd.read_parquet(comp_path)

        for _, crow in comp_df.iterrows():
            comp_id, _, _, _ = resolve_entity(
                crow["component_id"], "COMPONENT", crow["component_id"]
            )
            pri_id, _, _, _ = resolve_entity(
                crow["primary_supplier_id"], "SUPPLIER", crow["primary_supplier_id"]
            )
            bak_id, _, _, _ = resolve_entity(
                crow["backup_supplier_id"], "SUPPLIER", crow["backup_supplier_id"]
            )

            rel1 = make_relation_id(pri_id, "PRIMARY_SUPPLIER_OF", comp_id)
            relations_map.setdefault(
                rel1,
                {
                    "relation_id": rel1,
                    "tenant_id": tenant_id,
                    "subject_id": pri_id,
                    "predicate": "PRIMARY_SUPPLIER_OF",
                    "object_id": comp_id,
                    "confidence": 1.0,
                    "evidence_quote": f"{crow['primary_supplier_id']} is primary supplier for {crow['component_id']}",
                    "source_doc_id": "MASTER-ERP",
                },
            )

            rel2 = make_relation_id(bak_id, "BACKUP_SUPPLIER_FOR", comp_id)
            relations_map.setdefault(
                rel2,
                {
                    "relation_id": rel2,
                    "tenant_id": tenant_id,
                    "subject_id": bak_id,
                    "predicate": "BACKUP_SUPPLIER_FOR",
                    "object_id": comp_id,
                    "confidence": 1.0,
                    "evidence_quote": f"{crow['backup_supplier_id']} is qualified backup supplier for {crow['component_id']}",
                    "source_doc_id": "MASTER-ERP",
                },
            )

        for _, brow in bom_df.iterrows():
            comp_id, _, _, _ = resolve_entity(
                brow["component_id"], "COMPONENT", brow["component_id"]
            )
            prod_id, _, _, _ = resolve_entity(
                brow["product_id"], "PRODUCT", brow["product_id"]
            )
            rel_bom = make_relation_id(comp_id, "USED_IN_PRODUCT", prod_id)
            relations_map.setdefault(
                rel_bom,
                {
                    "relation_id": rel_bom,
                    "tenant_id": tenant_id,
                    "subject_id": comp_id,
                    "predicate": "USED_IN_PRODUCT",
                    "object_id": prod_id,
                    "confidence": 1.0,
                    "evidence_quote": f"{brow['component_id']} is required ({brow['qty_per_unit']} units) in BOM of {brow['product_id']}",
                    "source_doc_id": "MASTER-BOM",
                },
            )


def build_and_persist_knowledge_graph() -> dict[str, Any]:
    """Menjalankan ekstraksi KG tervalidasi Pydantic dari 12 dokumen korporat + Entity Resolution ke PostgreSQL."""
    init_db()
    docs_path = settings.docs_data_dir / "corp_docs.json"
    with docs_path.open("r", encoding="utf-8") as f:
        corp_docs = json.load(f)

    tenant_id = settings.default_tenant_id
    entities_map: dict[str, dict[str, Any]] = {}
    relations_map: dict[str, dict[str, Any]] = {}
    provider_usage: dict[str, int] = {}

    for idx, doc in enumerate(corp_docs):
        doc_id = doc["doc_id"]
        user_prompt = (
            f"Document ID: {doc_id}\n"
            f"Title: {doc['title']}\n"
            f"Type: {doc['doc_type']}\n"
            f"Content:\n{doc['content']}"
        )
        extracted, provider_used = invoke_structured_with_failover(
            system_prompt=EXTRACTION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            schema=DocumentExtractionResult,
            task_tier="fast",
            temperature=0.0,
            schema_example=KG_SCHEMA_EXAMPLE,
        )
        provider_usage[provider_used] = provider_usage.get(provider_used, 0) + 1

        for ent in extracted.entities:
            ent_id, canon_name, canon_type, canon_code = resolve_entity(
                ent.name, ent.entity_type, ent.code
            )
            if ent_id not in entities_map:
                entities_map[ent_id] = {
                    "entity_id": ent_id,
                    "tenant_id": tenant_id,
                    "entity_name": canon_name,
                    "entity_type": canon_type,
                    "canonical_code": canon_code,
                    "description": ent.description or canon_name,
                    "source_doc_id": doc_id,
                }

        for rel in extracted.relations:
            subj_id, subj_name, subj_type, subj_code = resolve_entity(rel.subject)
            obj_id, obj_name, obj_type, obj_code = resolve_entity(rel.object)
            if subj_id == obj_id:
                continue

            entities_map.setdefault(
                subj_id,
                {
                    "entity_id": subj_id,
                    "tenant_id": tenant_id,
                    "entity_name": subj_name,
                    "entity_type": subj_type,
                    "canonical_code": subj_code,
                    "description": subj_name,
                    "source_doc_id": doc_id,
                },
            )
            entities_map.setdefault(
                obj_id,
                {
                    "entity_id": obj_id,
                    "tenant_id": tenant_id,
                    "entity_name": obj_name,
                    "entity_type": obj_type,
                    "canonical_code": obj_code,
                    "description": obj_name,
                    "source_doc_id": doc_id,
                },
            )

            pred = _normalize_predicate(rel.predicate)
            rel_id = make_relation_id(subj_id, pred, obj_id)
            if rel_id not in relations_map:
                relations_map[rel_id] = {
                    "relation_id": rel_id,
                    "tenant_id": tenant_id,
                    "subject_id": subj_id,
                    "predicate": pred,
                    "object_id": obj_id,
                    "confidence": round(float(rel.confidence), 3),
                    "evidence_quote": rel.evidence_quote.strip()
                    or f"Extracted from {doc_id}",
                    "source_doc_id": doc_id,
                }

        if idx < len(corp_docs) - 1:
            time.sleep(1.0)

    _seed_canonical_and_bom_backbone(entities_map, relations_map, tenant_id)

    with SessionLocal() as session:
        for ent_data in entities_map.values():
            session.merge(KGEntity(**ent_data))
        session.flush()

        for rel_data in relations_map.values():
            session.merge(KGRelation(**rel_data))
        session.commit()

    snapshot = {
        "tenant_id": tenant_id,
        "total_entities": len(entities_map),
        "total_relations": len(relations_map),
        "provider_usage": provider_usage,
        "entities": list(entities_map.values()),
        "relations": list(relations_map.values()),
    }
    settings.curated_data_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = settings.curated_data_dir / "kg_snapshot.json"
    with snapshot_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    return {
        "total_documents_processed": len(corp_docs),
        "total_canonical_entities": len(entities_map),
        "total_deduplicated_relations": len(relations_map),
        "llm_provider_usage": provider_usage,
        "snapshot_path": str(snapshot_path),
    }


if __name__ == "__main__":
    summary = build_and_persist_knowledge_graph()
    print(
        "=== Fase 5 Automated Knowledge Graph Extraction & Entity Resolution Selesai ==="
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
