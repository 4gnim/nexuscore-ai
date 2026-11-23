from decimal import Decimal
import re
from typing import Any
from fastmcp import FastMCP
from sqlalchemy import text
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.ml.predictor import (
    get_high_risk_components_summary,
    predict_component_stockout,
    predict_supplier_delay,
)
from app.rag.hybrid_graphrag import hybrid_graphrag_retrieve
from app.sim.monte_carlo import run_monte_carlo_disruption_sim
from app.sim.optimizer import evaluate_mitigation_strategies

settings = get_settings()
mcp = FastMCP("NexusCore-SupplyChain-MCP")

FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|GRANT|REVOKE|EXEC|EXECUTE|ATTACH|DETACH|PRAGMA)\b",
    re.IGNORECASE,
)


def _serialize_sql_value(val: Any) -> Any:
    if isinstance(val, Decimal):
        return float(val)
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return val


def execute_tenant_sql_query(
    sql_query: str,
    tenant_id: str | None = None,
    max_rows: int = 50,
) -> dict[str, Any]:
    """Menjalankan kueri SQL SELECT read-only dengan isolasi baris otomatis per tenant_id."""
    target_tenant = tenant_id or settings.default_tenant_id
    cleaned_sql = sql_query.strip().rstrip(";")

    if not re.match(r"^(SELECT|WITH)\b", cleaned_sql, re.IGNORECASE):
        raise ValueError("Hanya kueri SELECT / WITH read-only yang diizinkan.")
    if ";" in cleaned_sql:
        raise ValueError("Multi-statement SQL dilarang demi keamanan.")
    if FORBIDDEN_SQL_PATTERN.search(cleaned_sql):
        raise ValueError("Kata kunci DML/DDL terdeteksi dan diblokir oleh SQL Guard.")

    tenant_cte_prefix = """WITH
  nc_suppliers AS (SELECT * FROM nc_suppliers WHERE tenant_id = :tenant_id),
  nc_components AS (SELECT * FROM nc_components WHERE tenant_id = :tenant_id),
  nc_products AS (SELECT * FROM nc_products WHERE tenant_id = :tenant_id),
  nc_bom AS (SELECT * FROM nc_bom WHERE tenant_id = :tenant_id),
  nc_inventory AS (SELECT * FROM nc_inventory WHERE tenant_id = :tenant_id),
  nc_shipments_history AS (SELECT * FROM nc_shipments_history WHERE tenant_id = :tenant_id),
  suppliers AS (SELECT * FROM nc_suppliers WHERE tenant_id = :tenant_id),
  components AS (SELECT * FROM nc_components WHERE tenant_id = :tenant_id),
  products AS (SELECT * FROM nc_products WHERE tenant_id = :tenant_id),
  bom AS (SELECT * FROM nc_bom WHERE tenant_id = :tenant_id),
  inventory AS (SELECT * FROM nc_inventory WHERE tenant_id = :tenant_id),
  shipments_history AS (SELECT * FROM nc_shipments_history WHERE tenant_id = :tenant_id)
"""
    if re.match(r"^WITH\b", cleaned_sql, re.IGNORECASE):
        body_without_with = re.sub(
            r"^WITH\s+", "", cleaned_sql, count=1, flags=re.IGNORECASE
        )
        sandboxed_sql = f"{tenant_cte_prefix}, {body_without_with}"
    else:
        sandboxed_sql = f"{tenant_cte_prefix}{cleaned_sql}"

    with SessionLocal() as session:
        result = session.execute(text(sandboxed_sql), {"tenant_id": target_tenant})
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchmany(max_rows)]

    serialized_rows = [{k: _serialize_sql_value(v) for k, v in r.items()} for r in rows]

    return {
        "tenant_id": target_tenant,
        "row_count": len(serialized_rows),
        "columns": columns,
        "rows": serialized_rows,
    }


def verify_governance_and_compliance(
    incremental_cost_usd: float,
    projected_consolidated_margin_pct: float,
    worst_product_margin_pct: float | None = None,
    backup_esg_score: float = 90.0,
    days_of_supply_wh_id: float | None = None,
    is_critical_component: bool = True,
) -> dict[str, Any]:
    """Memverifikasi kepatuhan terhadap COV-FIN-01, SOP-SC-04, dan ESG-2026-03 secara deterministik."""
    covenant_floor = settings.covenant_min_gross_margin_pct
    hitl_limit = settings.hitl_approval_threshold_usd

    consolidated_breach = projected_consolidated_margin_pct < covenant_floor
    product_breach = (
        worst_product_margin_pct is not None
        and worst_product_margin_pct < covenant_floor
    )
    hitl_required = incremental_cost_usd > hitl_limit
    esg_compliant = backup_esg_score >= 80.0
    sop_sc04_emergency = (
        is_critical_component
        and days_of_supply_wh_id is not None
        and days_of_supply_wh_id < 6.0
    )

    violations: list[str] = []
    if consolidated_breach or product_breach:
        violations.append(
            f"COV-FIN-01 BREACH RISK: Margin terproyeksi ({worst_product_margin_pct or projected_consolidated_margin_pct:.2f}%) di bawah batas kovenan {covenant_floor:.1f}%."
        )
    if not esg_compliant:
        violations.append(
            f"ESG-2026-03 VIOLATION: Skor ESG pemasok ({backup_esg_score:.1f}) di bawah ambang wajib 80.0."
        )
    if sop_sc04_emergency:
        violations.append(
            f"SOP-SC-04 TRIGGERED: Days-of-supply WH-ID ({days_of_supply_wh_id:.2f} hari) di bawah ambang darurat 6.0 hari."
        )

    return {
        "cov_fin_01": {
            "minimum_margin_pct": covenant_floor,
            "projected_consolidated_margin_pct": round(
                projected_consolidated_margin_pct, 2
            ),
            "worst_product_margin_pct": worst_product_margin_pct,
            "covenant_breach_detected": bool(consolidated_breach or product_breach),
        },
        "sop_sc_04_hitl": {
            "hitl_threshold_usd": hitl_limit,
            "incremental_cost_usd": round(incremental_cost_usd, 2),
            "requires_hitl_approval": hitl_required,
            "required_approver_role": (
                "SupplyChainDirector" if hitl_required else "None"
            ),
        },
        "esg_2026_03": {
            "minimum_esg_score": 80.0,
            "supplier_esg_score": backup_esg_score,
            "is_compliant": esg_compliant,
        },
        "sop_sc_04_inventory_alert": sop_sc04_emergency,
        "policy_alerts": violations,
    }


