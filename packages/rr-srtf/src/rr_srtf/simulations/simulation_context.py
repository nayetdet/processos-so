import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_entry_schema import (
    SchedulingTimelineEntrySchema,
    SchedulingTimelineEntryType)
from rr_srtf.simulations.runtime_process import RuntimeProcess


@dataclass
class SimulationContext:
    processes: list[SchedulingWorkloadProcessSchema]
    ctx_switch_cost: int
    throughput_window: int
    logger: logging.Logger
    quantum: Optional[int] = None
    ctx_switch_on_finish: bool = True
    sched_decision_cost: int = 0
    instant_start: bool = True

    entry_timeline: list[SchedulingTimelineEntrySchema] = field(default_factory=list, init=False)
    log_parts: list[str] = field(default_factory=list, init=False)

    next_arrival: int = field(default=0, init=False)
    ready_queue: deque[RuntimeProcess] = field(default_factory=deque, init=False)
    completed: list[RuntimeProcess] = field(default_factory=list, init=False)

    clock: int = field(default=0, init=False)
    inner_clock: int = field(default=0, init=False)
    ongoing_event: SchedulingTimelineEntryType = field(default=SchedulingTimelineState.IDLE, init=False)
    current: Optional[RuntimeProcess] = field(default=None, init=False)
    last_pid: Optional[str] = field(default=None, init=False)
    scheduler_overhead: int = field(default=0, init=False)  # amount of ticks the scheduler was in the cpu

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

    def add_event(self, event: SchedulingTimelineEntrySchema):
        self.entry_timeline.append(event)
        self.log_parts.append(event.no_time_str())

    def begin_tick(self) -> None:
        self.log_parts = [f"[{self.clock:03}]"]

    def flush_tick(self) -> None:
        self.logger.debug(" | ".join(self.log_parts))

    def tick_clock(self):
        self.clock += 1
