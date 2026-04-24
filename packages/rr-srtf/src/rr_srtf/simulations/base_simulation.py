from abc import ABC, abstractmethod
from typing import List, Callable

from rr_srtf.enums.scheduling_timeline_event import SchedulingTimelineEvent
from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling.scheduling_result_schema import SchedulingResultSchema
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema
from rr_srtf.utils.logging_utils import LoggingUtils


class BaseSimulation(ABC):
    @classmethod
    @abstractmethod
    def simulate(cls, scheduling: SchedulingSchema) -> List[SchedulingResultSchema]:
        pass

    @classmethod
    def _enqueue_arrived_processes(
            cls,
            time: int,
            processes: List[SchedulingWorkloadProcessSchema],
            next_arrival: int,
            enqueue_func: Callable[[str], None],
            log_parts: list[str]
    ) -> int:
        while next_arrival < len(processes) and processes[next_arrival].arrival_time == time:
            enqueue_func(processes[next_arrival].pid)
            log_parts.append(LoggingUtils.get_log_part(event=SchedulingTimelineEvent.ARRIVE, pid=processes[next_arrival].pid))
            next_arrival += 1
        return next_arrival

    @staticmethod
    def _append_execution_step(
            steps: List[SchedulingTimelineStepSchema],
            pid: str,
            start: int,
            end: int
    ) -> None:
        if (
                steps
                and steps[-1].state == SchedulingTimelineState.RUNNING
                and steps[-1].pid == pid
                and steps[-1].end == start
        ):
            steps[-1] = SchedulingTimelineStepSchema(
                state=SchedulingTimelineState.RUNNING,
                pid=pid,
                start=steps[-1].start,
                end=end
            )

            return

        steps.append(
            SchedulingTimelineStepSchema(
                state=SchedulingTimelineState.RUNNING,
                pid=pid,
                start=start,
                end=end
            )
        )
