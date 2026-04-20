import logging
from contextlib import contextmanager
from typing import Generator

from rr_srtf.schemas.scheduling_runtime.simulation_config import SimulationConfig
from rr_srtf.schemas.scheduling_runtime.simulation_state import SimulationState
from rr_srtf.schemas.scheduling_runtime.simulation_timeline import SimulationTimeline


class SimulationContext:
    def __init__(self, config: SimulationConfig, logger: logging.Logger) -> None:
        self.config = config
        self.state = SimulationState()
        self.timeline = SimulationTimeline()
        self.logger = logger

    @contextmanager
    def tick(self) -> Generator[None, None, None]:
        self.timeline.begin_tick(self.state.clock)
        try:
            yield
        finally:
            self.logger.debug(self.timeline.flush_parts())
            if not self.state.finished:
                self.state.tick_clock()
            else:
                self.logger.debug("")

    def flush_log_header(self, message: str) -> None:
        self.logger.info("=" * 60)
        self.logger.info(message)
        self.logger.info(f"Processes: {[(p.pid, p.arrival_time, p.burst_time) for p in self.config.processes]}")
        self.logger.info("=" * 60)
