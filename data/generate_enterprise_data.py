import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
DOCS_DIR = BASE_DIR / "data" / "documents"
DATA_DIR = BASE_DIR / "data"

TENANT_ID = "TENANT-APEX-GLOBAL"
RNG = random.Random(42)


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)


def build_suppliers() -> list[dict]:
    return [
        {
            "supplier_id": "SUP-001",
            "tenant_id": TENANT_ID,
            "supplier_name": "FormosaSilicon Foundry Corp",
            "country": "Taiwan",
            "port_hub": "Port of Kaohsiung",
            "tier": "Tier-1",
            "financial_health_score": 88.5,
            "geopolitical_risk_index": 74.0,
            "esg_score": 91.0,
            "contracted_lead_time_days": 18,
            "unit_cost_multiplier": 1.00,
            "monthly_capacity_units": 50000,
            "is_approved_backup": True,
        },
        {
            "supplier_id": "SUP-002",
            "tenant_id": TENANT_ID,
            "supplier_name": "Hanbit Semiconductor Korea",
            "country": "South Korea",
            "port_hub": "Port of Busan",
            "tier": "Tier-1",
            "financial_health_score": 92.0,
            "geopolitical_risk_index": 38.0,
            "esg_score": 94.0,
            "contracted_lead_time_days": 16,
            "unit_cost_multiplier": 1.08,
            "monthly_capacity_units": 45000,
            "is_approved_backup": True,
        },
        {
            "supplier_id": "SUP-003",
            "tenant_id": TENANT_ID,
            "supplier_name": "NipponOptics & Sensorics Ltd",
            "country": "Japan",
            "port_hub": "Port of Yokohama",
            "tier": "Tier-1",
            "financial_health_score": 94.5,
            "geopolitical_risk_index": 22.0,
            "esg_score": 96.0,
            "contracted_lead_time_days": 14,
            "unit_cost_multiplier": 1.12,
            "monthly_capacity_units": 35000,
            "is_approved_backup": True,
        },
        {
            "supplier_id": "SUP-004",
            "tenant_id": TENANT_ID,
            "supplier_name": "RheinMetallics Power GmbH",
            "country": "Germany",
            "port_hub": "Port of Hamburg",
            "tier": "Tier-1",
            "financial_health_score": 61.0,
            "geopolitical_risk_index": 25.0,
            "esg_score": 95.0,
            "contracted_lead_time_days": 24,
            "unit_cost_multiplier": 1.18,
            "monthly_capacity_units": 25000,
            "is_approved_backup": False,
        },
        {
            "supplier_id": "SUP-005",
            "tenant_id": TENANT_ID,
            "supplier_name": "Saigon ElectroAssembly JSC",
            "country": "Vietnam",
            "port_hub": "Port of Cat Lai",
            "tier": "Tier-2",
            "financial_health_score": 79.0,
            "geopolitical_risk_index": 34.0,
            "esg_score": 82.0,
            "contracted_lead_time_days": 12,
            "unit_cost_multiplier": 0.92,
            "monthly_capacity_units": 60000,
            "is_approved_backup": True,
        },
        {
            "supplier_id": "SUP-006",
            "tenant_id": TENANT_ID,
            "supplier_name": "Penang Precision Microelectronics",
            "country": "Malaysia",
            "port_hub": "Port of Tanjung Pelepas",
            "tier": "Tier-1",
            "financial_health_score": 86.0,
            "geopolitical_risk_index": 28.0,
            "esg_score": 89.0,
            "contracted_lead_time_days": 11,
            "unit_cost_multiplier": 1.04,
            "monthly_capacity_units": 48000,
            "is_approved_backup": True,
        },
        {
            "supplier_id": "SUP-007",
            "tenant_id": TENANT_ID,
            "supplier_name": "SiliconValley Photonics Inc",
            "country": "United States",
            "port_hub": "Port of Los Angeles",
            "tier": "Tier-1",
            "financial_health_score": 90.0,
            "geopolitical_risk_index": 20.0,
            "esg_score": 93.0,
            "contracted_lead_time_days": 21,
            "unit_cost_multiplier": 1.22,
            "monthly_capacity_units": 22000,
            "is_approved_backup": True,
        },
        {
            "supplier_id": "SUP-008",
            "tenant_id": TENANT_ID,
            "supplier_name": "Nusantara Precision Chassis PT",
            "country": "Indonesia",
            "port_hub": "Port of Tanjung Priok",
            "tier": "Tier-2",
            "financial_health_score": 84.0,
            "geopolitical_risk_index": 26.0,
            "esg_score": 87.0,
            "contracted_lead_time_days": 7,
            "unit_cost_multiplier": 0.89,
            "monthly_capacity_units": 70000,
            "is_approved_backup": True,
        },
    ]


