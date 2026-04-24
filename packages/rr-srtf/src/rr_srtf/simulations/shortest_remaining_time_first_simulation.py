import heapq
from logging import Logger
from random import Random
from typing import Dict, List, Optional

from rr_srtf.analysis.scheduling_analysis import SchedulingAnalysis
from rr_srtf.context import RunContext
from rr_srtf.enums.scheduling_timeline_event import SchedulingTimelineEvent
from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling.scheduling_result_schema import SchedulingResultSchema
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema
from rr_srtf.simulations.base_simulation import BaseSimulation
from rr_srtf.utils.logging_utils import LoggingUtils

class ShortestRemainingTimeFirstSimulation(BaseSimulation):
    SEED: int = 0

    @classmethod
    def simulate(cls, scheduling: SchedulingSchema) -> List[SchedulingResultSchema]:
        if "SRTF" not in scheduling.metadata.algorithms:
            raise ValueError("Shortest Remaining Time First must be listed as one of the algorithms to be able to simulate")

        return [
            cls.__simulate_once(scheduling=scheduling)
        ]

    @classmethod
    def __simulate_once(cls, scheduling: SchedulingSchema) -> SchedulingResultSchema:
        ctx_switch_cost: int = scheduling.metadata.context_switch_cost
        processes: List[SchedulingWorkloadProcessSchema] = scheduling.workload.processes
        steps: List[SchedulingTimelineStepSchema] = []
        log_parts: list[str]

        remaining_times: Dict[str, int] = {p.pid: p.burst_time for p in processes}
        start_times: Dict[str, int] = {p.pid: -1 for p in processes}
        finish_times: Dict[str, int] = {p.pid: -1 for p in processes}

        time: int = 0
        next_arrival: int = 0

        running_pid: Optional[str] = None
        last_pid: Optional[str] = None
        ctx_switch_count: int = 0
        switch_remaining: int = 0
        ready_pids: list[tuple[int, float, str]] = []
        rng: Random = Random(cls.SEED)

        logger: Logger = RunContext.current().get_logger(alg_name="SRTF")
        LoggingUtils.flush_log_header(
            logger=logger,
            message=f"Shortest Remaining Time First Scheduler  |  {ctx_switch_cost=})",
            processes=processes
        )

        def enqueue(pid: str) -> None:
            heapq.heappush(ready_pids, (remaining_times[pid], rng.random(), pid))

        while ready_pids or running_pid is not None or next_arrival < len(processes):
            log_parts = [f"[{time:03}]"]
            next_arrival = cls._enqueue_arrived_processes(
                time=time,
                processes=processes,
                next_arrival=next_arrival,
                enqueue_func=enqueue,
                log_parts=log_parts,
            )

            if switch_remaining > 0:
                log_parts.append(LoggingUtils.get_log_part(
                    event=SchedulingTimelineState.SWITCHING,
                    detail=f"{f'(t={switch_remaining} → {switch_remaining - 1})':<13}"
                ))
                switch_remaining -= 1
                time += 1
                LoggingUtils.flush_log_parts(logger=logger, parts=log_parts)
                continue

            if running_pid is not None and cls.__should_preempt(
                running_pid=running_pid,
                ready_pids=ready_pids,
                remaining_times=remaining_times
            ):
                log_parts.append(LoggingUtils.get_log_part(
                    event=SchedulingTimelineEvent.PREEMPT,
                    pid=running_pid,
                    detail=f"(r={remaining_times[running_pid]})"
                ))
                enqueue(running_pid)
                last_pid = running_pid
                running_pid = None

            if running_pid is None:
                if not ready_pids:
                    log_parts.append(LoggingUtils.get_log_part(event=SchedulingTimelineState.IDLE))
                    time += 1
                    last_pid = None
                    LoggingUtils.flush_log_parts(logger=logger, parts=log_parts)
                    continue

                if last_pid is not None and last_pid != ready_pids[0][2]:
                    if ctx_switch_cost > 0:
                        switch_remaining = ctx_switch_cost
                        ctx_switch_count += 1
                        last_pid = None
                        continue
                    last_pid = None

                running_pid = cls.__select_next_pid(ready_pids=ready_pids)
                if last_pid != running_pid:
                    if start_times[running_pid] == -1:
                        start_times[running_pid] = time
                    log_parts.append(LoggingUtils.get_log_part(event=SchedulingTimelineEvent.DISPATCH, pid=running_pid))

            cls._append_execution_step(
                steps=steps,
                pid=running_pid,
                start=time,
                end=time + 1
            )

            log_parts.append(LoggingUtils.get_log_part(
                event=SchedulingTimelineState.RUNNING,
                pid=running_pid,
                detail=f"{f'(r={remaining_times[running_pid]} → {remaining_times[running_pid] - 1})':<13}"
            ))

            remaining_times[running_pid] -= 1
            time += 1

            if remaining_times[running_pid] == 0:
                log_parts.append(LoggingUtils.get_log_part(event=SchedulingTimelineEvent.FINISH, pid=running_pid))
                finish_times[running_pid] = time
                last_pid = running_pid
                running_pid = None

            LoggingUtils.flush_log_parts(logger=logger, parts=log_parts)

        logger.debug("")

        return SchedulingResultSchema(
            timeline=SchedulingTimelineSchema(
                algorithm="SRTF",
                steps=steps
            ),
            metrics=SchedulingAnalysis.get_scheduling_metrics(
                scheduling=scheduling,
                start_times=start_times,
                finish_times=finish_times,
                total_time=time,
                ctx_switch_count=ctx_switch_count
            ),
        )

    @staticmethod
    def __should_preempt(
        running_pid: str,
        ready_pids: list[tuple[int, float, str]],
        remaining_times: Dict[str, int]
    ) -> bool:
        if not ready_pids:
            return False
        return ready_pids[0][0] < remaining_times[running_pid]

    @staticmethod
    def __select_next_pid(
        ready_pids: list[tuple[int, float, str]],
    ) -> str:
        *_, next_pid = heapq.heappop(ready_pids)
        return next_pid

