from abc import ABC, abstractmethod
from typing import List

from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling.scheduling_result_schema import SchedulingResultSchema
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema


class BaseSimulation(ABC):
    @classmethod
    @abstractmethod
    def simulate(cls, scheduling: SchedulingSchema) -> List[SchedulingResultSchema]:
        pass

    @staticmethod
    def _append_execution_step(
            steps: List[SchedulingTimelineStepSchema],
            pid: str,
            start: int,
            end: int
    ) -> None:
        if (
                steps
                and steps[-1].type == SchedulingTimelineState.RUNNING
                and steps[-1].ctx == pid
                and steps[-1].end == start
        ):
            steps[-1] = SchedulingTimelineStepSchema(
                type=SchedulingTimelineState.RUNNING,
                ctx=pid,
                start=steps[-1].start,
                end=end
            )

            return

        steps.append(
            SchedulingTimelineStepSchema(
                type=SchedulingTimelineState.RUNNING,
                ctx=pid,
                start=start,
                end=end
            )
        )