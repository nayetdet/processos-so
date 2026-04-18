from typing import List, Self
from pydantic import BaseModel, ConfigDict, Field, model_validator
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema

class SchedulingWorkloadSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    time_unit: str = Field(min_length=1)
    processes: List[SchedulingWorkloadProcessSchema] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_pids(self) -> Self:
        pids: List[str] = [process.pid for process in self.processes]
        if len(set(pids)) != len(pids):
            raise ValueError("processes must contain unique pid values")
        return self