def build_components() -> list[dict]:
    return [
        {
            "component_id": "CMP-001",
            "tenant_id": TENANT_ID,
            "component_name": "SoC Neural Processor 5nm",
            "category": "Semiconductors",
            "primary_supplier_id": "SUP-001",
            "backup_supplier_id": "SUP-002",
            "criticality": "CRITICAL",
            "standard_unit_cost_usd": 145.00,
            "hs_code": "8542.31",
            "base_tariff_pct": 5.0,
        },
        {
            "component_id": "CMP-002",
            "tenant_id": TENANT_ID,
            "component_name": "High-Density LiFePO4 Cell Module",
            "category": "Energy Storage",
            "primary_supplier_id": "SUP-005",
            "backup_supplier_id": "SUP-002",
            "criticality": "HIGH",
            "standard_unit_cost_usd": 210.00,
            "hs_code": "8507.60",
            "base_tariff_pct": 7.5,
        },
        {
            "component_id": "CMP-003",
            "tenant_id": TENANT_ID,
            "component_name": "Industrial SiC MOSFET Power Stage",
            "category": "Power Electronics",
            "primary_supplier_id": "SUP-004",
            "backup_supplier_id": "SUP-006",
            "criticality": "CRITICAL",
            "standard_unit_cost_usd": 98.00,
            "hs_code": "8541.29",
            "base_tariff_pct": 4.0,
        },
        {
            "component_id": "CMP-004",
            "tenant_id": TENANT_ID,
            "component_name": "Precision MEMS Gyroscope Array",
            "category": "Sensors",
            "primary_supplier_id": "SUP-003",
            "backup_supplier_id": "SUP-007",
            "criticality": "HIGH",
            "standard_unit_cost_usd": 64.00,
            "hs_code": "9031.80",
            "base_tariff_pct": 3.5,
        },
        {
            "component_id": "CMP-005",
            "tenant_id": TENANT_ID,
            "component_name": "Multi-Layer RF PCB Substrate",
            "category": "Interconnects",
            "primary_supplier_id": "SUP-001",
            "backup_supplier_id": "SUP-006",
            "criticality": "CRITICAL",
            "standard_unit_cost_usd": 42.00,
            "hs_code": "8534.00",
            "base_tariff_pct": 6.0,
        },
        {
            "component_id": "CMP-006",
            "tenant_id": TENANT_ID,
            "component_name": "Optical Transceiver Laser Diode",
            "category": "Optoelectronics",
            "primary_supplier_id": "SUP-007",
            "backup_supplier_id": "SUP-003",
            "criticality": "HIGH",
            "standard_unit_cost_usd": 115.00,
            "hs_code": "8541.41",
            "base_tariff_pct": 4.5,
        },
        {
            "component_id": "CMP-007",
            "tenant_id": TENANT_ID,
            "component_name": "Ruggedized Aluminum CNC Chassis",
            "category": "Mechanical",
            "primary_supplier_id": "SUP-008",
            "backup_supplier_id": "SUP-005",
            "criticality": "MEDIUM",
            "standard_unit_cost_usd": 36.00,
            "hs_code": "7616.99",
            "base_tariff_pct": 2.0,
        },
        {
            "component_id": "CMP-008",
            "tenant_id": TENANT_ID,
            "component_name": "Automotive Grade MLCC Capacitor Bank",
            "category": "Passives",
            "primary_supplier_id": "SUP-003",
            "backup_supplier_id": "SUP-006",
            "criticality": "MEDIUM",
            "standard_unit_cost_usd": 18.50,
            "hs_code": "8532.24",
            "base_tariff_pct": 2.5,
        },
        {
            "component_id": "CMP-009",
            "tenant_id": TENANT_ID,
            "component_name": "Industrial Grade 3D NAND Flash 1TB",
            "category": "Memory",
            "primary_supplier_id": "SUP-002",
            "backup_supplier_id": "SUP-006",
            "criticality": "HIGH",
            "standard_unit_cost_usd": 55.00,
            "hs_code": "8523.51",
            "base_tariff_pct": 3.0,
        },
        {
            "component_id": "CMP-010",
            "tenant_id": TENANT_ID,
            "component_name": "Thermal Vapor Chamber Heatsink",
            "category": "Thermal",
            "primary_supplier_id": "SUP-008",
            "backup_supplier_id": "SUP-005",
            "criticality": "LOW",
            "standard_unit_cost_usd": 24.00,
            "hs_code": "8419.50",
            "base_tariff_pct": 2.0,
        },
    ]


