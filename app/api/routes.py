import json
from typing import Any, Generator
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.agents.state import SwarmState
from app.agents.swarm import nexuscore_swarm_app
from app.api.schemas import HITLDecisionRequest, InvestigateRequest, SimulationRequest
from app.core.config import get_settings
from app.ml.predictor import get_high_risk_components_summary
from app.rag.hybrid_graphrag import get_knowledge_graph
from app.security.audit_hitl import (
    create_hitl_ticket,
    get_recent_audit_logs,
    list_hitl_tickets,
    record_audit_event,
    resolve_hitl_ticket,
    verify_audit_chain,
)
from app.security.guardrails import (
    enforce_rbac_and_tenant,
    inspect_prompt_security,
    redact_sensitive_pii,
)
from app.security.secured_runner import execute_secured_investigation
from app.sim.monte_carlo import run_monte_carlo_disruption_sim
from app.sim.optimizer import evaluate_mitigation_strategies

settings = get_settings()
router = APIRouter(prefix="/api", tags=["NexusCore Enterprise API"])


def _format_sse(event_name: str, data: dict[str, Any]) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/health")
def health_check() -> dict[str, Any]:
    """Memeriksa status layanan backend, model ML, dan integritas rantai audit SHA-256."""
    meta_path = settings.models_registry_dir / "model_metadata.json"
    ml_ready = meta_path.exists()
    chain_status = verify_audit_chain(settings.default_tenant_id)
    return {
        "status": "HEALTHY",
        "service": "NexusCore AI Enterprise Supply Chain Platform",
        "tenant_default": settings.default_tenant_id,
        "ml_models_registered": ml_ready,
        "audit_chain_valid": chain_status["is_chain_valid"],
        "audit_records_count": chain_status["total_records"],
    }


