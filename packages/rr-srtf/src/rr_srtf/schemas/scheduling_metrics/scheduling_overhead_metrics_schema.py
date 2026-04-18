from pydantic import BaseModel, ConfigDict, Field


class SchedulingOverheadMetricsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ctx_switch_count: int = Field(alias="ctx_count")
    ctx_switch_time: int = Field(alias="ctx_time")
    scheduler: int
