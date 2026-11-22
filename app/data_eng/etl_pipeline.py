import json
from dataclasses import asdict
from datetime import datetime, timezone
import pandas as pd
from app.core.config import get_settings
from app.core.database import (
    BOM,
    Component,
    Inventory,
    Product,
    SessionLocal,
    ShipmentHistory,
    Supplier,
    init_db,
)
from app.data_eng.quality_gate import validate_shipments_dataframe

settings = get_settings()


def _load_master_tables() -> dict[str, pd.DataFrame]:
    raw_dir = settings.raw_data_dir
    suppliers = pd.read_csv(raw_dir / "suppliers.csv")
    components = pd.read_csv(raw_dir / "components.csv")
    products = pd.read_csv(raw_dir / "products.csv")
    bom = pd.read_csv(raw_dir / "bom.csv")
    inventory = pd.read_csv(raw_dir / "inventory.csv")

    suppliers["is_approved_backup"] = suppliers["is_approved_backup"].astype(bool)
    bom["is_single_source_risk"] = bom["is_single_source_risk"].astype(bool)

    return {
        "suppliers": suppliers,
        "components": components,
        "products": products,
        "bom": bom,
        "inventory": inventory,
    }


def _build_curated_marts(
    masters: dict[str, pd.DataFrame],
    clean_shipments: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    suppliers = masters["suppliers"]
    components = masters["components"]
    inventory = masters["inventory"]

    # 1. Curated Shipments Enriched Mart (Siap untuk Feature Engineering ML Fase 4)
    shipments_enriched = (
        clean_shipments.merge(
            suppliers[
                [
                    "supplier_id",
                    "supplier_name",
                    "country",
                    "tier",
                    "geopolitical_risk_index",
                    "esg_score",
                    "contracted_lead_time_days",
                    "unit_cost_multiplier",
                ]
            ],
            on="supplier_id",
            how="left",
        )
        .merge(
            components[
                [
                    "component_id",
                    "component_name",
                    "category",
                    "criticality",
                    "standard_unit_cost_usd",
                    "base_tariff_pct",
                ]
            ],
            on="component_id",
            how="left",
        )
        .copy()
    )

    order_dt_series = pd.to_datetime(shipments_enriched["order_date"])
    promised_dt_series = pd.to_datetime(shipments_enriched["promised_date"])
    actual_dt_series = pd.to_datetime(shipments_enriched["actual_arrival_date"])

    shipments_enriched["promised_lead_days"] = (
        promised_dt_series - order_dt_series
    ).dt.days
    shipments_enriched["actual_lead_days"] = (
        actual_dt_series - order_dt_series
    ).dt.days
    shipments_enriched["material_cost_usd"] = (
        shipments_enriched["order_qty"] * shipments_enriched["unit_price_usd"]
    ).round(2)
    shipments_enriched["total_landed_cost_usd"] = (
        shipments_enriched["material_cost_usd"]
        + shipments_enriched["freight_cost_usd"]
        + shipments_enriched["tariff_paid_usd"]
    ).round(2)
    shipments_enriched["landed_unit_cost_usd"] = (
        shipments_enriched["total_landed_cost_usd"] / shipments_enriched["order_qty"]
    ).round(4)
    shipments_enriched["order_month"] = order_dt_series.dt.month
    shipments_enriched["order_dayofweek"] = order_dt_series.dt.day_of_week
    shipments_enriched["is_high_congestion"] = (
        shipments_enriched["port_congestion_index"] >= 75.0
    ).astype(int)

    # 2. Curated Inventory Risk & Days-of-Supply Mart (SOP-SC-04 Monitoring)
    inv_mart = inventory.merge(
        components[
            [
                "component_id",
                "component_name",
                "category",
                "criticality",
                "primary_supplier_id",
                "backup_supplier_id",
                "standard_unit_cost_usd",
            ]
        ],
        on="component_id",
        how="left",
    ).copy()
    inv_mart["net_available_qty"] = (
        inv_mart["on_hand_qty"] - inv_mart["reserved_qty"]
    ).clip(lower=0)
    inv_mart["days_of_supply"] = (
        inv_mart["on_hand_qty"] / inv_mart["daily_burn_rate"].replace(0, 1)
    ).round(2)
    inv_mart["net_days_of_supply"] = (
        inv_mart["net_available_qty"] / inv_mart["daily_burn_rate"].replace(0, 1)
    ).round(2)
    inv_mart["is_below_safety_stock"] = (
        inv_mart["on_hand_qty"] < inv_mart["safety_stock_qty"]
    )
    inv_mart["is_sop_sc04_breach"] = (
        (inv_mart["warehouse_code"] == "WH-ID")
        & (inv_mart["criticality"] == "CRITICAL")
        & (inv_mart["days_of_supply"] < 6.0)
    )

    return {
        "shipments_enriched": shipments_enriched,
        "inventory_risk_mart": inv_mart,
    }


def _upsert_to_postgres(
    masters: dict[str, pd.DataFrame],
    clean_shipments: pd.DataFrame,
) -> dict[str, int]:
    """Melakukan idempotent upsert secara berurutan (Parent -> Child) ke Supabase PostgreSQL."""
    init_db()
    counts: dict[str, int] = {}

    with SessionLocal() as session:
        # Tier 1: Independent Master Tables
        for row in masters["suppliers"].to_dict(orient="records"):
            session.merge(Supplier(**row))
        counts["nc_suppliers"] = len(masters["suppliers"])

        for row in masters["products"].to_dict(orient="records"):
            session.merge(Product(**row))
        counts["nc_products"] = len(masters["products"])
        session.flush()

        # Tier 2: Tables referencing Suppliers
        for row in masters["components"].to_dict(orient="records"):
            session.merge(Component(**row))
        counts["nc_components"] = len(masters["components"])
        session.flush()

        # Tier 3: Child & Fact Tables referencing Products, Components, and Suppliers
        for row in masters["bom"].to_dict(orient="records"):
            session.merge(BOM(**row))
        counts["nc_bom"] = len(masters["bom"])

        for row in masters["inventory"].to_dict(orient="records"):
            session.merge(Inventory(**row))
        counts["nc_inventory"] = len(masters["inventory"])

        for row in clean_shipments.to_dict(orient="records"):
            session.merge(ShipmentHistory(**row))
        counts["nc_shipments_history"] = len(clean_shipments)

        session.commit()

    return counts


def run_batch_etl() -> dict:
    """Menjalankan pipeline ETL end-to-end: Raw -> Quality Gate -> Cleaned/Curated Parquet -> PostgreSQL."""
    settings.cleaned_data_dir.mkdir(parents=True, exist_ok=True)
    settings.curated_data_dir.mkdir(parents=True, exist_ok=True)
    settings.dlq_data_dir.mkdir(parents=True, exist_ok=True)

    masters = _load_master_tables()
    raw_shipments = pd.read_csv(
        settings.raw_data_dir / "shipments_history.csv", dtype=str
    )

    valid_sup_ids = set(masters["suppliers"]["supplier_id"].astype(str))
    valid_comp_ids = set(masters["components"]["component_id"].astype(str))
    dlq_path = settings.dlq_data_dir / "shipments_dlq.json"

    clean_shipments, dlq_records, quality_report = validate_shipments_dataframe(
        df=raw_shipments,
        valid_supplier_ids=valid_sup_ids,
        valid_component_ids=valid_comp_ids,
        dlq_output_path=dlq_path,
    )

    # Simpan Cleaned Layer (Parquet)
    for name, df in masters.items():
        df.to_parquet(settings.cleaned_data_dir / f"{name}.parquet", index=False)

    shipments_for_parquet = clean_shipments.copy()
    for col in ("order_date", "promised_date", "actual_arrival_date"):
        shipments_for_parquet[col] = shipments_for_parquet[col].astype(str)
    shipments_for_parquet.to_parquet(
        settings.cleaned_data_dir / "shipments_cleaned.parquet", index=False
    )

    # Bangun & Simpan Curated Analytical Marts (Parquet)
    marts = _build_curated_marts(masters, shipments_for_parquet)
    for mart_name, mart_df in marts.items():
        mart_df.to_parquet(
            settings.curated_data_dir / f"{mart_name}.parquet", index=False
        )

    # Simpan ringkasan audit kualitas data
    report_path = settings.dlq_data_dir / "quality_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "executed_at": datetime.now(timezone.utc).isoformat(),
                **asdict(quality_report),
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    # Upsert ke Supabase PostgreSQL
    db_counts = _upsert_to_postgres(masters, clean_shipments)

    return {
        "quality_report": asdict(quality_report),
        "dlq_file": str(dlq_path),
        "curated_marts": {k: len(v) for k, v in marts.items()},
        "postgres_upserted": db_counts,
    }


if __name__ == "__main__":
    summary = run_batch_etl()
    print("=== Fase 3 Batch ETL & Data Quality Pipeline Selesai ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
