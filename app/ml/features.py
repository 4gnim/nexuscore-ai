import numpy as np
import pandas as pd

DELAY_NUMERIC_FEATURES = [
    "port_congestion_index",
    "weather_severity_index",
    "supplier_health_at_order",
    "geopolitical_risk_index",
    "esg_score",
    "contracted_lead_time_days",
    "promised_lead_days",
    "order_qty",
    "unit_price_usd",
    "order_month",
    "order_dayofweek",
    "is_high_congestion",
    "congestion_x_sea",
    "health_deficit",
    "lead_time_compression_ratio",
]

DELAY_CATEGORICAL_FEATURES = [
    "transport_mode",
    "destination_hub",
    "criticality",
    "country",
]

STOCKOUT_NUMERIC_FEATURES = [
    "days_of_supply",
    "net_days_of_supply",
    "safety_stock_ratio",
    "daily_burn_rate",
    "predicted_delay_days",
    "delay_probability",
    "lead_time_gap_days",
    "is_wh_id",
    "is_critical_comp",
]


def engineer_delay_features(df: pd.DataFrame) -> pd.DataFrame:
    """Membentuk fitur deterministik untuk model prediksi keterlambatan pengiriman."""
    out = df.copy()

    out["port_congestion_index"] = pd.to_numeric(
        out.get("port_congestion_index", 40.0), errors="coerce"
    ).fillna(40.0)
    out["weather_severity_index"] = pd.to_numeric(
        out.get("weather_severity_index", 15.0), errors="coerce"
    ).fillna(15.0)
    out["supplier_health_at_order"] = pd.to_numeric(
        out.get("supplier_health_at_order", 85.0), errors="coerce"
    ).fillna(85.0)
    out["geopolitical_risk_index"] = pd.to_numeric(
        out.get("geopolitical_risk_index", 30.0), errors="coerce"
    ).fillna(30.0)
    out["esg_score"] = pd.to_numeric(
        out.get("esg_score", 90.0), errors="coerce"
    ).fillna(90.0)
    out["contracted_lead_time_days"] = pd.to_numeric(
        out.get("contracted_lead_time_days", 14), errors="coerce"
    ).fillna(14)
    out["promised_lead_days"] = pd.to_numeric(
        out.get("promised_lead_days", out["contracted_lead_time_days"]), errors="coerce"
    ).fillna(14)
    out["order_qty"] = pd.to_numeric(
        out.get("order_qty", 1000), errors="coerce"
    ).fillna(1000)
    out["unit_price_usd"] = pd.to_numeric(
        out.get("unit_price_usd", 100.0), errors="coerce"
    ).fillna(100.0)
    out["order_month"] = pd.to_numeric(
        out.get("order_month", 11), errors="coerce"
    ).fillna(11)
    out["order_dayofweek"] = pd.to_numeric(
        out.get("order_dayofweek", 2), errors="coerce"
    ).fillna(2)

    out["transport_mode"] = (
        out.get("transport_mode", "SEA_FREIGHT").fillna("SEA_FREIGHT").astype(str)
    )
    out["destination_hub"] = (
        out.get("destination_hub", "WH-ID").fillna("WH-ID").astype(str)
    )
    out["criticality"] = out.get("criticality", "HIGH").fillna("HIGH").astype(str)
    out["country"] = out.get("country", "Taiwan").fillna("Taiwan").astype(str)

    # Engineered interaction & domain features
    out["is_high_congestion"] = (out["port_congestion_index"] >= 75.0).astype(int)
    is_sea = (out["transport_mode"] == "SEA_FREIGHT").astype(float)
    out["congestion_x_sea"] = (out["port_congestion_index"] * is_sea).round(2)
    out["health_deficit"] = np.maximum(
        0.0, 85.0 - out["supplier_health_at_order"]
    ).round(2)
    out["lead_time_compression_ratio"] = (
        out["promised_lead_days"] / out["contracted_lead_time_days"].replace(0, 1)
    ).round(3)

    all_cols = DELAY_NUMERIC_FEATURES + DELAY_CATEGORICAL_FEATURES
    return out[all_cols]


def engineer_stockout_features(df: pd.DataFrame) -> pd.DataFrame:
    """Membentuk fitur deterministik untuk model prediksi risiko kehabisan stok (Stockout)."""
    out = df.copy()

    out["days_of_supply"] = pd.to_numeric(
        out["days_of_supply"], errors="coerce"
    ).fillna(10.0)
    out["net_days_of_supply"] = pd.to_numeric(
        out.get("net_days_of_supply", out["days_of_supply"] * 0.78), errors="coerce"
    ).fillna(7.8)
    out["safety_stock_ratio"] = pd.to_numeric(
        out.get("safety_stock_ratio", 1.0), errors="coerce"
    ).fillna(1.0)
    out["daily_burn_rate"] = pd.to_numeric(
        out.get("daily_burn_rate", 100.0), errors="coerce"
    ).fillna(100.0)
    out["predicted_delay_days"] = pd.to_numeric(
        out.get("predicted_delay_days", 0.0), errors="coerce"
    ).fillna(0.0)
    out["delay_probability"] = pd.to_numeric(
        out.get("delay_probability", 0.1), errors="coerce"
    ).fillna(0.1)

    lead_time = pd.to_numeric(
        out.get("contracted_lead_time_days", 14.0), errors="coerce"
    ).fillna(14.0)
    total_expected_replenishment = lead_time + out["predicted_delay_days"]
    out["lead_time_gap_days"] = (
        out["net_days_of_supply"] - total_expected_replenishment
    ).round(2)

    wh = out.get("warehouse_code", "WH-ID").fillna("WH-ID").astype(str)
    crit = out.get("criticality", "HIGH").fillna("HIGH").astype(str)
    out["is_wh_id"] = (wh == "WH-ID").astype(int)
    out["is_critical_comp"] = (crit == "CRITICAL").astype(int)

    return out[STOCKOUT_NUMERIC_FEATURES]
