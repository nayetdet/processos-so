from pydantic import BaseModel, ConfigDict

class SchedulingProcessMetricsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    avg_turnaround_time: float
    avg_waiting_time: float
    avg_response_time: float
