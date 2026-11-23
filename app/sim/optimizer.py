from typing import Any
import pandas as pd
from app.core.config import get_settings
from app.sim.monte_carlo import run_monte_carlo_disruption_sim

settings = get_settings()


def evaluate_mitigation_strategies(
    component_id: str,
    warehouse_code: str = "WH-ID",
    port_congestion_index: float = 86.4,
    tariff_surcharge_pct: float = 18.0,
) -> dict[str, Any]:
    """Membandingkan dan memeringkat strategi mitigasi & pemasok alternatif secara multi-objektif."""
    suppliers_df = pd.read_parquet(settings.cleaned_data_dir / "suppliers.parquet")
    components_df = pd.read_parquet(settings.cleaned_data_dir / "components.parquet")

    comp_match = components_df[components_df["component_id"] == component_id]
    if comp_match.empty:
        raise ValueError(f"Component ID tidak ditemukan: {component_id}")
    comp = comp_match.iloc[0].to_dict()

    pri_sup = (
        suppliers_df[suppliers_df["supplier_id"] == comp["primary_supplier_id"]]
        .iloc[0]
        .to_dict()
    )
    bak_sup = (
        suppliers_df[suppliers_df["supplier_id"] == comp["backup_supplier_id"]]
        .iloc[0]
        .to_dict()
    )

    # Validasi kepatuhan ESG-2026-03 (minimal ESG score 80.0) & status qualified backup
    esg_compliant = float(bak_sup["esg_score"]) >= 80.0 and bool(
        bak_sup["is_approved_backup"]
    )

    strategies = [
        {
            "strategy_id": "STRAT-A-STATUS-QUO",
            "strategy_name": f"Pertahankan 100% {pri_sup['supplier_name']} (Sea Freight)",
            "backup_allocation_share": 0.0,
            "air_freight_share": 0.0,
            "policy_alignment": "Baseline (Terkena kemacetan pelabuhan & tarif TAR-2026-88)",
        },
        {
            "strategy_id": "STRAT-B-SOP-LOG-09-SPLIT",
            "strategy_name": (
                f"Dual-Sourcing 60% {bak_sup['supplier_name']} + Split 70% Sea / 30% Air (SOP-LOG-09 & Clause 14.2)"
            ),
            "backup_allocation_share": 0.60,
            "air_freight_share": 0.30,
            "policy_alignment": "Mematuhi Clause 14.2, bebas tarif TAR-2026-88 pada porsi backup, & SOP-LOG-09",
        },
        {
            "strategy_id": "STRAT-C-FULL-BACKUP-AIR",
            "strategy_name": f"Alihkan 80% ke {bak_sup['supplier_name']} + 70% Expedited Air Freight",
            "backup_allocation_share": 0.80,
            "air_freight_share": 0.70,
            "policy_alignment": "Pemulihan stok tercepat namun biaya air-freight sangat tinggi",
        },
    ]

    evaluated: list[dict[str, Any]] = []
    for strat in strategies:
        sim = run_monte_carlo_disruption_sim(
            component_id=component_id,
            warehouse_code=warehouse_code,
            port_congestion_index=port_congestion_index,
            tariff_surcharge_pct=tariff_surcharge_pct,
            air_freight_share=strat["air_freight_share"],
            backup_allocation_share=strat["backup_allocation_share"],
            n_iterations=1000,
        )
        p50_cost = sim["incremental_cost_usd"]["p50_median"]
        p50_shortfall = sim["shortfall_units_distribution"]["p50_median"]
        cov = sim["financial_covenant_cov_fin_01"]

        # Skor utilitas (semakin tinggi semakin optimal): penalti biaya, shortfall, dan covenant breach
        breach_penalty = 45.0 if cov["covenant_breach_detected"] else 0.0
        esg_penalty = 0.0 if esg_compliant else 50.0
        cost_score = max(0.0, 40.0 - (p50_cost / 15000.0))
        service_score = max(0.0, 60.0 - (p50_shortfall / 60.0))
        resilience_score = round(
            max(
                0.0,
                min(100.0, cost_score + service_score - breach_penalty - esg_penalty),
            ),
            2,
        )

        evaluated.append(
            {
                "strategy_id": strat["strategy_id"],
                "strategy_name": strat["strategy_name"],
                "policy_alignment": strat["policy_alignment"],
                "resilience_utility_score": resilience_score,
                "p50_incremental_cost_usd": p50_cost,
                "p95_incremental_cost_usd": sim["incremental_cost_usd"]["p95_var"],
                "p50_shortfall_units": p50_shortfall,
                "simulated_p50_consolidated_margin_pct": cov[
                    "simulated_p50_consolidated_margin_pct"
                ],
                "most_vulnerable_product": cov["most_vulnerable_product"],
                "covenant_breach_detected": cov["covenant_breach_detected"],
                "requires_hitl_approval": sim["incremental_cost_usd"][
                    "requires_hitl_approval"
                ],
            }
        )

    evaluated.sort(key=lambda x: x["resilience_utility_score"], reverse=True)
    recommended = evaluated[0]

    return {
        "component_id": component_id,
        "component_name": comp["component_name"],
        "primary_supplier": {
            "supplier_id": pri_sup["supplier_id"],
            "supplier_name": pri_sup["supplier_name"],
            "port_hub": pri_sup["port_hub"],
            "esg_score": float(pri_sup["esg_score"]),
        },
        "qualified_backup_supplier": {
            "supplier_id": bak_sup["supplier_id"],
            "supplier_name": bak_sup["supplier_name"],
            "port_hub": bak_sup["port_hub"],
            "esg_score": float(bak_sup["esg_score"]),
            "monthly_capacity_units": int(bak_sup["monthly_capacity_units"]),
            "esg_2026_03_compliant": esg_compliant,
        },
        "recommended_strategy": recommended,
        "all_evaluated_strategies": evaluated,
    }
