import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, Float, Integer, String, Text, inspect, select, text
from sqlalchemy.orm import declarative_base
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.security.guardrails import enforce_rbac_and_tenant

settings = get_settings()
SecurityBase = declarative_base()

GENESIS_HASH = "0" * 64


class AuditLogEntry(SecurityBase):
    __tablename__ = "nc_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String(64), unique=True, nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    timestamp_iso = Column(String(64), nullable=False)
    user_id = Column(String(64), nullable=False)
    user_role = Column(String(64), nullable=False)
    action = Column(String(128), nullable=False)
    status = Column(String(32), nullable=False)
    details_json = Column(Text, nullable=False)
    prev_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)


class HITLApprovalTicket(SecurityBase):
    __tablename__ = "nc_hitl_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(64), unique=True, nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    created_at_iso = Column(String(64), nullable=False)
    requested_by_user_id = Column(String(64), nullable=False)
    requested_by_role = Column(String(64), nullable=False)
    query_summary = Column(Text, nullable=False)
    recommended_strategy_id = Column(String(128), nullable=False)
    recommended_strategy_name = Column(Text, nullable=False)
    estimated_cost_usd = Column(Float, nullable=False)
    projected_margin_pct = Column(Float, nullable=False)
    covenant_breach_risk = Column(Integer, nullable=False, default=0)
    trigger_reasons_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="PENDING")
    resolved_by_user_id = Column(String(64), nullable=True)
    resolved_by_role = Column(String(64), nullable=True)
    resolved_at_iso = Column(String(64), nullable=True)
    resolution_notes = Column(Text, nullable=True)


def init_security_tables() -> None:
    with SessionLocal() as session:
        bind = session.get_bind()
        inspector = inspect(bind)

        if inspector.has_table("nc_audit_logs"):
            audit_cols = {c["name"] for c in inspector.get_columns("nc_audit_logs")}
            if "id" not in audit_cols or "prev_hash" not in audit_cols:
                session.execute(text("DROP TABLE IF EXISTS nc_audit_logs CASCADE"))
                session.commit()

        if inspector.has_table("nc_hitl_approvals"):
            hitl_cols = {c["name"] for c in inspector.get_columns("nc_hitl_approvals")}
            if "id" not in hitl_cols or "trigger_reasons_json" not in hitl_cols:
                session.execute(text("DROP TABLE IF EXISTS nc_hitl_approvals CASCADE"))
                session.commit()

        SecurityBase.metadata.create_all(bind=bind)


def _compute_chain_hash(
    prev_hash: str,
    timestamp_iso: str,
    tenant_id: str,
    user_id: str,
    action: str,
    status: str,
    details_json: str,
) -> str:
    payload = f"{prev_hash}|{timestamp_iso}|{tenant_id}|{user_id}|{action}|{status}|{details_json}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record_audit_event(
    tenant_id: str,
    user_id: str,
    user_role: str,
    action: str,
    status: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    """Mencatat peristiwa tata kelola & keamanan dengan rantai hash SHA-256."""
    init_security_tables()
    ts_iso = datetime.now(timezone.utc).isoformat()
    audit_id = f"AUD-{uuid.uuid4().hex[:12].upper()}"
    details_str = json.dumps(details, sort_keys=True, ensure_ascii=False)

    with SessionLocal() as session:
        last_entry = session.execute(
            select(AuditLogEntry)
            .where(AuditLogEntry.tenant_id == tenant_id)
            .order_by(AuditLogEntry.id.desc())
            .limit(1)
        ).scalar_one_or_none()

        prev_hash = last_entry.event_hash if last_entry else GENESIS_HASH
        event_hash = _compute_chain_hash(
            prev_hash=prev_hash,
            timestamp_iso=ts_iso,
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            status=status,
            details_json=details_str,
        )

        entry = AuditLogEntry(
            audit_id=audit_id,
            tenant_id=tenant_id,
            timestamp_iso=ts_iso,
            user_id=user_id,
            user_role=user_role,
            action=action,
            status=status,
            details_json=details_str,
            prev_hash=prev_hash,
            event_hash=event_hash,
        )
        session.add(entry)
        session.commit()

    return {
        "audit_id": audit_id,
        "tenant_id": tenant_id,
        "timestamp_iso": ts_iso,
        "action": action,
        "status": status,
        "prev_hash": prev_hash,
        "event_hash": event_hash,
    }


