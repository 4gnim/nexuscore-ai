import operator
from typing import Annotated, Any, TypedDict
from pydantic import BaseModel, Field


class InvestigationPlan(BaseModel):
    """Rencana investigasi terstruktur hasil Meta-Planner Agent."""

    target_component_id: str = Field(
        default="CMP-001",
        description="Kode komponen utama yang diselidiki (CMP-001..CMP-010)",
    )
    target_warehouse: str = Field(
        default="WH-ID",
        description="Kode gudang target (WH-ID, WH-SG, WH-DE)",
    )
    assumed_port_congestion: float = Field(
        default=86.4,
        description="Indeks kemacetan pelabuhan (0-100) untuk simulasi",
    )
    assumed_tariff_surcharge_pct: float = Field(
        default=18.0,
        description="Persentase tarif bea cukai tambahan untuk simulasi",
    )
    graph_subtask: str = Field(..., description="Sub-tugas investigasi graf & dokumen")
    ml_sql_subtask: str = Field(
        ..., description="Sub-tugas analitik SQL, ML, & Monte Carlo"
    )
    compliance_subtask: str = Field(..., description="Sub-tugas audit kovenan & SOP")


class CriticReview(BaseModel):
    """Hasil audit adversarial dari Red-Team Critic Agent."""

    passed: bool = Field(
        ..., description="True jika seluruh angka konsisten dengan bukti dokumen/graf"
    )
    consistency_score: float = Field(default=0.95, ge=0.0, le=1.0)
    critique_notes: str = Field(..., description="Catatan verifikasi silang antar-agen")
    discrepancies_found: list[str] = Field(default_factory=list)


class SwarmState(TypedDict):
    """State bersama untuk orkestrasi LangGraph Hierarchical Multi-Agent Swarm."""

    query: str
    tenant_id: str
    user_id: str
    user_role: str
    plan: dict[str, Any]
    worker_results: Annotated[list[dict[str, Any]], operator.add]
    critic_review: dict[str, Any]
    revision_count: int
    final_response: dict[str, Any]
    trace_events: Annotated[list[dict[str, Any]], operator.add]