@router.get("/overview")
def get_executive_overview(
    tenant_id: str = Query(default="TENANT-APEX-GLOBAL"),
    user_role: str = Query(default="Analyst"),
) -> dict[str, Any]:
    """Mengambil ringkasan eksekutif untuk dashboard War Room (inventori kritis, PageRank KG, HITL, & Audit)."""
    try:
        enforce_rbac_and_tenant(
            user_role=user_role,
            required_permission="read_dashboard",
            requested_tenant_id=tenant_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    wh_id_risks = get_high_risk_components_summary("WH-ID")
    kg = get_knowledge_graph(tenant_id)
    default_subgraph = kg.traverse_multi_hop(
        seed_entity_ids=[
            "ENT-PORT-KAOHSIUNG",
            "ENT-SUP-001",
            "ENT-CMP-001",
            "ENT-POL-COV-FIN-01",
        ],
        max_hops=2,
        max_triples=24,
    )
    tickets = list_hitl_tickets(tenant_id=tenant_id, limit=15)
    audits = get_recent_audit_logs(tenant_id=tenant_id, limit=15)
    chain_integrity = verify_audit_chain(tenant_id=tenant_id)

    pending_count = sum(1 for t in tickets if t["status"] == "PENDING")
    breach_count = sum(1 for r in wh_id_risks if r.get("sop_sc04_breach"))

    return {
        "tenant_id": tenant_id,
        "kpis": {
            "wh_id_sop_sc04_alerts": breach_count,
            "pending_hitl_approvals": pending_count,
            "covenant_min_margin_pct": settings.covenant_min_gross_margin_pct,
            "hitl_threshold_usd": settings.hitl_approval_threshold_usd,
            "audit_chain_valid": chain_integrity["is_chain_valid"],
        },
        "wh_id_inventory_risks": wh_id_risks,
        "systemic_bottlenecks": kg.get_top_central_entities(top_n=6),
        "initial_cytoscape": default_subgraph["cytoscape"],
        "hitl_tickets": tickets,
        "recent_audit_logs": audits,
        "audit_chain_integrity": chain_integrity,
    }


@router.post("/investigate")
def investigate_supply_chain(payload: InvestigateRequest) -> dict[str, Any]:
    """Menjalankan investigasi Multi-Agent Swarm secara sinkron dengan perlindungan RBAC & Guardrails."""
    try:
        return execute_secured_investigation(
            query=payload.query,
            tenant_id=payload.tenant_id,
            user_id=payload.user_id,
            user_role=payload.user_role,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Swarm execution error: {exc}"
        ) from exc


@router.post("/investigate/stream")
def investigate_supply_chain_stream(payload: InvestigateRequest) -> StreamingResponse:
    """Streaming Server-Sent Events (SSE) real-time untuk setiap tahapan eksekusi agen LangGraph."""
    try:
        enforce_rbac_and_tenant(
            user_role=payload.user_role,
            required_permission="run_investigation",
            requested_tenant_id=payload.tenant_id,
        )
    except PermissionError as exc:
        record_audit_event(
            tenant_id=settings.default_tenant_id,
            user_id=payload.user_id,
            user_role=payload.user_role,
            action="SWARM_SSE_STREAM",
            status="BLOCKED_RBAC",
            details={"requested_tenant": payload.tenant_id, "reason": str(exc)},
        )
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    sec_check = inspect_prompt_security(payload.query)
    if not sec_check.allowed:
        record_audit_event(
            tenant_id=payload.tenant_id,
            user_id=payload.user_id,
            user_role=payload.user_role,
            action="SWARM_SSE_STREAM",
            status="BLOCKED_GUARDRAIL",
            details={
                "matched_rule": sec_check.matched_rule,
                "reason": sec_check.blocked_reason,
            },
        )
        raise HTTPException(
            status_code=400,
            detail=sec_check.blocked_reason
            or "Permintaan diblokir oleh Guardrail keamanan.",
        )

    def event_generator() -> Generator[str, None, None]:
        initial_state: SwarmState = {
            "query": sec_check.sanitized_text,
            "tenant_id": payload.tenant_id,
            "user_id": payload.user_id,
            "user_role": payload.user_role,
            "plan": {},
            "worker_results": [],
            "critic_review": {},
            "revision_count": 0,
            "final_response": {},
            "trace_events": [],
        }

        collected_traces: list[dict[str, Any]] = []
        final_result: dict[str, Any] = {}

        try:
            yield _format_sse(
                "started",
                {
                    "message": "Guardrails & RBAC terverifikasi. Mengaktifkan Hierarchical Multi-Agent Swarm...",
                    "tenant_id": payload.tenant_id,
                },
            )

            for update in nexuscore_swarm_app.stream(
                initial_state, stream_mode="updates"
            ):
                for _, node_output in update.items():
                    if not isinstance(node_output, dict):
                        continue
                    for trace_item in node_output.get("trace_events", []):
                        collected_traces.append(trace_item)
                        yield _format_sse("trace", trace_item)
                    if (
                        "final_response" in node_output
                        and node_output["final_response"]
                    ):
                        final_result = node_output["final_response"]

            if not final_result:
                yield _format_sse(
                    "error", {"detail": "Swarm selesai tanpa output akhir."}
                )
                return

            clean_brief, out_redactions = redact_sensitive_pii(
                final_result.get("executive_brief_markdown", "")
            )
            final_result["executive_brief_markdown"] = clean_brief
            final_result["execution_trace"] = collected_traces

            trigger_reasons: list[str] = []
            if final_result.get("requires_hitl_approval"):
                trigger_reasons.append(
                    f"SOP-SC-04: Estimasi biaya mitigasi USD {final_result['estimated_cost_usd']:,.2f} melebihi batas USD {settings.hitl_approval_threshold_usd:,.2f}."
                )
            if final_result.get("covenant_breach_risk"):
                trigger_reasons.append(
                    f"COV-FIN-01: Risiko margin turun di bawah batas kovenan utang {settings.covenant_min_gross_margin_pct:.1f}%."
                )

            hitl_ticket = None
            if trigger_reasons:
                best_strat = final_result.get("recommended_strategy") or {}
                hitl_ticket = create_hitl_ticket(
                    tenant_id=payload.tenant_id,
                    user_id=payload.user_id,
                    user_role=payload.user_role,
                    query=sec_check.sanitized_text,
                    strategy_id=best_strat.get("strategy_id", "STRAT-UNKNOWN"),
                    strategy_name=best_strat.get(
                        "strategy_name", "Emergency Mitigation"
                    ),
                    estimated_cost_usd=float(
                        final_result.get("estimated_cost_usd", 0.0)
                    ),
                    projected_margin_pct=float(
                        final_result.get("projected_margin_pct", 0.0)
                    ),
                    covenant_breach_risk=bool(
                        final_result.get("covenant_breach_risk", False)
                    ),
                    trigger_reasons=trigger_reasons,
                )

            audit_record = record_audit_event(
                tenant_id=payload.tenant_id,
                user_id=payload.user_id,
                user_role=payload.user_role,
                action="SWARM_SSE_STREAM",
                status="COMPLETED",
                details={
                    "strategy_id": (final_result.get("recommended_strategy") or {}).get(
                        "strategy_id"
                    ),
                    "estimated_cost_usd": final_result.get("estimated_cost_usd"),
                    "hitl_ticket_id": hitl_ticket["ticket_id"] if hitl_ticket else None,
                    "pii_redacted": sec_check.pii_redacted_count + out_redactions,
                },
            )

            final_result["hitl_ticket"] = hitl_ticket
            final_result["audit_record"] = audit_record
            yield _format_sse("complete", final_result)
        except Exception as exc:
            yield _format_sse("error", {"detail": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/simulate")
def simulate_what_if(payload: SimulationRequest) -> dict[str, Any]:
    """Menjalankan simulasi interaktif What-If Monte Carlo 1.000 iterasi & komparasi strategi."""
    try:
        enforce_rbac_and_tenant(
            user_role=payload.user_role,
            required_permission="run_simulation",
            requested_tenant_id=payload.tenant_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    try:
        custom_mc = run_monte_carlo_disruption_sim(
            component_id=payload.component_id,
            warehouse_code=payload.warehouse_code,
            port_congestion_index=payload.port_congestion_index,
            tariff_surcharge_pct=payload.tariff_surcharge_pct,
            air_freight_share=payload.air_freight_share,
            backup_allocation_share=payload.backup_allocation_share,
            n_iterations=1000,
        )
        strategy_ranking = evaluate_mitigation_strategies(
            component_id=payload.component_id,
            warehouse_code=payload.warehouse_code,
            port_congestion_index=payload.port_congestion_index,
            tariff_surcharge_pct=payload.tariff_surcharge_pct,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    record_audit_event(
        tenant_id=payload.tenant_id,
        user_id=payload.user_id,
        user_role=payload.user_role,
        action="MONTE_CARLO_WHAT_IF",
        status="COMPLETED",
        details={
            "component_id": payload.component_id,
            "port_congestion_index": payload.port_congestion_index,
            "p50_cost_usd": custom_mc["incremental_cost_usd"]["p50_median"],
        },
    )

    return {
        "custom_simulation": custom_mc,
        "strategy_comparison": strategy_ranking,
    }


@router.get("/hitl/tickets")
def get_hitl_tickets(
    tenant_id: str = Query(default="TENANT-APEX-GLOBAL"),
    user_role: str = Query(default="Analyst"),
) -> dict[str, Any]:
    try:
        enforce_rbac_and_tenant(
            user_role=user_role,
            required_permission="read_dashboard",
            requested_tenant_id=tenant_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return {
        "tenant_id": tenant_id,
        "tickets": list_hitl_tickets(tenant_id=tenant_id, limit=25),
    }


@router.post("/hitl/tickets/{ticket_id}/resolve")
def resolve_hitl_ticket_endpoint(
    ticket_id: str, payload: HITLDecisionRequest
) -> dict[str, Any]:
    """Menyetujui atau menolak tiket HITL dengan penegakan ketat peran SupplyChainDirector/Admin."""
    try:
        return resolve_hitl_ticket(
            ticket_id=ticket_id,
            actor_user_id=payload.actor_user_id,
            actor_role=payload.actor_role,
            decision=payload.decision,
            notes=payload.notes,
            tenant_id=payload.tenant_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/audit/logs")
def get_audit_logs_endpoint(
    tenant_id: str = Query(default="TENANT-APEX-GLOBAL"),
    user_role: str = Query(default="Analyst"),
) -> dict[str, Any]:
    try:
        enforce_rbac_and_tenant(
            user_role=user_role,
            required_permission="view_audit",
            requested_tenant_id=tenant_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return {
        "tenant_id": tenant_id,
        "chain_integrity": verify_audit_chain(tenant_id=tenant_id),
        "logs": get_recent_audit_logs(tenant_id=tenant_id, limit=30),
    }
