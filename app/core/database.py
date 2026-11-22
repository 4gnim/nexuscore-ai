from collections.abc import Generator
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.core.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Base ORM class untuk seluruh tabel NexusCore AI."""


def _build_engine():
    db_url = settings.supabase_db_url
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            future=True,
        )
    return create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
        future=True,
    )


engine = _build_engine()
SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
)


# ==============================================================================
# 1. RELATIONAL SUPPLY CHAIN & ERP TABLES (PREFIX: nc_)
# ==============================================================================


class Supplier(Base):
    __tablename__ = "nc_suppliers"

    supplier_id = Column(String(32), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    supplier_name = Column(String(160), nullable=False)
    country = Column(String(80), nullable=False)
    port_hub = Column(String(120), nullable=False)
    tier = Column(String(20), nullable=False)
    financial_health_score = Column(Float, nullable=False)
    geopolitical_risk_index = Column(Float, nullable=False)
    esg_score = Column(Float, nullable=False)
    contracted_lead_time_days = Column(Integer, nullable=False)
    unit_cost_multiplier = Column(Float, nullable=False)
    monthly_capacity_units = Column(Integer, nullable=False)
    is_approved_backup = Column(Boolean, nullable=False, default=True)


class Component(Base):
    __tablename__ = "nc_components"

    component_id = Column(String(32), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    component_name = Column(String(160), nullable=False)
    category = Column(String(80), nullable=False)
    primary_supplier_id = Column(
        String(32), ForeignKey("nc_suppliers.supplier_id"), nullable=False
    )
    backup_supplier_id = Column(
        String(32), ForeignKey("nc_suppliers.supplier_id"), nullable=False
    )
    criticality = Column(String(20), nullable=False)
    standard_unit_cost_usd = Column(Float, nullable=False)
    hs_code = Column(String(32), nullable=False)
    base_tariff_pct = Column(Float, nullable=False)


class Product(Base):
    __tablename__ = "nc_products"

    product_id = Column(String(32), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    product_name = Column(String(160), nullable=False)
    product_line = Column(String(80), nullable=False)
    selling_price_usd = Column(Float, nullable=False)
    standard_cogs_usd = Column(Float, nullable=False)
    gross_margin_pct = Column(Float, nullable=False)
    monthly_demand_units = Column(Integer, nullable=False)


class BOM(Base):
    __tablename__ = "nc_bom"

    bom_id = Column(String(32), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    product_id = Column(
        String(32), ForeignKey("nc_products.product_id"), nullable=False
    )
    component_id = Column(
        String(32), ForeignKey("nc_components.component_id"), nullable=False
    )
    qty_per_unit = Column(Integer, nullable=False)
    is_single_source_risk = Column(Boolean, nullable=False, default=False)


class Inventory(Base):
    __tablename__ = "nc_inventory"

    inventory_id = Column(String(32), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    warehouse_code = Column(String(32), nullable=False)
    component_id = Column(
        String(32), ForeignKey("nc_components.component_id"), nullable=False
    )
    on_hand_qty = Column(Integer, nullable=False)
    reserved_qty = Column(Integer, nullable=False)
    safety_stock_qty = Column(Integer, nullable=False)
    daily_burn_rate = Column(Float, nullable=False)
    holding_cost_per_day_usd = Column(Float, nullable=False)


class ShipmentHistory(Base):
    __tablename__ = "nc_shipments_history"

    shipment_id = Column(String(32), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    supplier_id = Column(
        String(32), ForeignKey("nc_suppliers.supplier_id"), nullable=False, index=True
    )
    component_id = Column(
        String(32), ForeignKey("nc_components.component_id"), nullable=False, index=True
    )
    origin_port = Column(String(120), nullable=False)
    destination_hub = Column(String(32), nullable=False)
    transport_mode = Column(String(32), nullable=False)
    order_date = Column(Date, nullable=False)
    promised_date = Column(Date, nullable=False)
    actual_arrival_date = Column(Date, nullable=False)
    order_qty = Column(Integer, nullable=False)
    unit_price_usd = Column(Float, nullable=False)
    freight_cost_usd = Column(Float, nullable=False)
    tariff_paid_usd = Column(Float, nullable=False)
    port_congestion_index = Column(Float, nullable=False)
    weather_severity_index = Column(Float, nullable=False)
    supplier_health_at_order = Column(Float, nullable=False)
    delay_days = Column(Integer, nullable=False)
    is_delayed = Column(Integer, nullable=False)
    shipment_status = Column(String(32), nullable=False)


# ==============================================================================
# 2. KNOWLEDGE GRAPH TABLES (ENTITY & RELATION STORE)
# ==============================================================================


class KGEntity(Base):
    __tablename__ = "nc_kg_entities"

    entity_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    entity_name = Column(String(200), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    canonical_code = Column(String(64), nullable=True, index=True)
    description = Column(Text, nullable=True)
    source_doc_id = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class KGRelation(Base):
    __tablename__ = "nc_kg_relations"

    relation_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    subject_id = Column(
        String(64), ForeignKey("nc_kg_entities.entity_id"), nullable=False, index=True
    )
    predicate = Column(String(80), nullable=False, index=True)
    object_id = Column(
        String(64), ForeignKey("nc_kg_entities.entity_id"), nullable=False, index=True
    )
    confidence = Column(Float, nullable=False, default=1.0)
    evidence_quote = Column(Text, nullable=False)
    source_doc_id = Column(String(64), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# ==============================================================================
# 3. ENTERPRISE GOVERNANCE, HITL & APPEND-ONLY AUDIT LOG TABLES
# ==============================================================================


class AuditLog(Base):
    __tablename__ = "nc_audit_logs"

    audit_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    user_id = Column(String(80), nullable=False)
    user_role = Column(String(40), nullable=False)
    action_type = Column(String(64), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    decision_summary = Column(Text, nullable=True)
    security_status = Column(String(32), nullable=False, default="ALLOWED")
    hitl_required = Column(Boolean, nullable=False, default=False)
    estimated_cost_usd = Column(Float, nullable=True)
    citations_json = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class HITLApproval(Base):
    __tablename__ = "nc_hitl_approvals"

    approval_id = Column(String(64), primary_key=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    audit_id = Column(String(64), ForeignKey("nc_audit_logs.audit_id"), nullable=False)
    requested_by = Column(String(80), nullable=False)
    scenario_title = Column(String(200), nullable=False)
    mitigation_plan_json = Column(Text, nullable=False)
    incremental_cost_usd = Column(Float, nullable=False)
    projected_margin_pct = Column(Float, nullable=True)
    covenant_breach_risk = Column(Boolean, nullable=False, default=False)
    status = Column(String(24), nullable=False, default="PENDING", index=True)
    reviewed_by = Column(String(80), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)


Index(
    "ix_nc_kg_rel_tenant_subj_obj",
    KGRelation.tenant_id,
    KGRelation.subject_id,
    KGRelation.object_id,
)


def init_db() -> None:
    """Membuat seluruh tabel relasional, Knowledge Graph, dan Governance di database."""
    Base.metadata.create_all(bind=engine)


def check_db_connection() -> bool:
    """Memverifikasi konektivitas aktif ke Supabase PostgreSQL / SQLite."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        return result == 1


def get_db() -> Generator[Session, None, None]:
    """Dependency session database untuk FastAPI dan layanan internal."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
