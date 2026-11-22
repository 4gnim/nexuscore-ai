import json
from functools import lru_cache
from typing import Any
import joblib
import pandas as pd
from app.core.config import get_settings
from app.ml.features import engineer_delay_features, engineer_stockout_features

settings = get_settings()


@lru_cache(maxsize=1)
def load_ml_artifacts() -> dict[str, Any]:
    """Memuat model terlatih dan metadata dari models_registry."""
    registry_dir = settings.models_registry_dir.resolve()
    delay_cls_path = registry_dir / "delay_classifier.joblib"
    if not delay_cls_path.exists():
        from app.ml.train_models import train_and_register_all

        train_and_register_all()

    with (registry_dir / "model_metadata.json").open("r", encoding="utf-8") as f:
        metadata = json.load(f)

    return {
        "delay_classifier": joblib.load(registry_dir / "delay_classifier.joblib"),
        "delay_regressor": joblib.load(registry_dir / "delay_regressor.joblib"),
        "stockout_classifier": joblib.load(registry_dir / "stockout_classifier.joblib"),
        "metadata": metadata,
    }


def _classify_risk_tier(prob: float) -> str:
    if prob >= 0.75:
        return "CRITICAL"
    if prob >= 0.50:
        return "HIGH"
    if prob >= 0.25:
        return "MODERATE"
    return "LOW"


def predict_supplier_delay(
    supplier_id: str,
    component_id: str | None = None,
    transport_mode: str = "SEA_FREIGHT",
    destination_hub: str = "WH-ID",
    override_port_congestion: float | None = None,
    override_weather_severity: float | None = None,
    override_supplier_health: float | None = None,
    order_qty: int = 1500,
) -> dict[str, Any]:
    """Memprediksi risiko keterlambatan & estimasi hari keterlambatan untuk pemasok tertentu."""
    artifacts = load_ml_artifacts()
    suppliers_df = pd.read_parquet(settings.cleaned_data_dir / "suppliers.parquet")
    components_df = pd.read_parquet(settings.cleaned_data_dir / "components.parquet")

    sup_match = suppliers_df[suppliers_df["supplier_id"] == supplier_id]
    if sup_match.empty:
        raise ValueError(f"Supplier ID tidak ditemukan: {supplier_id}")
    sup = sup_match.iloc[0].to_dict()

    if component_id:
        comp_match = components_df[components_df["component_id"] == component_id]
    else:
        comp_match = components_df[
            (components_df["primary_supplier_id"] == supplier_id)
            | (components_df["backup_supplier_id"] == supplier_id)
        ]
    comp = (
        comp_match.iloc[0].to_dict()
        if not comp_match.empty
        else {
            "component_id": "CMP-001",
            "criticality": "HIGH",
            "standard_unit_cost_usd": 100.0,
        }
    )

    congestion = (
        float(override_port_congestion)
        if override_port_congestion is not None
        else float(sup["geopolitical_risk_index"] * 0.90)
    )
    weather = (
        float(override_weather_severity)
        if override_weather_severity is not None
        else 20.0
    )
    health = (
        float(override_supplier_health)
        if override_supplier_health is not None
        else float(sup["financial_health_score"])
    )

    base_lead = int(sup["contracted_lead_time_days"])
    promised_lead = (
        base_lead if transport_mode == "SEA_FREIGHT" else max(3, int(base_lead * 0.35))
    )

    sample_row = pd.DataFrame(
        [
            {
                "port_congestion_index": congestion,
                "weather_severity_index": weather,
                "supplier_health_at_order": health,
                "geopolitical_risk_index": float(sup["geopolitical_risk_index"]),
                "esg_score": float(sup["esg_score"]),
                "contracted_lead_time_days": base_lead,
                "promised_lead_days": promised_lead,
                "order_qty": order_qty,
                "unit_price_usd": float(comp["standard_unit_cost_usd"])
                * float(sup["unit_cost_multiplier"]),
                "order_month": 11,
                "order_dayofweek": 2,
                "transport_mode": transport_mode,
                "destination_hub": destination_hub,
                "criticality": comp["criticality"],
                "country": sup["country"],
            }
        ]
    )

    X_feat = engineer_delay_features(sample_row)
    delay_prob = float(artifacts["delay_classifier"].predict_proba(X_feat)[0, 1])
    pred_days = max(0.0, float(artifacts["delay_regressor"].predict(X_feat)[0]))

    drivers = []
    if congestion >= 75.0:
        drivers.append(
            f"Kemacetan pelabuhan tinggi ({congestion:.1f}/100 di {sup['port_hub']})"
        )
    if health < 70.0:
        drivers.append(f"Kesehatan finansial pemasok menurun ({health:.1f}/100)")
    if weather >= 50.0:
        drivers.append(f"Cuaca maritim ekstrem ({weather:.1f}/100)")
    if transport_mode == "SEA_FREIGHT" and base_lead >= 18:
        drivers.append(f"Lead time laut panjang ({base_lead} hari)")
    if not drivers:
        drivers.append("Parameter operasional dalam batas normal")

    return {
        "supplier_id": supplier_id,
        "supplier_name": sup["supplier_name"],
        "country": sup["country"],
        "port_hub": sup["port_hub"],
        "component_id": comp["component_id"],
        "transport_mode": transport_mode,
        "input_congestion_index": round(congestion, 2),
        "input_supplier_health": round(health, 2),
        "delay_probability": round(delay_prob, 4),
        "predicted_delay_days": round(pred_days, 2),
        "risk_tier": _classify_risk_tier(delay_prob),
        "risk_drivers": drivers,
    }


