from dataclasses import dataclass, field

from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema


@dataclass
class RuntimeProcess:
    _schema: SchedulingWorkloadProcessSchema
    remaining_time: int = field(init=False)

    start_time: int = field(default=-1, init=False)
    finish_time: int = field(default=-1, init=False)
    waiting_time: int = field(default=-1, init=False)
    turnaround_time: int = field(default=-1, init=False)
    response_time: int = field(default=-1, init=False)

    @property
    def pid(self) -> str:
        return self._schema.pid

    @property
    def arrival_time(self) -> int:
        return self._schema.arrival_time

    @property
    def burst_time(self) -> int:
        return self._schema.burst_time

    @property
    def is_completed(self) -> bool:
        return self.finish_time != -1

    @property
    def has_responded(self) -> bool:
        return self.response_time != -1

    @classmethod
    def from_schema(cls, schema: SchedulingWorkloadProcessSchema) -> 'RuntimeProcess':
        return cls(_schema=schema)

    def __post_init__(self):
        self.remaining_time = self._schema.burst_time

    def mark_completed(self, clock: int) -> None:
        self.finish_time = clock
        self.turnaround_time = clock - self.arrival_time
        self.waiting_time = (clock - self.arrival_time) - self.burst_time
