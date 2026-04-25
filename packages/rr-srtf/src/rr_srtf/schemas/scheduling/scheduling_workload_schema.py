from typing import List, Self
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema

class SchedulingWorkloadSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    time_unit: str = Field(min_length=1)
    processes: List[SchedulingWorkloadProcessSchema] = Field(min_length=1)

    @field_validator("processes", mode="after")
    @classmethod
    def sort_processes(cls, processes: List[SchedulingWorkloadProcessSchema]) -> List[SchedulingWorkloadProcessSchema]:
        return sorted(processes, key=lambda process: (process.arrival_time, process.pid))

    @model_validator(mode="after")
    def validate_unique_pids(self) -> Self:
        pids: List[str] = [process.pid for process in self.processes]
        if len(set(pids)) != len(pids):
            raise ValueError("processes must contain unique pid values")
        return self
