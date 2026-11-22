import json
from datetime import date, timedelta
from typing import Any
import pandas as pd
from app.core.config import get_settings
from app.core.database import SessionLocal, ShipmentHistory
from app.data_eng.quality_gate import validate_shipments_dataframe

settings = get_settings()


def ingest_realtime_shipment_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Memproses batch mikro (event stream) masuk melewati Quality Gate sebelum ke PostgreSQL."""
    suppliers_df = pd.read_parquet(settings.cleaned_data_dir / "suppliers.parquet")
    components_df = pd.read_parquet(settings.cleaned_data_dir / "components.parquet")

    valid_sup_ids = set(suppliers_df["supplier_id"].astype(str))
    valid_comp_ids = set(components_df["component_id"].astype(str))

    incoming_df = pd.DataFrame(events)
    clean_df, dlq_records, report = validate_shipments_dataframe(
        df=incoming_df,
        valid_supplier_ids=valid_sup_ids,
        valid_component_ids=valid_comp_ids,
        dlq_output_path=None,
    )

    if not clean_df.empty:
        with SessionLocal() as session:
            for row in clean_df.to_dict(orient="records"):
                session.merge(ShipmentHistory(**row))
            session.commit()

    return {
        "stream_batch_size": len(events),
        "accepted_count": len(clean_df),
        "rejected_dlq_count": len(dlq_records),
        "rejected_reasons": [
            {"shipment_id": r.shipment_id, "errors": r.error_codes} for r in dlq_records
        ],
    }


if __name__ == "__main__":
    today = date(2026, 11, 22)
    sample_events = [
        {
            "shipment_id": "SHP-LIVE-0001",
            "tenant_id": settings.default_tenant_id,
            "supplier_id": "SUP-001",
            "component_id": "CMP-001",
            "origin_port": "Port of Kaohsiung",
            "destination_hub": "WH-ID",
            "transport_mode": "SEA_FREIGHT",
            "order_date": (today - timedelta(days=28)).isoformat(),
            "promised_date": (today - timedelta(days=10)).isoformat(),
            "actual_arrival_date": today.isoformat(),
            "order_qty": 1200,
            "unit_price_usd": 146.50,
            "freight_cost_usd": 2450.00,
            "tariff_paid_usd": 8790.00,
            "port_congestion_index": 86.4,
            "weather_severity_index": 34.0,
            "supplier_health_at_order": 88.5,
            "delay_days": 10,
        },
        {
            "shipment_id": "SHP-LIVE-ERR-99",
            "tenant_id": settings.default_tenant_id,
            "supplier_id": "SUP-UNKNOWN",
            "component_id": "CMP-001",
            "origin_port": "Unknown Port",
            "destination_hub": "WH-ID",
            "transport_mode": "SEA_FREIGHT",
            "order_date": today.isoformat(),
            "promised_date": today.isoformat(),
            "actual_arrival_date": today.isoformat(),
            "order_qty": -10,
            "unit_price_usd": 145.0,
            "freight_cost_usd": 500.0,
            "tariff_paid_usd": 0.0,
            "port_congestion_index": 120.0,
            "weather_severity_index": 10.0,
            "supplier_health_at_order": 80.0,
            "delay_days": 0,
        },
    ]
    res = ingest_realtime_shipment_events(sample_events)
    print("=== Fase 3 Stream Simulator Verification ===")
    print(json.dumps(res, indent=2))