def build_products() -> list[dict]:
    return [
        {
            "product_id": "PRD-001",
            "tenant_id": TENANT_ID,
            "product_name": "ApexEdge AI Gateway X9",
            "product_line": "Edge Computing",
            "selling_price_usd": 1250.00,
            "standard_cogs_usd": 835.00,
            "gross_margin_pct": 33.20,
            "monthly_demand_units": 3200,
        },
        {
            "product_id": "PRD-002",
            "tenant_id": TENANT_ID,
            "product_name": "ApexPower Industrial Inverter 50kW",
            "product_line": "Clean Energy Grid",
            "selling_price_usd": 2400.00,
            "standard_cogs_usd": 1680.00,
            "gross_margin_pct": 30.00,
            "monthly_demand_units": 1500,
        },
        {
            "product_id": "PRD-003",
            "tenant_id": TENANT_ID,
            "product_name": "ApexVision Autonomous LiDAR Node",
            "product_line": "Industrial Robotics",
            "selling_price_usd": 1680.00,
            "standard_cogs_usd": 1125.00,
            "gross_margin_pct": 33.04,
            "monthly_demand_units": 2100,
        },
        {
            "product_id": "PRD-004",
            "tenant_id": TENANT_ID,
            "product_name": "ApexGrid Smart Substation Controller",
            "product_line": "Clean Energy Grid",
            "selling_price_usd": 1950.00,
            "standard_cogs_usd": 1345.00,
            "gross_margin_pct": 31.03,
            "monthly_demand_units": 1800,
        },
        {
            "product_id": "PRD-005",
            "tenant_id": TENANT_ID,
            "product_name": "ApexCore Robotic Servo Drive",
            "product_line": "Industrial Robotics",
            "selling_price_usd": 980.00,
            "standard_cogs_usd": 665.00,
            "gross_margin_pct": 32.14,
            "monthly_demand_units": 2900,
        },
        {
            "product_id": "PRD-006",
            "tenant_id": TENANT_ID,
            "product_name": "ApexSense Telemetry Hub",
            "product_line": "Edge Computing",
            "selling_price_usd": 720.00,
            "standard_cogs_usd": 475.00,
            "gross_margin_pct": 34.03,
            "monthly_demand_units": 4100,
        },
    ]


def build_bom() -> list[dict]:
    rows = [
        ("BOM-001", "PRD-001", "CMP-001", 2, True),
        ("BOM-002", "PRD-001", "CMP-005", 2, True),
        ("BOM-003", "PRD-001", "CMP-009", 2, False),
        ("BOM-004", "PRD-001", "CMP-007", 1, False),
        ("BOM-005", "PRD-001", "CMP-010", 1, False),
        ("BOM-006", "PRD-002", "CMP-002", 4, False),
        ("BOM-007", "PRD-002", "CMP-003", 4, True),
        ("BOM-008", "PRD-002", "CMP-008", 6, False),
        ("BOM-009", "PRD-002", "CMP-007", 2, False),
        ("BOM-010", "PRD-003", "CMP-001", 1, True),
        ("BOM-011", "PRD-003", "CMP-004", 3, False),
        ("BOM-012", "PRD-003", "CMP-006", 2, True),
        ("BOM-013", "PRD-003", "CMP-007", 1, False),
        ("BOM-014", "PRD-004", "CMP-003", 3, True),
        ("BOM-015", "PRD-004", "CMP-005", 2, True),
        ("BOM-016", "PRD-004", "CMP-009", 1, False),
        ("BOM-017", "PRD-004", "CMP-008", 4, False),
        ("BOM-018", "PRD-005", "CMP-003", 2, True),
        ("BOM-019", "PRD-005", "CMP-004", 2, False),
        ("BOM-020", "PRD-005", "CMP-010", 1, False),
        ("BOM-021", "PRD-006", "CMP-005", 1, True),
        ("BOM-022", "PRD-006", "CMP-008", 3, False),
        ("BOM-023", "PRD-006", "CMP-009", 1, False),
        ("BOM-024", "PRD-006", "CMP-007", 1, False),
    ]
    return [
        {
            "bom_id": r[0],
            "tenant_id": TENANT_ID,
            "product_id": r[1],
            "component_id": r[2],
            "qty_per_unit": r[3],
            "is_single_source_risk": r[4],
        }
        for r in rows
    ]