def verify_audit_chain(tenant_id: str | None = None) -> dict[str, Any]:
    """Memverifikasi integritas seluruh rantai hash SHA-256 pada tabel audit PostgreSQL."""
    init_security_tables()
    target_tenant = tenant_id or settings.default_tenant_id

    with SessionLocal() as session:
        rows = (
            session.execute(
                select(AuditLogEntry)
                .where(AuditLogEntry.tenant_id == target_tenant)
                .order_by(AuditLogEntry.id.asc())
            )
            .scalars()
            .all()
        )

    expected_prev = GENESIS_HASH
    for row in rows:
        if row.prev_hash != expected_prev:
            return {
                "tenant_id": target_tenant,
                "total_records": len(rows),
                "is_chain_valid": False,
                "corrupted_audit_id": row.audit_id,
            }
        recomputed = _compute_chain_hash(
            prev_hash=row.prev_hash,
            timestamp_iso=row.timestamp_iso,
            tenant_id=row.tenant_id,
            user_id=row.user_id,
            action=row.action,
            status=row.status,
            details_json=row.details_json,
        )
        if recomputed != row.event_hash:
            return {
                "tenant_id": target_tenant,
                "total_records": len(rows),
                "is_chain_valid": False,
                "corrupted_audit_id": row.audit_id,
            }
        expected_prev = row.event_hash

    return {
        "tenant_id": target_tenant,
        "total_records": len(rows),
        "is_chain_valid": True,
        "latest_head_hash": expected_prev,
    }


