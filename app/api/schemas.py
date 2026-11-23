from typing import Literal
from pydantic import BaseModel, Field


class InvestigateRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=4000,
        description="Pertanyaan atau skenario disrupsi rantai pasok untuk diinvestigasi Swarm",
    )
    tenant_id: str = Field(default="TENANT-APEX-GLOBAL")
    user_id: str = Field(default="USR-ANA-01")
    user_role: Literal["Viewer", "Analyst", "SupplyChainDirector", "Admin"] = Field(
        default="Analyst"
    )


class SimulationRequest(BaseModel):
    component_id: str = Field(
        default="CMP-001", description="Kode komponen (CMP-001..CMP-010)"
    )
    warehouse_code: str = Field(default="WH-ID")
    port_congestion_index: float = Field(default=86.4, ge=0.0, le=100.0)
    tariff_surcharge_pct: float = Field(default=18.0, ge=0.0, le=50.0)
    air_freight_share: float = Field(default=0.30, ge=0.0, le=1.0)
    backup_allocation_share: float = Field(default=0.60, ge=0.0, le=1.0)
    tenant_id: str = Field(default="TENANT-APEX-GLOBAL")
    user_id: str = Field(default="USR-ANA-01")
    user_role: Literal["Viewer", "Analyst", "SupplyChainDirector", "Admin"] = Field(
        default="Analyst"
    )


class HITLDecisionRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    actor_user_id: str = Field(default="USR-DIR-01")
    actor_role: Literal["Viewer", "Analyst", "SupplyChainDirector", "Admin"] = Field(
        default="SupplyChainDirector"
    )
    notes: str = Field(default="", max_length=1000)
    tenant_id: str = Field(default="TENANT-APEX-GLOBAL")
