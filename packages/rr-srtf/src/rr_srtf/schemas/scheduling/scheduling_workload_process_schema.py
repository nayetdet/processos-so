from pydantic import BaseModel, ConfigDict, Field

class SchedulingWorkloadProcessSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pid: str = Field(min_length=1)
    arrival_time: int = Field(ge=0)
    burst_time: int = Field(gt=0)