def get_recent_audit_logs(
    tenant_id: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    init_security_tables()
    target_tenant = tenant_id or settings.default_tenant_id
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(AuditLogEntry)
                .where(AuditLogEntry.tenant_id == target_tenant)
                .order_by(AuditLogEntry.id.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
    return [
        {
            "audit_id": r.audit_id,
            "timestamp_iso": r.timestamp_iso,
            "user_id": r.user_id,
            "user_role": r.user_role,
            "action": r.action,
            "status": r.status,
            "details": json.loads(r.details_json),
            "event_hash": r.event_hash,
        }
        for r in rows
    ]


def create_hitl_ticket(
    tenant_id: str,
    user_id: str,
    user_role: str,
    query: str,
    strategy_id: str,
    strategy_name: str,
    estimated_cost_usd: float,
    projected_margin_pct: float,
    covenant_breach_risk: bool,
    trigger_reasons: list[str],
) -> dict[str, Any]:
    """Membuat tiket persetujuan Human-in-the-Loop (HITL) baru di PostgreSQL."""
    init_security_tables()
    ticket_id = f"HITL-{uuid.uuid4().hex[:10].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()

    ticket = HITLApprovalTicket(
        ticket_id=ticket_id,
        tenant_id=tenant_id,
        created_at_iso=now_iso,
        requested_by_user_id=user_id,
        requested_by_role=user_role,
        query_summary=query[:500],
        recommended_strategy_id=strategy_id,
        recommended_strategy_name=strategy_name,
        estimated_cost_usd=round(float(estimated_cost_usd), 2),
        projected_margin_pct=round(float(projected_margin_pct), 2),
        covenant_breach_risk=1 if covenant_breach_risk else 0,
        trigger_reasons_json=json.dumps(trigger_reasons, ensure_ascii=False),
        status="PENDING",
    )
    with SessionLocal() as session:
        session.add(ticket)
        session.commit()

    record_audit_event(
        tenant_id=tenant_id,
        user_id=user_id,
        user_role=user_role,
        action="HITL_TICKET_CREATED",
        status="PENDING_APPROVAL",
        details={
            "ticket_id": ticket_id,
            "strategy_id": strategy_id,
            "estimated_cost_usd": round(float(estimated_cost_usd), 2),
            "trigger_reasons": trigger_reasons,
        },
    )

    return {
        "ticket_id": ticket_id,
        "tenant_id": tenant_id,
        "status": "PENDING",
        "created_at_iso": now_iso,
        "recommended_strategy_id": strategy_id,
        "recommended_strategy_name": strategy_name,
        "estimated_cost_usd": round(float(estimated_cost_usd), 2),
        "projected_margin_pct": round(float(projected_margin_pct), 2),
        "covenant_breach_risk": covenant_breach_risk,
        "trigger_reasons": trigger_reasons,
        "required_approver_role": "SupplyChainDirector",
    }


def resolve_hitl_ticket(
    ticket_id: str,
    actor_user_id: str,
    actor_role: str,
    decision: str,
    notes: str = "",
    tenant_id: str | None = None,
) -> dict[str, Any]:
    """Menyetujui atau menolak tiket HITL dengan penegakan RBAC ketat (SupplyChainDirector/Admin)."""
    init_security_tables()
    target_tenant = tenant_id or settings.default_tenant_id
    normalized_decision = decision.upper().strip()
    if normalized_decision not in {"APPROVED", "REJECTED"}:
        raise ValueError("Keputusan HITL harus 'APPROVED' atau 'REJECTED'.")

    try:
        enforce_rbac_and_tenant(
            user_role=actor_role,
            required_permission="approve_hitl",
            requested_tenant_id=target_tenant,
        )
    except PermissionError as exc:
        record_audit_event(
            tenant_id=target_tenant,
            user_id=actor_user_id,
            user_role=actor_role,
            action="HITL_APPROVAL_ATTEMPT",
            status="DENIED_RBAC",
            details={"ticket_id": ticket_id, "reason": str(exc)},
        )
        raise

    now_iso = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        ticket = session.execute(
            select(HITLApprovalTicket).where(
                HITLApprovalTicket.ticket_id == ticket_id,
                HITLApprovalTicket.tenant_id == target_tenant,
            )
        ).scalar_one_or_none()

        if ticket is None:
            raise ValueError(f"Tiket HITL tidak ditemukan: {ticket_id}")

        ticket.status = normalized_decision
        ticket.resolved_by_user_id = actor_user_id
        ticket.resolved_by_role = actor_role
        ticket.resolved_at_iso = now_iso
        ticket.resolution_notes = notes
        session.commit()

        result_payload = {
            "ticket_id": ticket.ticket_id,
            "tenant_id": ticket.tenant_id,
            "status": ticket.status,
            "estimated_cost_usd": ticket.estimated_cost_usd,
            "resolved_by_user_id": actor_user_id,
            "resolved_by_role": actor_role,
            "resolved_at_iso": now_iso,
            "resolution_notes": notes,
        }

    record_audit_event(
        tenant_id=target_tenant,
        user_id=actor_user_id,
        user_role=actor_role,
        action=f"HITL_TICKET_{normalized_decision}",
        status="SUCCESS",
        details=result_payload,
    )
    return result_payload


def list_hitl_tickets(
    tenant_id: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    init_security_tables()
    target_tenant = tenant_id or settings.default_tenant_id
    with SessionLocal() as session:
        rows = (
            session.execute(
                select(HITLApprovalTicket)
                .where(HITLApprovalTicket.tenant_id == target_tenant)
                .order_by(HITLApprovalTicket.id.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
    return [
        {
            "ticket_id": r.ticket_id,
            "created_at_iso": r.created_at_iso,
            "requested_by_user_id": r.requested_by_user_id,
            "requested_by_role": r.requested_by_role,
            "query_summary": r.query_summary,
            "recommended_strategy_id": r.recommended_strategy_id,
            "recommended_strategy_name": r.recommended_strategy_name,
            "estimated_cost_usd": r.estimated_cost_usd,
            "projected_margin_pct": r.projected_margin_pct,
            "covenant_breach_risk": bool(r.covenant_breach_risk),
            "trigger_reasons": json.loads(r.trigger_reasons_json),
            "status": r.status,
            "resolved_by_user_id": r.resolved_by_user_id,
            "resolved_by_role": r.resolved_by_role,
            "resolved_at_iso": r.resolved_at_iso,
            "resolution_notes": r.resolution_notes,
        }
        for r in rows
    ]
