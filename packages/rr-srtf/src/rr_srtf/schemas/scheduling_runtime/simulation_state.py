from typing import Optional

from pydantic import BaseModel, PrivateAttr, Field, ConfigDict

from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling_runtime.runtime_process import RuntimeProcess
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_entry_schema import SchedulingTimelineEntryType


class SimulationState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    next_arrival: int = 0
    current: Optional[RuntimeProcess] = None
    last_pid: Optional[str] = None
    completed: list[RuntimeProcess] = Field(default_factory=list)
    clock: int = 0
    inner_clock: int = 0
    ongoing_event: SchedulingTimelineEntryType = SchedulingTimelineState.IDLE

    _finished: bool = PrivateAttr(default=False)

    @property
    def finished(self) -> bool:
        return self._finished

    def finish(self) -> None:
        self._finished = True

    def tick_clock(self) -> None:
        if self._finished:
            raise RuntimeError("Cannot tick a finished simulation.")
        self.clock += 1