@mcp.tool()
def query_supply_chain_sql(
    sql_query: str, tenant_id: str = "TENANT-APEX-GLOBAL"
) -> dict[str, Any]:
    """Eksekusi kueri SQL SELECT analitik pada tabel rantai pasok ApexGlobal dengan isolasi tenant."""
    return execute_tenant_sql_query(sql_query=sql_query, tenant_id=tenant_id)


@mcp.tool()
def predict_delay_and_stockout_ml(
    component_id: str,
    warehouse_code: str = "WH-ID",
    override_port_congestion: float | None = None,
) -> dict[str, Any]:
    """Prediksi probabilitas keterlambatan pemasok dan risiko stockout komponen menggunakan XGBoost."""
    stockout_res = predict_component_stockout(
        component_id=component_id,
        warehouse_code=warehouse_code,
        override_port_congestion=override_port_congestion,
    )
    delay_res = predict_supplier_delay(
        supplier_id=stockout_res["primary_supplier_id"],
        component_id=component_id,
        destination_hub=warehouse_code,
        override_port_congestion=override_port_congestion,
    )
    return {
        "delay_prediction": delay_res,
        "stockout_prediction": stockout_res,
        "wh_id_risk_ranking_top3": get_high_risk_components_summary(warehouse_code)[:3],
    }


@mcp.tool()
def run_quantitative_risk_simulation(
    component_id: str,
    warehouse_code: str = "WH-ID",
    port_congestion_index: float = 86.4,
    tariff_surcharge_pct: float = 18.0,
) -> dict[str, Any]:
    """Simulasi Monte Carlo (1.000 iterasi) & pemeringkatan strategi mitigasi pemasok cadangan."""
    optimization = evaluate_mitigation_strategies(
        component_id=component_id,
        warehouse_code=warehouse_code,
        port_congestion_index=port_congestion_index,
        tariff_surcharge_pct=tariff_surcharge_pct,
    )
    best = optimization["recommended_strategy"]
    best_share = (
        0.80
        if "80%" in best["strategy_name"]
        else (0.60 if "60%" in best["strategy_name"] else 0.0)
    )
    best_air = (
        0.70
        if "70%" in best["strategy_name"]
        else (0.30 if "30%" in best["strategy_name"] else 0.0)
    )
    detailed_sim = run_monte_carlo_disruption_sim(
        component_id=component_id,
        warehouse_code=warehouse_code,
        port_congestion_index=port_congestion_index,
        tariff_surcharge_pct=tariff_surcharge_pct,
        air_freight_share=best_air,
        backup_allocation_share=best_share,
        n_iterations=1000,
    )
    return {
        "optimization_summary": optimization,
        "recommended_strategy_monte_carlo": detailed_sim,
    }


@mcp.tool()
def search_hybrid_knowledge_graph(
    query: str,
    tenant_id: str = "TENANT-APEX-GLOBAL",
    top_k_docs: int = 5,
) -> dict[str, Any]:
    """Penelusuran multi-hop Knowledge Graph NetworkX + Hybrid Qdrant RRF beserta sitasi dokumen."""
    return hybrid_graphrag_retrieve(
        query=query, tenant_id=tenant_id, top_k_docs=top_k_docs, max_hops=3
    )


@mcp.tool()
def check_covenant_and_sop_compliance(
    incremental_cost_usd: float,
    projected_consolidated_margin_pct: float,
    worst_product_margin_pct: float | None = None,
    backup_esg_score: float = 90.0,
    days_of_supply_wh_id: float | None = None,
) -> dict[str, Any]:
    """Audit kepatuhan terhadap kovenan utang COV-FIN-01, SOP-SC-04 HITL, dan mandat ESG-2026-03."""
    return verify_governance_and_compliance(
        incremental_cost_usd=incremental_cost_usd,
        projected_consolidated_margin_pct=projected_consolidated_margin_pct,
        worst_product_margin_pct=worst_product_margin_pct,
        backup_esg_score=backup_esg_score,
        days_of_supply_wh_id=days_of_supply_wh_id,
    )