def predict_component_stockout(
    component_id: str,
    warehouse_code: str = "WH-ID",
    override_port_congestion: float | None = None,
) -> dict[str, Any]:
    """Memprediksi risiko kehabisan stok komponen di gudang tertentu berdasarkan posisi inventori & prediksi delay."""
    artifacts = load_ml_artifacts()
    inv_mart = pd.read_parquet(
        settings.curated_data_dir / "inventory_risk_mart.parquet"
    )
    suppliers_df = pd.read_parquet(settings.cleaned_data_dir / "suppliers.parquet")

    match = inv_mart[
        (inv_mart["component_id"] == component_id)
        & (inv_mart["warehouse_code"] == warehouse_code)
    ]
    if match.empty:
        raise ValueError(
            f"Data inventori tidak ditemukan untuk {component_id} di {warehouse_code}"
        )

    row = match.iloc[0].to_dict()
    primary_sup_id = row["primary_supplier_id"]
    sup_row = (
        suppliers_df[suppliers_df["supplier_id"] == primary_sup_id].iloc[0].to_dict()
    )

    delay_pred = predict_supplier_delay(
        supplier_id=primary_sup_id,
        component_id=component_id,
        destination_hub=warehouse_code,
        override_port_congestion=override_port_congestion,
    )

    safety_ratio = float(row["on_hand_qty"]) / max(1.0, float(row["safety_stock_qty"]))
    stk_df = pd.DataFrame(
        [
            {
                "warehouse_code": warehouse_code,
                "criticality": row["criticality"],
                "days_of_supply": float(row["days_of_supply"]),
                "net_days_of_supply": float(row["net_days_of_supply"]),
                "safety_stock_ratio": round(safety_ratio, 3),
                "daily_burn_rate": float(row["daily_burn_rate"]),
                "predicted_delay_days": delay_pred["predicted_delay_days"],
                "delay_probability": delay_pred["delay_probability"],
                "contracted_lead_time_days": int(sup_row["contracted_lead_time_days"]),
            }
        ]
    )

    X_stk = engineer_stockout_features(stk_df)
    stockout_prob = float(artifacts["stockout_classifier"].predict_proba(X_stk)[0, 1])

    total_replenishment_days = (
        int(sup_row["contracted_lead_time_days"]) + delay_pred["predicted_delay_days"]
    )
    uncovered_days = max(
        0.0, total_replenishment_days - float(row["net_days_of_supply"])
    )
    projected_shortfall_units = int(
        round(uncovered_days * float(row["daily_burn_rate"]))
    )

    return {
        "component_id": component_id,
        "component_name": row["component_name"],
        "warehouse_code": warehouse_code,
        "criticality": row["criticality"],
        "primary_supplier_id": primary_sup_id,
        "backup_supplier_id": row["backup_supplier_id"],
        "on_hand_qty": int(row["on_hand_qty"]),
        "net_available_qty": int(row["net_available_qty"]),
        "daily_burn_rate": float(row["daily_burn_rate"]),
        "days_of_supply": float(row["days_of_supply"]),
        "net_days_of_supply": float(row["net_days_of_supply"]),
        "sop_sc04_breach": bool(row["is_sop_sc04_breach"]),
        "supplier_delay_probability": delay_pred["delay_probability"],
        "predicted_delay_days": delay_pred["predicted_delay_days"],
        "stockout_probability": round(stockout_prob, 4),
        "stockout_risk_tier": _classify_risk_tier(stockout_prob),
        "projected_shortfall_units": projected_shortfall_units,
    }


def get_high_risk_components_summary(
    warehouse_code: str = "WH-ID",
) -> list[dict[str, Any]]:
    """Menjalankan pemindaian prediktif seluruh 10 komponen pada hub perakitan tertentu."""
    components_df = pd.read_parquet(settings.cleaned_data_dir / "components.parquet")
    results = []
    for comp_id in components_df["component_id"].tolist():
        results.append(
            predict_component_stockout(comp_id, warehouse_code=warehouse_code)
        )
    results.sort(key=lambda x: x["stockout_probability"], reverse=True)
    return results
