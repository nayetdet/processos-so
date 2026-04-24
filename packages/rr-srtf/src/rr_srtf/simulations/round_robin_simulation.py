from collections import deque
from logging import Logger
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

class RoundRobinSimulation(BaseSimulation):
    @classmethod
    def simulate(cls, scheduling: SchedulingSchema) -> List[SchedulingResultSchema]:
        if "RR" not in scheduling.metadata.algorithms:
            raise ValueError("Round Robin must be listed as one of the algorithms to be able to simulate")

        return [
            cls.__simulate_once(
                scheduling=scheduling,
                quantum=quantum
            )
            for quantum in scheduling.metadata.rr_quantums or []
        ]

    @classmethod
    def __simulate_once(cls, scheduling: SchedulingSchema, quantum: int) -> SchedulingResultSchema:
        ctx_switch_cost: int = scheduling.metadata.context_switch_cost
        processes: List[SchedulingWorkloadProcessSchema] = scheduling.workload.processes
        steps: List[SchedulingTimelineStepSchema] = []
        log_parts: list[str]
        remaining_times: Dict[str, int] = {p.pid: p.burst_time for p in processes}
        start_times: Dict[str, int] = {p.pid: -1 for p in processes}
        finish_times: Dict[str, int] = {p.pid: -1 for p in processes}

        time: int = 0
        ready_pids: deque[str] = deque()
        next_arrival: int = 0
        last_pid: Optional[str] = None
        ctx_switch_count: int = 0

        logger: Logger = RunContext.current().get_logger(alg_name="RR", label=f'q{quantum}')
        cls._flush_log_header(
            logger=logger,
            message=f"Round Robin Scheduler  |  {quantum=}  {ctx_switch_cost=})",
            processes=processes
        )

        while ready_pids or next_arrival < len(processes):
            log_parts = [f"[{time:03}]"]
            next_arrival = cls.__enqueue_arrived_processes(
                time=time,
                processes=processes,
                ready_pids=ready_pids,
                next_arrival=next_arrival,
                log_parts=log_parts
            )

            if not ready_pids:
                for _ in range(processes[next_arrival].arrival_time-time):
                    log_parts.append(cls._get_log_part(
                        event=SchedulingTimelineState.IDLE
                    ))
                    cls._flush_log_parts(logger=logger, parts=log_parts)
                    time += 1
                    log_parts = [f"[{time:03}]"]
                last_pid = None
                continue

            running_pid: str = ready_pids.popleft()
            if last_pid is not None and last_pid != running_pid:
                for i in range(ctx_switch_cost):
                    next_arrival = cls.__enqueue_arrived_processes(
                        time=time,
                        ready_pids=ready_pids,
                        processes=processes,
                        next_arrival=next_arrival,
                        log_parts=log_parts
                    )
                    log_parts.append(cls._get_log_part(
                        event=SchedulingTimelineState.SWITCHING,
                        detail=f"{f'(t={ctx_switch_cost - i} → {ctx_switch_cost - i - 1})':<13}"
                    ))
                    cls._flush_log_parts(logger=logger, parts=log_parts)
                    time += 1
                    log_parts = [f"[{time:03}]"]
                ctx_switch_count += 1

            if last_pid != running_pid:
                log_parts.append(cls._get_log_part(
                    event=SchedulingTimelineEvent.DISPATCH,
                    pid=running_pid,
                ))
                if start_times[running_pid] == -1:
                    start_times[running_pid] = time

            runtime: int = min(quantum, remaining_times[running_pid])
            cls._append_execution_step(
                steps=steps,
                pid=running_pid,
                start=time,
                end=time + runtime
            )

            for i in range(runtime):
                next_arrival = cls.__enqueue_arrived_processes(
                    time=time,
                    ready_pids=ready_pids,
                    processes=processes,
                    next_arrival=next_arrival,
                    log_parts=log_parts
                )
                log_parts.append(cls._get_log_part(
                    event=SchedulingTimelineState.RUNNING,
                    pid=running_pid,
                    detail=(
                        f"{f'(q={quantum - i} → {quantum - i - 1})':<13} "
                        f"{f'(r={remaining_times[running_pid]} → {remaining_times[running_pid] - 1})':<13}"
                    )
                ))
                remaining_times[running_pid] -= 1
                time += 1
                if i != runtime-1:
                    cls._flush_log_parts(logger=logger, parts=log_parts)
                    log_parts = [f"[{time:03}]"]
            last_pid = running_pid

            if remaining_times[running_pid] > 0:
                log_parts.append(cls._get_log_part(
                    event=SchedulingTimelineEvent.PREEMPT,
                    pid=running_pid,
                    detail=f"(r={remaining_times[running_pid]})"
                ))
                ready_pids.append(running_pid)
            else:
                log_parts.append(cls._get_log_part(
                    event=SchedulingTimelineEvent.FINISH,
                    pid=running_pid
                ))
                finish_times[running_pid] = time

            cls._flush_log_parts(logger=logger, parts=log_parts)

        logger.debug("")

        return SchedulingResultSchema(
            timeline=SchedulingTimelineSchema(
                algorithm="RR",
                quantum=quantum,
                steps=steps
            ),
            metrics=SchedulingAnalysis.get_scheduling_metrics(
                scheduling=scheduling,
                start_times=start_times,
                finish_times=finish_times,
                total_time=time,
                ctx_switch_count=ctx_switch_count
            )
        )

    @classmethod
    def __enqueue_arrived_processes(
        cls,
        time: int,
        processes: List[SchedulingWorkloadProcessSchema],
        ready_pids: deque[str],
        next_arrival: int,
        log_parts: list[str]
    ) -> int:
        while next_arrival < len(processes) and processes[next_arrival].arrival_time <= time:
            ready_pids.append(processes[next_arrival].pid)
            log_parts.append(cls._get_log_part(
                event=SchedulingTimelineEvent.ARRIVE,
                pid=processes[next_arrival].pid
            ))
            next_arrival += 1
        return next_arrival
