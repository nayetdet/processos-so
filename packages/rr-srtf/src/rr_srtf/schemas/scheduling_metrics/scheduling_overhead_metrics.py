from pydantic import BaseModel, ConfigDict

class SchedulingOverheadMetricsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ctx_switch_count: int
    ctx_switch_time: int
    scheduler: int
