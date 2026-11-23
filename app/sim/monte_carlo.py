from typing import Any
import numpy as np
import pandas as pd
from app.core.config import get_settings

settings = get_settings()


def run_monte_carlo_disruption_sim(
    component_id: str,
    warehouse_code: str = "WH-ID",
    port_congestion_index: float = 86.4,
    tariff_surcharge_pct: float = 18.0,
    air_freight_share: float = 0.30,
    backup_allocation_share: float = 0.60,
    n_iterations: int = 1000,
    random_seed: int = 42,
) -> dict[str, Any]:
    """Menjalankan simulasi Monte Carlo (1.000 iterasi) untuk mengukur risiko biaya, stockout, dan margin kovenan COV-FIN-01."""
    rng = np.random.default_rng(random_seed)

    suppliers_df = pd.read_parquet(settings.cleaned_data_dir / "suppliers.parquet")
    components_df = pd.read_parquet(settings.cleaned_data_dir / "components.parquet")
    products_df = pd.read_parquet(settings.cleaned_data_dir / "products.parquet")
    bom_df = pd.read_parquet(settings.cleaned_data_dir / "bom.parquet")
    inv_mart_df = pd.read_parquet(
        settings.curated_data_dir / "inventory_risk_mart.parquet"
    )

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

    inv_match = inv_mart_df[
        (inv_mart_df["component_id"] == component_id)
        & (inv_mart_df["warehouse_code"] == warehouse_code)
    ]
    if inv_match.empty:
        raise ValueError(
            f"Data inventori tidak ditemukan untuk {component_id} di {warehouse_code}"
        )
    inv = inv_match.iloc[0].to_dict()

    # Identifikasi produk terdampak melalui BOM
    affected_bom = bom_df[bom_df["component_id"] == component_id].merge(
        products_df, on="product_id", how="inner"
    )
    monthly_comp_demand = int(
        (affected_bom["qty_per_unit"] * affected_bom["monthly_demand_units"]).sum()
    )
    if monthly_comp_demand <= 0:
        monthly_comp_demand = int(float(inv["daily_burn_rate"]) * 30)

    # Baseline finansial perusahaan (konsolidasi seluruh lini produk)
    products_df = products_df.copy()
    products_df["monthly_revenue"] = (
        products_df["selling_price_usd"] * products_df["monthly_demand_units"]
    )
    products_df["monthly_cogs"] = (
        products_df["standard_cogs_usd"] * products_df["monthly_demand_units"]
    )
    total_baseline_revenue = float(products_df["monthly_revenue"].sum())
    total_baseline_cogs = float(products_df["monthly_cogs"].sum())
    baseline_consolidated_margin_pct = round(
        (total_baseline_revenue - total_baseline_cogs) / total_baseline_revenue * 100.0,
        2,
    )

    # Parameter distribusi Monte Carlo (1.000 skenario)
    congestion_samples = np.clip(
        rng.normal(port_congestion_index, 6.5, size=n_iterations), 10.0, 100.0
    )
    weather_samples = np.clip(rng.exponential(18.0, size=n_iterations), 0.0, 95.0)
    health_shock = np.maximum(0.0, 80.0 - float(pri_sup["financial_health_score"]))

    # Simulasi keterlambatan (hari) pada porsi yang tetap dikirim via laut pemasok utama
    primary_sea_share = max(
        0.0, (1.0 - backup_allocation_share) * (1.0 - air_freight_share)
    )
    base_delay = (
        0.095 * np.maximum(0.0, congestion_samples - 45.0)
        + 0.045 * weather_samples
        + 0.08 * health_shock
        + rng.normal(0.0, 1.6, size=n_iterations)
    )
    simulated_delay_days = np.maximum(0.0, base_delay)

    # Efektif lead time gabungan
    pri_sea_lead = float(pri_sup["contracted_lead_time_days"]) + simulated_delay_days
    bak_lead = float(bak_sup["contracted_lead_time_days"]) * (
        0.35 * air_freight_share + 1.0 * (1.0 - air_freight_share)
    )
    effective_lead_days = (1.0 - backup_allocation_share) * (
        air_freight_share * 4.0 + (1.0 - air_freight_share) * pri_sea_lead
    ) + backup_allocation_share * bak_lead

    net_dos = float(inv["net_days_of_supply"])
    daily_burn = float(inv["daily_burn_rate"])
    shortfall_days = np.maximum(0.0, effective_lead_days - net_dos)
    shortfall_units = shortfall_days * daily_burn

    # Simulasi biaya tambahan bulanan (USD)
    std_cost = float(comp["standard_unit_cost_usd"])
    pri_units = monthly_comp_demand * (1.0 - backup_allocation_share)
    bak_units = monthly_comp_demand * backup_allocation_share

    # 1. Premi harga unit pemasok cadangan
    backup_price_delta = (
        bak_units * std_cost * (float(bak_sup["unit_cost_multiplier"]) - 1.0)
    )

    # 2. Dampak tarif tambahan TAR-2026-88 hanya pada porsi pemasok utama non-FTA
    tariff_shock_samples = np.clip(
        rng.normal(tariff_surcharge_pct, 2.0, size=n_iterations), 0.0, 40.0
    )
    tariff_delta = pri_units * std_cost * (tariff_shock_samples / 100.0)

    # 3. Premi ekspedisi udara (air freight) & war-risk sea surcharge
    air_units = monthly_comp_demand * air_freight_share
    sea_pri_units = pri_units * (1.0 - air_freight_share)
    air_freight_delta = air_units * rng.normal(7.2, 1.1, size=n_iterations)
    war_risk_sea_delta = sea_pri_units * np.where(congestion_samples > 75.0, 2.4, 0.4)

    # 4. Penalti keterlambatan lini perakitan (line-stoppage expediting cost)
    stoppage_penalty = shortfall_units * std_cost * 0.12

    total_incremental_cost = np.maximum(
        0.0,
        backup_price_delta
        + tariff_delta
        + air_freight_delta
        + war_risk_sea_delta
        + stoppage_penalty,
    )

    # Dampak terhadap Consolidated Gross Margin
    simulated_cogs = total_baseline_cogs + total_incremental_cost
    simulated_consolidated_margin = (
        (total_baseline_revenue - simulated_cogs) / total_baseline_revenue * 100.0
    )

    # Dampak terhadap produk paling rentan (margin terendah di antara produk terdampak)
    most_vulnerable_product = None
    worst_product_p50_margin = None
    worst_product_breach_prob = 0.0

    if not affected_bom.empty:
        affected_bom = affected_bom.copy()
        affected_bom["comp_demand_share"] = (
            affected_bom["qty_per_unit"] * affected_bom["monthly_demand_units"]
        ) / max(1, monthly_comp_demand)

        for _, prow in affected_bom.iterrows():
            prod_rev = float(prow["selling_price_usd"]) * float(
                prow["monthly_demand_units"]
            )
            prod_base_cogs = float(prow["standard_cogs_usd"]) * float(
                prow["monthly_demand_units"]
            )
            allocated_extra_cost = total_incremental_cost * float(
                prow["comp_demand_share"]
            )
            prod_margin_dist = (
                (prod_rev - (prod_base_cogs + allocated_extra_cost)) / prod_rev * 100.0
            )
            p50_m = float(np.percentile(prod_margin_dist, 50))
            breach_p = float(
                np.mean(prod_margin_dist < settings.covenant_min_gross_margin_pct)
            )

            if worst_product_p50_margin is None or p50_m < worst_product_p50_margin:
                worst_product_p50_margin = round(p50_m, 2)
                worst_product_breach_prob = round(breach_p, 4)
                most_vulnerable_product = {
                    "product_id": prow["product_id"],
                    "product_name": prow["product_name"],
                    "baseline_margin_pct": float(prow["gross_margin_pct"]),
                    "simulated_p50_margin_pct": round(p50_m, 2),
                    "covenant_floor_pct": settings.covenant_min_gross_margin_pct,
                    "product_covenant_breach_probability": round(breach_p, 4),
                }

    covenant_floor = settings.covenant_min_gross_margin_pct
    hitl_limit = settings.hitl_approval_threshold_usd

    consolidated_breach_prob = float(
        np.mean(simulated_consolidated_margin < covenant_floor)
    )
    hitl_trigger_prob = float(np.mean(total_incremental_cost > hitl_limit))

    # Histogram 10 bin untuk Chart.js di Frontend War Room
    hist_counts, hist_edges = np.histogram(total_incremental_cost, bins=10)
    histogram_bins = [
        {
            "range_label": f"${int(hist_edges[i]/1000)}k-${int(hist_edges[i+1]/1000)}k",
            "count": int(hist_counts[i]),
        }
        for i in range(len(hist_counts))
    ]

    p50_cost = float(np.percentile(total_incremental_cost, 50))
    p95_cost = float(np.percentile(total_incremental_cost, 95))
    p50_cons_margin = float(np.percentile(simulated_consolidated_margin, 50))

    return {
        "component_id": component_id,
        "component_name": comp["component_name"],
        "warehouse_code": warehouse_code,
        "n_iterations": n_iterations,
        "scenario_inputs": {
            "port_congestion_index": port_congestion_index,
            "tariff_surcharge_pct": tariff_surcharge_pct,
            "air_freight_share": air_freight_share,
            "backup_allocation_share": backup_allocation_share,
            "monthly_component_demand": monthly_comp_demand,
        },
        "delay_distribution_days": {
            "p10": round(float(np.percentile(simulated_delay_days, 10)), 2),
            "p50_median": round(float(np.percentile(simulated_delay_days, 50)), 2),
            "p90": round(float(np.percentile(simulated_delay_days, 90)), 2),
            "mean": round(float(np.mean(simulated_delay_days)), 2),
        },
        "shortfall_units_distribution": {
            "p50_median": int(round(float(np.percentile(shortfall_units, 50)))),
            "p95_tail_risk": int(round(float(np.percentile(shortfall_units, 95)))),
        },
        "incremental_cost_usd": {
            "mean": round(float(np.mean(total_incremental_cost)), 2),
            "p50_median": round(p50_cost, 2),
            "p90": round(float(np.percentile(total_incremental_cost, 90)), 2),
            "p95_var": round(p95_cost, 2),
            "hitl_threshold_usd": hitl_limit,
            "hitl_trigger_probability": round(hitl_trigger_prob, 4),
            "requires_hitl_approval": p50_cost > hitl_limit,
        },
        "financial_covenant_cov_fin_01": {
            "covenant_min_margin_pct": covenant_floor,
            "baseline_consolidated_margin_pct": baseline_consolidated_margin_pct,
            "simulated_p50_consolidated_margin_pct": round(p50_cons_margin, 2),
            "simulated_p05_worst_margin_pct": round(
                float(np.percentile(simulated_consolidated_margin, 5)), 2
            ),
            "consolidated_breach_probability": round(consolidated_breach_prob, 4),
            "most_vulnerable_product": most_vulnerable_product,
            "covenant_breach_detected": bool(
                consolidated_breach_prob >= 0.25 or worst_product_breach_prob >= 0.50
            ),
        },
        "chartjs_cost_histogram": histogram_bins,
    }