def build_inventory(components: list[dict]) -> list[dict]:
    warehouses = [
        ("WH-ID", 1.0),
        ("WH-SG", 0.7),
        ("WH-DE", 0.5),
    ]
    inventory_rows = []
    idx = 1
    for comp in components:
        for wh_code, scale in warehouses:
            daily_burn = round(RNG.uniform(45, 190) * scale, 1)
            safety_stock = int(daily_burn * 10)
            if comp["component_id"] in ("CMP-001", "CMP-003") and wh_code == "WH-ID":
                on_hand = int(daily_burn * 4.5)
            else:
                on_hand = int(daily_burn * RNG.uniform(14, 26))
            reserved = int(on_hand * 0.22)
            inventory_rows.append(
                {
                    "inventory_id": f"INV-{idx:03d}",
                    "tenant_id": TENANT_ID,
                    "warehouse_code": wh_code,
                    "component_id": comp["component_id"],
                    "on_hand_qty": on_hand,
                    "reserved_qty": reserved,
                    "safety_stock_qty": safety_stock,
                    "daily_burn_rate": daily_burn,
                    "holding_cost_per_day_usd": round(
                        comp["standard_unit_cost_usd"] * 0.0018, 4
                    ),
                }
            )
            idx += 1
    return inventory_rows


def build_shipments(suppliers: list[dict], components: list[dict]) -> list[dict]:
    sup_map = {s["supplier_id"]: s for s in suppliers}
    hubs = ["WH-ID", "WH-SG", "WH-DE"]
    modes = ["SEA_FREIGHT", "AIR_FREIGHT", "EXPRESS_COURIER"]
    start_base = date(2025, 10, 1)

    shipments = []
    for i in range(1, 601):
        comp = RNG.choice(components)
        use_backup = RNG.random() < 0.22
        sup_id = (
            comp["backup_supplier_id"] if use_backup else comp["primary_supplier_id"]
        )
        sup = sup_map[sup_id]

        mode = RNG.choices(modes, weights=[0.72, 0.20, 0.08], k=1)[0]
        order_dt = start_base + timedelta(days=RNG.randint(0, 395))
        base_lead = sup["contracted_lead_time_days"]
        if mode == "AIR_FREIGHT":
            base_lead = max(3, int(base_lead * 0.35))
        elif mode == "EXPRESS_COURIER":
            base_lead = max(2, int(base_lead * 0.25))

        promised_dt = order_dt + timedelta(days=base_lead)

        port_congestion = round(
            min(
                100.0, max(5.0, RNG.gauss(sup["geopolitical_risk_index"] * 0.85, 14.0))
            ),
            2,
        )
        weather_severity = round(min(100.0, max(0.0, RNG.expovariate(1 / 22.0))), 2)
        health_at_order = round(
            min(
                100.0, max(35.0, sup["financial_health_score"] + RNG.uniform(-8.0, 5.0))
            ),
            2,
        )

        risk_signal = (
            0.045 * port_congestion
            + 0.035 * weather_severity
            + 0.040 * max(0.0, 80.0 - health_at_order)
            + (1.8 if mode == "SEA_FREIGHT" else 0.3)
        )
        noise = RNG.gauss(0, 1.1)
        raw_delay = int(round(risk_signal - 3.6 + noise))
        delay_days = max(0, raw_delay)
        is_delayed = 1 if delay_days >= 2 else 0

        actual_dt = promised_dt + timedelta(days=delay_days)
        order_qty = RNG.randint(250, 3500)
        unit_price = round(
            comp["standard_unit_cost_usd"]
            * sup["unit_cost_multiplier"]
            * RNG.uniform(0.98, 1.04),
            2,
        )
        freight_rate = (
            1.4 if mode == "SEA_FREIGHT" else (6.8 if mode == "AIR_FREIGHT" else 11.5)
        )
        freight_cost = round(order_qty * freight_rate + RNG.uniform(180, 950), 2)
        tariff_paid = round(
            order_qty * unit_price * (comp["base_tariff_pct"] / 100.0), 2
        )

        shipments.append(
            {
                "shipment_id": f"SHP-2026-{i:04d}",
                "tenant_id": TENANT_ID,
                "supplier_id": sup_id,
                "component_id": comp["component_id"],
                "origin_port": sup["port_hub"],
                "destination_hub": RNG.choice(hubs),
                "transport_mode": mode,
                "order_date": order_dt.isoformat(),
                "promised_date": promised_dt.isoformat(),
                "actual_arrival_date": actual_dt.isoformat(),
                "order_qty": order_qty,
                "unit_price_usd": unit_price,
                "freight_cost_usd": freight_cost,
                "tariff_paid_usd": tariff_paid,
                "port_congestion_index": port_congestion,
                "weather_severity_index": weather_severity,
                "supplier_health_at_order": health_at_order,
                "delay_days": delay_days,
                "is_delayed": is_delayed,
                "shipment_status": (
                    "DELIVERED_DELAYED" if is_delayed else "DELIVERED_ON_TIME"
                ),
            }
        )

    dirty_records = [
        {**shipments[10], "shipment_id": "SHP-ERR-0001", "order_qty": -450},
        {**shipments[20], "shipment_id": "SHP-ERR-0002", "supplier_id": ""},
        {**shipments[30], "shipment_id": "SHP-ERR-0003", "supplier_id": "SUP-999"},
        {**shipments[40], "shipment_id": "SHP-ERR-0004", "component_id": "CMP-999"},
        {
            **shipments[50],
            "shipment_id": "SHP-ERR-0005",
            "order_date": "2026-08-15",
            "actual_arrival_date": "2026-07-01",
        },
        {**shipments[60], "shipment_id": "SHP-ERR-0006", "unit_price_usd": 0.0},
        {**shipments[70], "shipment_id": "SHP-ERR-0007", "unit_price_usd": 999999.99},
        {
            **shipments[80],
            "shipment_id": "SHP-ERR-0008",
            "port_congestion_index": 185.5,
        },
        {**shipments[90], "shipment_id": "SHP-ERR-0009", "delay_days": -7},
        {
            **shipments[100],
            "shipment_id": "SHP-ERR-0010",
            "transport_mode": "TELEPORTATION",
        },
        {**shipments[110], "shipment_id": "SHP-2026-0111"},
        {**shipments[120], "shipment_id": "SHP-ERR-0012", "tenant_id": ""},
        {**shipments[130], "shipment_id": "SHP-ERR-0013", "freight_cost_usd": -1200.0},
        {**shipments[140], "shipment_id": "SHP-ERR-0014", "order_date": "2026/99/45"},
        {**shipments[150], "shipment_id": "SHP-ERR-0015", "tariff_paid_usd": -88.5},
    ]

    combined = shipments + dirty_records
    RNG.shuffle(combined)
    return combined


