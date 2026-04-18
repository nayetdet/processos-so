from pydantic import BaseModel, ConfigDict, Field

class SchedulingSystemMetricsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total_time: int
    busy_time: float = Field(alias="busy")
    utilization: float = Field(alias="util")
    throughput_at_window: int = Field(alias="thr_at_window")
    throughput_overall: float = Field(alias="thr_overall")

