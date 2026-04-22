from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class ScenarioCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scenario_id: int
    name: str
    created_at: str
    summary: dict
    points: Optional[List[dict]] = None
    ga_result: Optional[List[dict]] = None
    sa_result: Optional[List[dict]] = None
