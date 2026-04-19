import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Literal

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
    instant_start: bool = True
    ctx_switch_on_finish: bool = True
    sched_decision_cost: int = 0

    # Timeline/Logging
    entry_timeline: list[SchedulingTimelineEntrySchema] = field(default_factory=list, init=False)
    log_parts: list[str] = field(default_factory=list, init=False)

    # Process Management
    nb_processes: int = field(default=0, init=False)
    next_arrival: int = field(default=0, init=False)
    current: Optional[RuntimeProcess] = field(default=None, init=False)
    last_pid: Optional[str] = field(default=None, init=False)
    completed: list[RuntimeProcess] = field(default_factory=list, init=False)

    # Tick Event/State Management
    clock: int = field(default=0, init=False)
    inner_clock: int = field(default=0, init=False)
    ongoing_event: SchedulingTimelineEntryType = field(default=SchedulingTimelineState.IDLE, init=False)

    # Metrics
    scheduler_overhead: int = field(default=0, init=False)

    _finished: bool = field(default=False, init=False) # freeze flag

    def __post_init__(self):
        self.nb_processes = len(self.processes)

    @property
    def finished(self) -> bool:
        return self._finished

    def finish(self):
        object.__setattr__(self, '_finished', True)

    def __setattr__(self, name, value):
        if self._finished:
            raise AttributeError(f"Simulation has already finished, cannot set '{name}'.")
        super().__setattr__(name, value)

    def add_timeline_entry(self, entry: SchedulingTimelineEntrySchema):
        self.entry_timeline.append(entry)
        self.log_parts.append(entry.no_time_str())

    def flush_log_header(self, message: str):
        self.logger.info("=" * 60)
        self.logger.info(message)
        self.logger.info(f"Processes: {[(p.pid, p.arrival_time, p.burst_time) for p in self.processes]}")
        self.logger.info("=" * 60)

    def begin_tick(self) -> None:
        self.log_parts = [f"[{self.clock:03}]"]

    def flush_tick(self) -> None:
        self.logger.debug(" | ".join(self.log_parts))

    def tick_clock(self):
        self.clock += 1