def build_corporate_documents() -> list[dict]:
    return [
        {
            "doc_id": "DOC-001",
            "tenant_id": TENANT_ID,
            "title": "Master Supply Agreement — FormosaSilicon Foundry Corp (SUP-001)",
            "doc_type": "CONTRACT",
            "effective_date": "2026-01-15",
            "content": (
                "ApexGlobal Manufacturing Corp maintains an exclusive volume tier agreement with "
                "FormosaSilicon Foundry Corp (SUP-001), headquartered in Hsinchu and shipping exclusively "
                "through Port of Kaohsiung. SUP-001 supplies 85% of SoC Neural Processor 5nm (CMP-001) "
                "and 75% of Multi-Layer RF PCB Substrate (CMP-005). Under Clause 14.2, if maritime transit "
                "from Port of Kaohsiung is delayed exceeding 10 calendar days due to port congestion or "
                "maritime exclusion zones, ApexGlobal is authorized to invoke dual-sourcing step-in rights "
                "and reallocate up to 60% of monthly volume to qualified backup supplier Hanbit Semiconductor "
                "Korea (SUP-002) for CMP-001 and Penang Precision Microelectronics (SUP-006) for CMP-005 "
                "without incurring volume shortfall penalties."
            ),
        },
        {
            "doc_id": "DOC-002",
            "tenant_id": TENANT_ID,
            "title": "Q4 Maritime & Geopolitical Risk Intelligence Bulletin — Taiwan Strait",
            "doc_type": "RISK_INTELLIGENCE",
            "effective_date": "2026-11-01",
            "content": (
                "Regional maritime telemetry indicates severe vessel queuing at Port of Kaohsiung with "
                "congestion index surging to 86.4/100 and average berth waiting times extending by 11 to 14 days. "
                "FormosaSilicon Foundry Corp (SUP-001) exports for SoC Neural Processor 5nm (CMP-001) and "
                "Multi-Layer RF PCB Substrate (CMP-005) face immediate schedule slippage. Furthermore, marine "
                "war-risk hull insurance surcharges on Taiwan Strait container routes have increased freight "
                "expenses by 38%."
            ),
        },
        {
            "doc_id": "DOC-003",
            "tenant_id": TENANT_ID,
            "title": "Senior Syndicated Credit Facility & Financial Debt Covenant Policy (COV-FIN-01)",
            "doc_type": "FINANCIAL_POLICY",
            "effective_date": "2026-03-01",
            "content": (
                "Under Section 7.1 of the Senior Credit Facility Agreement (Covenant ID: COV-FIN-01), "
                "ApexGlobal Manufacturing Corp must maintain a Consolidated Gross Margin of at least 28.0% "
                "measured quarterly across all manufacturing divisions. Any supply chain mitigation action—"
                "including expedited air freight, emergency spot buys, or high-tariff supplier switching—"
                "that compresses consolidated gross margin below 28.0% triggers a Technical Covenant Breach "
                "requiring immediate CFO and Supply Chain Director sign-off plus lender waiver notification."
            ),
        },
        {
            "doc_id": "DOC-004",
            "tenant_id": TENANT_ID,
            "title": "SOP-SC-04: Emergency Air-Freight & Backup Supplier Activation Protocol",
            "doc_type": "SOP",
            "effective_date": "2026-04-10",
            "content": (
                "Standard Operating Procedure SOP-SC-04 governs emergency procurement interventions when "
                "warehouse days-of-supply at primary assembly hub WH-ID falls below 6.0 days for CRITICAL "
                "components (CMP-001, CMP-003, CMP-005). Section 4.3 mandates that any emergency mitigation "
                "package whose total incremental cost (air-freight premium + unit price variance + tariff delta) "
                "exceeds USD 50,000.00 MUST be routed to the Human-in-the-Loop (HITL) approval queue for "
                "explicit authorization by a user holding the SupplyChainDirector role prior to ERP execution."
            ),
        },
        {
            "doc_id": "DOC-005",
            "tenant_id": TENANT_ID,
            "title": "Qualified Backup Supplier Technical & Capacity Audit — SUP-002 & SUP-006",
            "doc_type": "AUDIT_REPORT",
            "effective_date": "2026-06-20",
            "content": (
                "Quality Engineering completed full PPAP Level-3 qualification for Hanbit Semiconductor Korea "
                "(SUP-002, Port of Busan) as the primary backup for SoC Neural Processor 5nm (CMP-001) at an "
                "8% unit cost premium (USD 156.60/unit vs USD 145.00/unit) with 16-day sea lead time or 3-day "
                "air transit. Penang Precision Microelectronics (SUP-006, Port of Tanjung Pelepas) is fully "
                "certified as backup for Industrial SiC MOSFET Power Stage (CMP-003) and Multi-Layer RF PCB "
                "Substrate (CMP-005) at a 4% unit cost premium and 11-day sea lead time."
            ),
        },
        {
            "doc_id": "DOC-006",
            "tenant_id": TENANT_ID,
            "title": "Cross-Border Semiconductor & Power Electronics Tariff Directive (TAR-2026-88)",
            "doc_type": "REGULATORY",
            "effective_date": "2026-09-15",
            "content": (
                "Trade Compliance Directive TAR-2026-88 imposes an additional 18.0% retaliatory customs duty "
                "on semiconductor wafers and RF PCB substrates (HS Codes 8542.31 and 8534.00) routed through "
                "non-FTA transshipment ports unless originating from ASEAN-RCEP or Korea-FTA certified fabs "
                "such as Hanbit Semiconductor Korea (SUP-002) or Penang Precision Microelectronics (SUP-006). "
                "Switching CMP-001 and CMP-005 orders to SUP-002 and SUP-006 avoids the 18.0% tariff surcharge."
            ),
        },
        {
            "doc_id": "DOC-007",
            "tenant_id": TENANT_ID,
            "title": "Supplier Financial Health & Credit Watch Bulletin — RheinMetallics GmbH (SUP-004)",
            "doc_type": "RISK_INTELLIGENCE",
            "effective_date": "2026-10-18",
            "content": (
                "Credit risk monitoring placed RheinMetallics Power GmbH (SUP-004, Port of Hamburg) on "
                "Elevated Credit Watch after its financial health score dropped from 84.0 to 61.0 due to "
                "European energy cost restructuring and short-term liquidity tightening. SUP-004 is the "
                "single-source primary supplier for Industrial SiC MOSFET Power Stage (CMP-003), which is "
                "essential for ApexPower Industrial Inverter 50kW (PRD-002), ApexGrid Smart Substation "
                "Controller (PRD-004), and ApexCore Robotic Servo Drive (PRD-005). Pre-emptive volume shifting "
                "of 40% to Penang Precision Microelectronics (SUP-006) is recommended."
            ),
        },
        {
            "doc_id": "DOC-008",
            "tenant_id": TENANT_ID,
            "title": "Product Line BOM Dependency & Margin Resilience Analysis (PRD-001 & PRD-002)",
            "doc_type": "FINANCIAL_ANALYSIS",
            "effective_date": "2026-10-25",
            "content": (
                "ApexEdge AI Gateway X9 (PRD-001, selling price USD 1,250, baseline gross margin 33.20%) "
                "consumes 2 units of CMP-001 and 2 units of CMP-005 per finished device, making it highly "
                "sensitive to disruptions at FormosaSilicon Foundry Corp (SUP-001). Meanwhile, ApexPower "
                "Industrial Inverter 50kW (PRD-002, selling price USD 2,400, baseline gross margin 30.00%) "
                "has only a 2.00 percentage point buffer above the COV-FIN-01 covenant floor of 28.0%. "
                "A combined spike in CMP-003 cost and air-freight charges on PRD-002 can push its product "
                "gross margin down to 25.4%, jeopardizing consolidated covenant compliance."
            ),
        },
        {
            "doc_id": "DOC-009",
            "tenant_id": TENANT_ID,
            "title": "SOP-LOG-09: Maritime Carrier Force Majeure & Port Rerouting Protocol",
            "doc_type": "SOP",
            "effective_date": "2026-05-12",
            "content": (
                "Under SOP-LOG-09, when Port of Kaohsiung or Port of Hamburg congestion index exceeds 75.0, "
                "Logistics Operations must split shipments into 70% sea freight via regional hub Port of "
                "Tanjung Pelepas or Port of Busan and 30% expedited air freight directly to WH-ID (Batam/Jakarta) "
                "to prevent assembly line stoppage while containing freight spend."
            ),
        },
        {
            "doc_id": "DOC-010",
            "tenant_id": TENANT_ID,
            "title": "ESG & Responsible Minerals Compliance Mandate (ESG-2026-03)",
            "doc_type": "REGULATORY",
            "effective_date": "2026-02-01",
            "content": (
                "Policy ESG-2026-03 prohibits procurement from any Tier-1 or Tier-2 supplier whose ESG "
                "compliance rating falls below 80.0 or lacks conflict-mineral traceability for LiFePO4 battery "
                "cells (CMP-002) and power semiconductors (CMP-003). All current qualified suppliers "
                "(SUP-001 through SUP-008) exceed the 80.0 threshold, with NipponOptics (SUP-003, 96.0) and "
                "RheinMetallics (SUP-004, 95.0) leading ESG governance."
            ),
        },
        {
            "doc_id": "DOC-011",
            "tenant_id": TENANT_ID,
            "title": "ASEAN Nearshoring & Capacity Expansion Memorandum — SUP-005 & SUP-008",
            "doc_type": "STRATEGY_MEMO",
            "effective_date": "2026-08-30",
            "content": (
                "To reduce trans-Pacific and East Asian chokepoint exposure, ApexGlobal expanded frame "
                "contracts with Saigon ElectroAssembly JSC (SUP-005, Vietnam) and Nusantara Precision Chassis "
                "PT (SUP-008, Indonesia). SUP-008 delivers Ruggedized Aluminum CNC Chassis (CMP-007) and "
                "Thermal Vapor Chamber Heatsink (CMP-010) to WH-ID within 7 days at 11% below global benchmark cost."
            ),
        },
        {
            "doc_id": "DOC-012",
            "tenant_id": TENANT_ID,
            "title": "Enterprise AI Governance, RBAC & Data Security Policy (GOV-SEC-01)",
            "doc_type": "SECURITY_POLICY",
            "effective_date": "2026-07-01",
            "content": (
                "Policy GOV-SEC-01 enforces strict Role-Based Access Control (RBAC) across NexusCore AI: "
                "Viewer role has read-only access to dashboards and public risk summaries; Analyst role may "
                "execute SQL analytics, ML risk scoring, and Monte Carlo simulations; SupplyChainDirector role "
                "holds exclusive authority to approve HITL mitigation packages above USD 50,000 and modify "
                "supplier allocation weights. All prompt inputs must pass adversarial injection inspection."
            ),
        },
    ]


