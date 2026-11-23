from typing import Any
from app.agents.swarm import run_swarm_investigation
from app.core.config import get_settings
from app.security.audit_hitl import create_hitl_ticket, record_audit_event
from app.security.guardrails import (
    enforce_rbac_and_tenant,
    inspect_prompt_security,
    redact_sensitive_pii,
)

settings = get_settings()


def execute_secured_investigation(
    query: str,
    tenant_id: str | None = None,
    user_id: str = "USR-ANALYST-01",
    user_role: str = "Analyst",
) -> dict[str, Any]:
    """Menjalankan investigasi Swarm di bawah perlindungan RBAC, Guardrails, HITL Queue, dan Audit Log."""
    target_tenant = tenant_id or settings.default_tenant_id

    # 1. Validasi RBAC & Tenant Isolation
    try:
        enforce_rbac_and_tenant(
            user_role=user_role,
            required_permission="run_investigation",
            requested_tenant_id=target_tenant,
        )
    except PermissionError as exc:
        record_audit_event(
            tenant_id=settings.default_tenant_id,
            user_id=user_id,
            user_role=user_role,
            action="SWARM_INVESTIGATION",
            status="BLOCKED_RBAC",
            details={"requested_tenant": target_tenant, "reason": str(exc)},
        )
        raise

    # 2. Validasi OWASP GenAI Prompt Injection & PII Redaction
    sec_check = inspect_prompt_security(query)
    if not sec_check.allowed:
        record_audit_event(
            tenant_id=target_tenant,
            user_id=user_id,
            user_role=user_role,
            action="SWARM_INVESTIGATION",
            status="BLOCKED_GUARDRAIL",
            details={
                "matched_rule": sec_check.matched_rule,
                "reason": sec_check.blocked_reason,
            },
        )
        raise ValueError(
            sec_check.blocked_reason or "Kueri diblokir oleh kebijakan keamanan."
        )

    # 3. Jalankan Hierarchical Multi-Agent Swarm
    result = run_swarm_investigation(
        query=sec_check.sanitized_text,
        tenant_id=target_tenant,
        user_id=user_id,
        user_role=user_role,
    )

    # 4. Sensor potensi PII pada keluaran narasi eksekutif
    clean_brief, out_redactions = redact_sensitive_pii(
        result.get("executive_brief_markdown", "")
    )
    result["executive_brief_markdown"] = clean_brief

    # 5. Otomatis buat tiket HITL jika biaya > $50,000 atau risiko pelanggaran kovenan COV-FIN-01
    trigger_reasons: list[str] = []
    if result.get("requires_hitl_approval"):
        trigger_reasons.append(
            f"SOP-SC-04: Estimasi biaya mitigasi USD {result['estimated_cost_usd']:,.2f} melebihi batas otoritas otomatis USD {settings.hitl_approval_threshold_usd:,.2f}."
        )
    if result.get("covenant_breach_risk"):
        trigger_reasons.append(
            f"COV-FIN-01: Risiko margin produk/konsolidasi turun di bawah ambang batas kovenan utang {settings.covenant_min_gross_margin_pct:.1f}%."
        )

    hitl_ticket = None
    if trigger_reasons:
        best_strat = result.get("recommended_strategy") or {}
        hitl_ticket = create_hitl_ticket(
            tenant_id=target_tenant,
            user_id=user_id,
            user_role=user_role,
            query=sec_check.sanitized_text,
            strategy_id=best_strat.get("strategy_id", "STRAT-UNKNOWN"),
            strategy_name=best_strat.get("strategy_name", "Emergency Mitigation"),
            estimated_cost_usd=float(result.get("estimated_cost_usd", 0.0)),
            projected_margin_pct=float(result.get("projected_margin_pct", 0.0)),
            covenant_breach_risk=bool(result.get("covenant_breach_risk", False)),
            trigger_reasons=trigger_reasons,
        )

    # 6. Catat hasil eksekusi ke SHA-256 Hash-Chained Audit Log
    audit_record = record_audit_event(
        tenant_id=target_tenant,
        user_id=user_id,
        user_role=user_role,
        action="SWARM_INVESTIGATION",
        status="COMPLETED",
        details={
            "strategy_id": (result.get("recommended_strategy") or {}).get(
                "strategy_id"
            ),
            "estimated_cost_usd": result.get("estimated_cost_usd"),
            "hitl_ticket_id": hitl_ticket["ticket_id"] if hitl_ticket else None,
            "pii_redacted": sec_check.pii_redacted_count + out_redactions,
        },
    )

    result["hitl_ticket"] = hitl_ticket
    result["audit_record"] = audit_record
    return result
