from dataclasses import dataclass, field
from typing import Any, Self

from pydantic import BaseModel, Field

from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema


class RuntimeProcess(BaseModel):
    schema: SchedulingWorkloadProcessSchema
    remaining_time: int = Field(default=-1,init=False)

    start_time: int = Field(default=-1, init=False)
    finish_time: int = Field(default=-1, init=False)
    waiting_time: int = Field(default=-1, init=False)
    turnaround_time: int = Field(default=-1, init=False)
    response_time: int = Field(default=-1, init=False)

    @property
    def pid(self) -> str:
        return self.schema.pid

    @property
    def arrival_time(self) -> int:
        return self.schema.arrival_time

    @property
    def burst_time(self) -> int:
        return self.schema.burst_time

    @property
    def is_completed(self) -> bool:
        return self.finish_time != -1

    @property
    def has_responded(self) -> bool:
        return self.response_time != -1

    def model_post_init(self, context: Any) -> None:
        self.remaining_time = self.schema.burst_time

    def mark_completed(self, clock: int) -> None:
        self.finish_time = clock
        self.turnaround_time = clock - self.arrival_time
        self.waiting_time = (clock - self.arrival_time) - self.burst_time