def build_golden_dataset() -> list[dict]:
    return [
        {
            "eval_id": "EVAL-001",
            "question": (
                "Jika Port of Kaohsiung mengalami kemacetan parah (indeks > 85), produk ApexGlobal mana saja "
                "yang terdampak melalui rantai pasok komponen, pemasok cadangan mana yang memenuhi syarat "
                "kontrak & bebas tarif tambahan TAR-2026-88, dan apakah biaya mitigasi memicu HITL?"
            ),
            "expected_entities": [
                "Port of Kaohsiung",
                "FormosaSilicon Foundry Corp",
                "CMP-001",
                "CMP-005",
                "PRD-001",
                "PRD-003",
                "PRD-004",
                "PRD-006",
                "Hanbit Semiconductor Korea",
                "Penang Precision Microelectronics",
            ],
            "expected_citations": [
                "DOC-001",
                "DOC-002",
                "DOC-004",
                "DOC-005",
                "DOC-006",
            ],
            "expected_hitl_required": True,
            "expected_covenant_breach": False,
        },
        {
            "eval_id": "EVAL-002",
            "question": (
                "Evaluasi risiko kebangkrutan atau penurunan skor kesehatan finansial RheinMetallics Power "
                "GmbH (SUP-004) terhadap lini produk ApexPower Industrial Inverter 50kW (PRD-002) dan "
                "kepatuhan kovenan utang COV-FIN-01 jika dilakukan air-freight darurat."
            ),
            "expected_entities": [
                "RheinMetallics Power GmbH",
                "CMP-003",
                "PRD-002",
                "COV-FIN-01",
                "Penang Precision Microelectronics",
            ],
            "expected_citations": ["DOC-003", "DOC-004", "DOC-007", "DOC-008"],
            "expected_hitl_required": True,
            "expected_covenant_breach": True,
        },
        {
            "eval_id": "EVAL-003",
            "question": (
                "Berapa hari sisa ketahanan stok (days of supply) untuk CMP-001 dan CMP-003 di gudang "
                "WH-ID saat ini, dan apakah sudah melanggar ambang batas darurat SOP-SC-04?"
            ),
            "expected_entities": ["CMP-001", "CMP-003", "WH-ID", "SOP-SC-04"],
            "expected_citations": ["DOC-004"],
            "expected_hitl_required": False,
            "expected_covenant_breach": False,
        },
        {
            "eval_id": "EVAL-004",
            "question": (
                "Bandingkan profil biaya, lead time, dan skor ESG antara pemasok utama dan pemasok "
                "cadangan untuk komponen High-Density LiFePO4 Cell Module (CMP-002) berdasarkan ESG-2026-03."
            ),
            "expected_entities": [
                "CMP-002",
                "Saigon ElectroAssembly JSC",
                "Hanbit Semiconductor Korea",
                "ESG-2026-03",
            ],
            "expected_citations": ["DOC-005", "DOC-010", "DOC-011"],
            "expected_hitl_required": False,
            "expected_covenant_breach": False,
        },
        {
            "eval_id": "EVAL-005",
            "question": (
                "Jalankan simulasi risiko keterlambatan pada pemasok dengan port_congestion_index tertinggi "
                "dan tentukan strategi split shipment sesuai SOP-LOG-09."
            ),
            "expected_entities": ["Port of Kaohsiung", "SOP-LOG-09", "WH-ID"],
            "expected_citations": ["DOC-002", "DOC-009"],
            "expected_hitl_required": True,
            "expected_covenant_breach": False,
        },
        {
            "eval_id": "EVAL-006",
            "question": (
                "Siapa role yang berwenang menyetujui paket mitigasi senilai USD 75,000 menurut kebijakan "
                "GOV-SEC-01 dan SOP-SC-04?"
            ),
            "expected_entities": ["SupplyChainDirector", "GOV-SEC-01", "SOP-SC-04"],
            "expected_citations": ["DOC-004", "DOC-012"],
            "expected_hitl_required": True,
            "expected_covenant_breach": False,
        },
    ]


