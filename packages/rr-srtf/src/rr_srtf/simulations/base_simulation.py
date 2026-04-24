from abc import ABC, abstractmethod
from logging import Logger
from typing import List

from rr_srtf.enums.scheduling_timeline_event import SchedulingTimelineEvent
from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling.scheduling_result_schema import SchedulingResultSchema
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
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

    @staticmethod
    def _get_log_part(
        event: SchedulingTimelineState | SchedulingTimelineEvent,
        pid: str = "",
        detail: str = ""
    ) -> str:
        event_pid: str = f"{event.value:<8}   [{pid}]" if pid != "" else f"{event.value}"
        return f"{f"{event_pid:<16}  {"" if detail == "" else f'{detail}'}":<45}"

    @staticmethod
    def _flush_log_header(logger: Logger, message: str, processes: List[SchedulingWorkloadProcessSchema]) -> None:
        logger.info("=" * 60)
        logger.info(message)
        logger.info(f"Processes: {[(p.pid, p.arrival_time, p.burst_time) for p in processes]}")
        logger.info("=" * 60)

    @staticmethod
    def _flush_log_parts(logger: Logger, parts: List[str]) -> None:
        logger.debug(" | ".join(parts))
