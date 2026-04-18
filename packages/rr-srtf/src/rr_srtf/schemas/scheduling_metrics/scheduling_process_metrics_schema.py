from pydantic import BaseModel, ConfigDict, Field

class SchedulingProcessMetricsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    avg_turnaround_time: float = Field(alias="avg_tat")
    avg_waiting_time: float = Field(alias="avg_wt")
    avg_response_time: float = Field(alias="avg_rt")