def write_csv(filepath: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with filepath.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ensure_dirs()

    suppliers = build_suppliers()
    components = build_components()
    products = build_products()
    bom = build_bom()
    inventory = build_inventory(components)
    shipments = build_shipments(suppliers, components)
    corp_docs = build_corporate_documents()
    golden = build_golden_dataset()

    write_csv(RAW_DIR / "suppliers.csv", suppliers)
    write_csv(RAW_DIR / "components.csv", components)
    write_csv(RAW_DIR / "products.csv", products)
    write_csv(RAW_DIR / "bom.csv", bom)
    write_csv(RAW_DIR / "inventory.csv", inventory)
    write_csv(RAW_DIR / "shipments_history.csv", shipments)

    with (DOCS_DIR / "corp_docs.json").open("w", encoding="utf-8") as f:
        json.dump(corp_docs, f, indent=2, ensure_ascii=False)

    with (DATA_DIR / "golden_dataset.json").open("w", encoding="utf-8") as f:
        json.dump(golden, f, indent=2, ensure_ascii=False)

    print("=== Fase 1 Dataset Seeding Selesai ===")
    print(f"- suppliers.csv         : {len(suppliers)} baris")
    print(f"- components.csv        : {len(components)} baris")
    print(f"- products.csv          : {len(products)} baris")
    print(f"- bom.csv               : {len(bom)} baris")
    print(f"- inventory.csv         : {len(inventory)} baris")
    print(
        f"- shipments_history.csv : {len(shipments)} baris (600 bersih + 15 anomali DLQ)"
    )
    print(f"- corp_docs.json        : {len(corp_docs)} dokumen korporat")
    print(f"- golden_dataset.json   : {len(golden)} kasus uji evaluasi")


if __name__ == "__main__":
    main()
