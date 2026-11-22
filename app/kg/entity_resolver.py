import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalEntitySpec:
    entity_id: str
    canonical_name: str
    entity_type: str
    canonical_code: str
    aliases: tuple[str, ...]


# Master Canonical Registry untuk Entity Resolution & Deduplication lintas dokumen dan tabel SQL
CANONICAL_SPECS: list[CanonicalEntitySpec] = [
    # Organization
    CanonicalEntitySpec(
        "ENT-ORG-APEX",
        "ApexGlobal Manufacturing Corp",
        "ORGANIZATION",
        "APEX-GLOBAL",
        (
            "apexglobal",
            "apexglobal manufacturing",
            "apexglobal manufacturing corp",
            "apex global",
        ),
    ),
    # Suppliers
    CanonicalEntitySpec(
        "ENT-SUP-001",
        "FormosaSilicon Foundry Corp",
        "SUPPLIER",
        "SUP-001",
        (
            "sup-001",
            "formosasilicon",
            "formosasilicon foundry",
            "formosasilicon foundry corp",
        ),
    ),
    CanonicalEntitySpec(
        "ENT-SUP-002",
        "Hanbit Semiconductor Korea",
        "SUPPLIER",
        "SUP-002",
        ("sup-002", "hanbit", "hanbit semiconductor", "hanbit semiconductor korea"),
    ),
    CanonicalEntitySpec(
        "ENT-SUP-003",
        "NipponOptics & Sensorics Ltd",
        "SUPPLIER",
        "SUP-003",
        (
            "sup-003",
            "nipponoptics",
            "nipponoptics & sensorics",
            "nipponoptics & sensorics ltd",
        ),
    ),
    CanonicalEntitySpec(
        "ENT-SUP-004",
        "RheinMetallics Power GmbH",
        "SUPPLIER",
        "SUP-004",
        (
            "sup-004",
            "rheinmetallics",
            "rheinmetallics power",
            "rheinmetallics power gmbh",
            "rheinmetallics gmbh",
        ),
    ),
    CanonicalEntitySpec(
        "ENT-SUP-005",
        "Saigon ElectroAssembly JSC",
        "SUPPLIER",
        "SUP-005",
        ("sup-005", "saigon electroassembly", "saigon electroassembly jsc"),
    ),
    CanonicalEntitySpec(
        "ENT-SUP-006",
        "Penang Precision Microelectronics",
        "SUPPLIER",
        "SUP-006",
        ("sup-006", "penang precision", "penang precision microelectronics"),
    ),
    CanonicalEntitySpec(
        "ENT-SUP-007",
        "SiliconValley Photonics Inc",
        "SUPPLIER",
        "SUP-007",
        ("sup-007", "siliconvalley photonics", "siliconvalley photonics inc"),
    ),
    CanonicalEntitySpec(
        "ENT-SUP-008",
        "Nusantara Precision Chassis PT",
        "SUPPLIER",
        "SUP-008",
        (
            "sup-008",
            "nusantara precision",
            "nusantara precision chassis",
            "nusantara precision chassis pt",
        ),
    ),
    # Components
    CanonicalEntitySpec(
        "ENT-CMP-001",
        "SoC Neural Processor 5nm",
        "COMPONENT",
        "CMP-001",
        (
            "cmp-001",
            "soc neural processor 5nm",
            "soc neural processor",
            "5nm processor",
        ),
    ),
    CanonicalEntitySpec(
        "ENT-CMP-002",
        "High-Density LiFePO4 Cell Module",
        "COMPONENT",
        "CMP-002",
        (
            "cmp-002",
            "high-density lifepo4 cell module",
            "lifepo4 cell module",
            "lifepo4 battery cells",
        ),
    ),
    CanonicalEntitySpec(
        "ENT-CMP-003",
        "Industrial SiC MOSFET Power Stage",
        "COMPONENT",
        "CMP-003",
        (
            "cmp-003",
            "industrial sic mosfet power stage",
            "sic mosfet power stage",
            "sic mosfet",
        ),
    ),
    CanonicalEntitySpec(
        "ENT-CMP-004",
        "Precision MEMS Gyroscope Array",
        "COMPONENT",
        "CMP-004",
        ("cmp-004", "precision mems gyroscope array", "mems gyroscope"),
    ),
    CanonicalEntitySpec(
        "ENT-CMP-005",
        "Multi-Layer RF PCB Substrate",
        "COMPONENT",
        "CMP-005",
        ("cmp-005", "multi-layer rf pcb substrate", "rf pcb substrate", "rf pcb"),
    ),
    CanonicalEntitySpec(
        "ENT-CMP-006",
        "Optical Transceiver Laser Diode",
        "COMPONENT",
        "CMP-006",
        ("cmp-006", "optical transceiver laser diode", "laser diode"),
    ),
    CanonicalEntitySpec(
        "ENT-CMP-007",
        "Ruggedized Aluminum CNC Chassis",
        "COMPONENT",
        "CMP-007",
        ("cmp-007", "ruggedized aluminum cnc chassis", "aluminum cnc chassis"),
    ),
    CanonicalEntitySpec(
        "ENT-CMP-008",
        "Automotive Grade MLCC Capacitor Bank",
        "COMPONENT",
        "CMP-008",
        ("cmp-008", "automotive grade mlcc capacitor bank", "mlcc capacitor bank"),
    ),
    CanonicalEntitySpec(
        "ENT-CMP-009",
        "Industrial Grade 3D NAND Flash 1TB",
        "COMPONENT",
        "CMP-009",
        ("cmp-009", "industrial grade 3d nand flash 1tb", "3d nand flash"),
    ),
    CanonicalEntitySpec(
        "ENT-CMP-010",
        "Thermal Vapor Chamber Heatsink",
        "COMPONENT",
        "CMP-010",
        ("cmp-010", "thermal vapor chamber heatsink", "vapor chamber heatsink"),
    ),
    # Products
    CanonicalEntitySpec(
        "ENT-PRD-001",
        "ApexEdge AI Gateway X9",
        "PRODUCT",
        "PRD-001",
        ("prd-001", "apexedge ai gateway x9", "apexedge ai gateway"),
    ),
    CanonicalEntitySpec(
        "ENT-PRD-002",
        "ApexPower Industrial Inverter 50kW",
        "PRODUCT",
        "PRD-002",
        (
            "prd-002",
            "apexpower industrial inverter 50kw",
            "apexpower industrial inverter",
        ),
    ),
    CanonicalEntitySpec(
        "ENT-PRD-003",
        "ApexVision Autonomous LiDAR Node",
        "PRODUCT",
        "PRD-003",
        ("prd-003", "apexvision autonomous lidar node", "apexvision lidar"),
    ),
    CanonicalEntitySpec(
        "ENT-PRD-004",
        "ApexGrid Smart Substation Controller",
        "PRODUCT",
        "PRD-004",
        ("prd-004", "apexgrid smart substation controller", "apexgrid controller"),
    ),
    CanonicalEntitySpec(
        "ENT-PRD-005",
        "ApexCore Robotic Servo Drive",
        "PRODUCT",
        "PRD-005",
        ("prd-005", "apexcore robotic servo drive", "apexcore servo drive"),
    ),
    CanonicalEntitySpec(
        "ENT-PRD-006",
        "ApexSense Telemetry Hub",
        "PRODUCT",
        "PRD-006",
        ("prd-006", "apexsense telemetry hub", "apexsense hub"),
    ),
    # Ports & Warehouses
    CanonicalEntitySpec(
        "ENT-PORT-KAOHSIUNG",
        "Port of Kaohsiung",
        "PORT_HUB",
        "PORT-KHH",
        ("port of kaohsiung", "kaohsiung", "kaohsiung port"),
    ),
    CanonicalEntitySpec(
        "ENT-PORT-BUSAN",
        "Port of Busan",
        "PORT_HUB",
        "PORT-PUS",
        ("port of busan", "busan", "busan port"),
    ),
    CanonicalEntitySpec(
        "ENT-PORT-HAMBURG",
        "Port of Hamburg",
        "PORT_HUB",
        "PORT-HAM",
        ("port of hamburg", "hamburg", "hamburg port"),
    ),
    CanonicalEntitySpec(
        "ENT-PORT-PTP",
        "Port of Tanjung Pelepas",
        "PORT_HUB",
        "PORT-PTP",
        ("port of tanjung pelepas", "tanjung pelepas"),
    ),
    CanonicalEntitySpec(
        "ENT-WH-ID",
        "Warehouse Hub Indonesia (WH-ID)",
        "WAREHOUSE",
        "WH-ID",
        ("wh-id", "warehouse wh-id", "hub wh-id", "assembly hub wh-id"),
    ),
    # Policies, Covenants, Directives & Roles
    CanonicalEntitySpec(
        "ENT-POL-COV-FIN-01",
        "Financial Debt Covenant COV-FIN-01",
        "POLICY",
        "COV-FIN-01",
        (
            "cov-fin-01",
            "financial debt covenant cov-fin-01",
            "covenant cov-fin-01",
            "technical covenant breach",
        ),
    ),
    CanonicalEntitySpec(
        "ENT-POL-SOP-SC-04",
        "Emergency Protocol SOP-SC-04",
        "POLICY",
        "SOP-SC-04",
        (
            "sop-sc-04",
            "standard operating procedure sop-sc-04",
            "emergency protocol sop-sc-04",
        ),
    ),
    CanonicalEntitySpec(
        "ENT-POL-SOP-LOG-09",
        "Maritime Rerouting Protocol SOP-LOG-09",
        "POLICY",
        "SOP-LOG-09",
        ("sop-log-09", "maritime rerouting protocol sop-log-09"),
    ),
    CanonicalEntitySpec(
        "ENT-POL-TAR-2026-88",
        "Tariff Directive TAR-2026-88",
        "REGULATION",
        "TAR-2026-88",
        (
            "tar-2026-88",
            "trade compliance directive tar-2026-88",
            "tariff directive tar-2026-88",
        ),
    ),
    CanonicalEntitySpec(
        "ENT-POL-ESG-2026-03",
        "ESG Mandate ESG-2026-03",
        "REGULATION",
        "ESG-2026-03",
        ("esg-2026-03", "policy esg-2026-03", "esg mandate esg-2026-03"),
    ),
    CanonicalEntitySpec(
        "ENT-POL-GOV-SEC-01",
        "Security & RBAC Policy GOV-SEC-01",
        "POLICY",
        "GOV-SEC-01",
        ("gov-sec-01", "policy gov-sec-01", "rbac policy gov-sec-01"),
    ),
    CanonicalEntitySpec(
        "ENT-ROLE-DIRECTOR",
        "SupplyChainDirector",
        "ROLE",
        "ROLE-SCD",
        ("supplychaindirector", "supply chain director", "director role"),
    ),
]


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\-\s&]", " ", text.lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def resolve_entity(
    raw_name: str,
    raw_type: str = "CONCEPT",
    raw_code: str | None = None,
) -> tuple[str, str, str, str | None]:
    """Memetakan nama/kode entitas mentah ke (entity_id, canonical_name, entity_type, canonical_code)."""
    norm_name = _normalize_text(raw_name)
    norm_code = _normalize_text(raw_code) if raw_code else ""

    # 1. Exact code or alias match against canonical registry
    for spec in CANONICAL_SPECS:
        if norm_code and norm_code == spec.canonical_code.lower():
            return (
                spec.entity_id,
                spec.canonical_name,
                spec.entity_type,
                spec.canonical_code,
            )
        if norm_name in spec.aliases:
            return (
                spec.entity_id,
                spec.canonical_name,
                spec.entity_type,
                spec.canonical_code,
            )

    # 2. Substring match for embedded codes like "FormosaSilicon (SUP-001)"
    for spec in CANONICAL_SPECS:
        code_token = spec.canonical_code.lower()
        if re.search(rf"\b{re.escape(code_token)}\b", norm_name):
            return (
                spec.entity_id,
                spec.canonical_name,
                spec.entity_type,
                spec.canonical_code,
            )
        for alias in spec.aliases:
            if len(alias) >= 7 and alias in norm_name:
                return (
                    spec.entity_id,
                    spec.canonical_name,
                    spec.entity_type,
                    spec.canonical_code,
                )

    # 3. Deterministic fallback entity ID for novel domain concepts
    clean_display = re.sub(r"\s+", " ", raw_name).strip()
    digest = hashlib.sha1(norm_name.encode("utf-8")).hexdigest()[:10].upper()
    clean_type = re.sub(r"[^A-Z_]", "", raw_type.upper()) or "CONCEPT"
    return f"ENT-{clean_type[:6]}-{digest}", clean_display, clean_type, raw_code


def make_relation_id(subject_id: str, predicate: str, object_id: str) -> str:
    norm_pred = re.sub(r"[^A-Z0-9_]", "_", predicate.upper().strip())
    norm_pred = re.sub(r"_+", "_", norm_pred).strip("_") or "RELATED_TO"
    digest = (
        hashlib.sha1(f"{subject_id}::{norm_pred}::{object_id}".encode("utf-8"))
        .hexdigest()[:12]
        .upper()
    )
    return f"REL-{digest}"
