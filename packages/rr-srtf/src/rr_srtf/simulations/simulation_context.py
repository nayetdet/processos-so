from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from rr_srtf.models.process_model import ProcessModel
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_event_schema import SchedulingEventSchema


@dataclass
class SimulationContext:
    processes: list[SchedulingWorkloadProcessSchema]
    quantum: int
    ctx_switch_cost: int
    throughput_window: int
    cost_on_finish: bool = False

    timeline: list[SchedulingEventSchema] = field(default_factory=list)
    message_parts: list[str] = field(default_factory=list)

    next_arrival: int = 0
    ready_queue: deque[ProcessModel] = field(default_factory=deque)
    completed: list[ProcessModel] = field(default_factory=list)

    clock: int = 0
    inner_clock: int = 0
    last_pid: Optional[str] = None
    current: Optional[ProcessModel] = None
    tick_done: bool = False
    switching: bool = False
    just_dispatched: bool = False
    just_completed: bool = False
    sched_oh: int = 0  # amount of ticks the scheduler was in the cpu

    def add_event(self, event: SchedulingEventSchema):
        self.timeline.append(event)
        self.message_parts.append(event.no_time_str())

    def begin_tick(self) -> None:
        self.message_parts = [f"[{self.clock:03}]"]

    def flush_tick(self) -> None:
        print(" | ".join(self.message_parts))
        self.clock += 1
