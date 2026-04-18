from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from rr_srtf.models.process_model import ProcessModel
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_event_schema import SchedulingEventSchema


class SimulationContext(BaseModel):
    model_config = ConfigDict(frozen=False)

    processes: list[SchedulingWorkloadProcessSchema]
    quantum: int
    ctx_switch_cost: int
    throughput_window: int
    cost_on_finish: bool = False

    timeline: list[SchedulingEventSchema] = Field(default=[],init=False)
    message_parts: list[str] = Field(default=[],init=False)

    next_arrival: int = Field(default=0,init=False)
    ready_queue: deque[ProcessModel] = Field(default=deque(),init=False)
    completed: list[ProcessModel] = Field(default=[],init=False)

    clock: int = Field(default=0,init=False)
    inner_clock: int = Field(default=0,init=False)
    current: Optional[ProcessModel] = Field(default=None, init=False)
    last_pid: Optional[str] = Field(default=None,init=False)
    sched_oh: int = Field(default=0, init=False)  # amount of ticks the scheduler was in the cpu

    switching: bool =  Field(default=False,init=False)
    just_dispatched: bool =  Field(default=False,init=False)
    just_completed: bool =  Field(default=False,init=False)

    _finished: bool = False

    @property
    def finished(self) -> bool:
        return self._finished

    def finish(self):
        object.__setattr__(self, '_finished', True)

    def __setattr__(self, name, value):
        if self._finished:
            raise AttributeError(f"Simulation has already finished, cannot set '{name}'.")
        super().__setattr__(name, value)

    def add_event(self, event: SchedulingEventSchema):
        self.timeline.append(event)
        self.message_parts.append(event.no_time_str())

    def begin_tick(self) -> None:
        self.message_parts = [f"[{self.clock:03}]"]

    def flush_tick(self) -> None:
        print(" | ".join(self.message_parts))
        self.clock += 1
