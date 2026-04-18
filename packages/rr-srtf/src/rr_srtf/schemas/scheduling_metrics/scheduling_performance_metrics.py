from pydantic import BaseModel, ConfigDict

class SchedulingPerformanceMetricsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total_time: int
    busy_time: float
    utilization: float
    throughput_at_window: float
    throughput_overall: float
