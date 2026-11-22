import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
from app.core.config import get_settings

settings = get_settings()

VALID_TRANSPORT_MODES = {"SEA_FREIGHT", "AIR_FREIGHT", "EXPRESS_COURIER"}
VALID_WAREHOUSES = {"WH-ID", "WH-SG", "WH-DE"}


@dataclass
class DLQRecord:
    shipment_id: str
    rejected_at: str
    error_codes: list[str]
    raw_payload: dict[str, Any]


@dataclass
class QualityReport:
    dataset_name: str
    total_input_rows: int
    valid_rows: int
    rejected_rows: int
    pass_rate_pct: float
    error_breakdown: dict[str, int]


def _parse_iso_date(val: Any) -> date | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    text = str(val).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def validate_shipments_dataframe(
    df: pd.DataFrame,
    valid_supplier_ids: set[str],
    valid_component_ids: set[str],
    dlq_output_path: Path | None = None,
) -> tuple[pd.DataFrame, list[DLQRecord], QualityReport]:
    """Memvalidasi dataset pengiriman dan memisahkan record cacat ke Dead-Letter Queue (DLQ)."""
    seen_ids: set[str] = set()
    clean_rows: list[dict[str, Any]] = []
    dlq_records: list[DLQRecord] = []
    error_counts: dict[str, int] = {}

    for _, row in df.iterrows():
        raw = row.to_dict()
        errors: list[str] = []

        shipment_id = str(raw.get("shipment_id", "") or "").strip()
        tenant_id = str(raw.get("tenant_id", "") or "").strip()
        supplier_id = str(raw.get("supplier_id", "") or "").strip()
        component_id = str(raw.get("component_id", "") or "").strip()
        transport_mode = str(raw.get("transport_mode", "") or "").strip()
        destination_hub = str(raw.get("destination_hub", "") or "").strip()

        # 1. Required fields & Primary Key Uniqueness
        if not shipment_id:
            errors.append("MISSING_SHIPMENT_ID")
        elif shipment_id in seen_ids:
            errors.append("DUPLICATE_SHIPMENT_ID")

        if not tenant_id:
            errors.append("MISSING_TENANT_ID")

        # 2. Referential Integrity (Foreign Keys)
        if not supplier_id:
            errors.append("MISSING_SUPPLIER_ID")
        elif supplier_id not in valid_supplier_ids:
            errors.append("INVALID_FK_SUPPLIER_ID")

        if not component_id:
            errors.append("MISSING_COMPONENT_ID")
        elif component_id not in valid_component_ids:
            errors.append("INVALID_FK_COMPONENT_ID")

        # 3. Domain Enums
        if transport_mode not in VALID_TRANSPORT_MODES:
            errors.append("INVALID_TRANSPORT_MODE")
        if destination_hub not in VALID_WAREHOUSES:
            errors.append("INVALID_DESTINATION_HUB")

        # 4. Date Format & Chronological Consistency
        order_dt = _parse_iso_date(raw.get("order_date"))
        promised_dt = _parse_iso_date(raw.get("promised_date"))
        actual_dt = _parse_iso_date(raw.get("actual_arrival_date"))

        if order_dt is None or promised_dt is None or actual_dt is None:
            errors.append("MALFORMED_DATE")
        else:
            if promised_dt < order_dt:
                errors.append("PROMISED_BEFORE_ORDER_DATE")
            if actual_dt < order_dt:
                errors.append("ARRIVAL_BEFORE_ORDER_DATE")

        # 5. Numeric Bounds & Outlier Guard
        try:
            order_qty = int(raw.get("order_qty"))
            if order_qty <= 0 or order_qty > 100_000:
                errors.append("OUT_OF_RANGE_ORDER_QTY")
        except (TypeError, ValueError):
            errors.append("INVALID_NUMERIC_ORDER_QTY")
            order_qty = 0

        try:
            unit_price = float(raw.get("unit_price_usd"))
            if unit_price <= 0.0 or unit_price > 25_000.0:
                errors.append("OUT_OF_RANGE_UNIT_PRICE")
        except (TypeError, ValueError):
            errors.append("INVALID_NUMERIC_UNIT_PRICE")
            unit_price = 0.0

        try:
            freight_cost = float(raw.get("freight_cost_usd"))
            if freight_cost < 0.0 or freight_cost > 500_000.0:
                errors.append("OUT_OF_RANGE_FREIGHT_COST")
        except (TypeError, ValueError):
            errors.append("INVALID_NUMERIC_FREIGHT_COST")
            freight_cost = 0.0

        try:
            tariff_paid = float(raw.get("tariff_paid_usd"))
            if tariff_paid < 0.0:
                errors.append("NEGATIVE_TARIFF_PAID")
        except (TypeError, ValueError):
            errors.append("INVALID_NUMERIC_TARIFF")
            tariff_paid = 0.0

        try:
            congestion = float(raw.get("port_congestion_index"))
            if not (0.0 <= congestion <= 100.0):
                errors.append("OUT_OF_RANGE_PORT_CONGESTION")
        except (TypeError, ValueError):
            errors.append("INVALID_NUMERIC_CONGESTION")
            congestion = 0.0

        try:
            weather = float(raw.get("weather_severity_index"))
            if not (0.0 <= weather <= 100.0):
                errors.append("OUT_OF_RANGE_WEATHER_INDEX")
        except (TypeError, ValueError):
            errors.append("INVALID_NUMERIC_WEATHER")
            weather = 0.0

        try:
            health = float(raw.get("supplier_health_at_order"))
            if not (0.0 <= health <= 100.0):
                errors.append("OUT_OF_RANGE_SUPPLIER_HEALTH")
        except (TypeError, ValueError):
            errors.append("INVALID_NUMERIC_HEALTH")
            health = 0.0

        try:
            delay_days = int(raw.get("delay_days"))
            if delay_days < 0 or delay_days > 180:
                errors.append("OUT_OF_RANGE_DELAY_DAYS")
        except (TypeError, ValueError):
            errors.append("INVALID_NUMERIC_DELAY_DAYS")
            delay_days = 0

        if errors:
            for code in errors:
                error_counts[code] = error_counts.get(code, 0) + 1
            sanitized_raw = {
                k: (None if (isinstance(v, float) and pd.isna(v)) else v)
                for k, v in raw.items()
            }
            dlq_records.append(
                DLQRecord(
                    shipment_id=shipment_id or "UNKNOWN",
                    rejected_at=datetime.now(timezone.utc).isoformat(),
                    error_codes=errors,
                    raw_payload=sanitized_raw,
                )
            )
        else:
            seen_ids.add(shipment_id)
            clean_rows.append(
                {
                    "shipment_id": shipment_id,
                    "tenant_id": tenant_id,
                    "supplier_id": supplier_id,
                    "component_id": component_id,
                    "origin_port": str(raw.get("origin_port", "")).strip(),
                    "destination_hub": destination_hub,
                    "transport_mode": transport_mode,
                    "order_date": order_dt,
                    "promised_date": promised_dt,
                    "actual_arrival_date": actual_dt,
                    "order_qty": order_qty,
                    "unit_price_usd": round(unit_price, 2),
                    "freight_cost_usd": round(freight_cost, 2),
                    "tariff_paid_usd": round(tariff_paid, 2),
                    "port_congestion_index": round(congestion, 2),
                    "weather_severity_index": round(weather, 2),
                    "supplier_health_at_order": round(health, 2),
                    "delay_days": delay_days,
                    "is_delayed": 1 if delay_days >= 2 else 0,
                    "shipment_status": (
                        "DELIVERED_DELAYED" if delay_days >= 2 else "DELIVERED_ON_TIME"
                    ),
                }
            )

    if dlq_output_path is not None:
        dlq_output_path.parent.mkdir(parents=True, exist_ok=True)
        with dlq_output_path.open("w", encoding="utf-8") as f:
            json.dump(
                [asdict(rec) for rec in dlq_records], f, indent=2, ensure_ascii=False
            )

    total_rows = len(df)
    valid_count = len(clean_rows)
    rejected_count = len(dlq_records)
    pass_rate = round((valid_count / total_rows * 100.0) if total_rows else 0.0, 2)

    report = QualityReport(
        dataset_name="shipments_history",
        total_input_rows=total_rows,
        valid_rows=valid_count,
        rejected_rows=rejected_count,
        pass_rate_pct=pass_rate,
        error_breakdown=dict(sorted(error_counts.items())),
    )
    return pd.DataFrame(clean_rows), dlq_records, report
