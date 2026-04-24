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
from rr_srtf.utils.logging_utils import LoggingUtils

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

        remaining_times: Dict[str, int] = {p.pid: p.burst_time for p in processes}
        start_times: Dict[str, int] = {p.pid: -1 for p in processes}
        finish_times: Dict[str, int] = {p.pid: -1 for p in processes}

        time: int = 0
        next_arrival: int = 0
        running_pid: Optional[str] = None
        last_pid: Optional[str] = None
        ctx_switch_count: int = 0
        switch_remaining: int = 0
        ready_pids: deque[str] = deque()
        q_remaining: int = 0

        logger: Logger = RunContext.current().get_logger(alg_name="RR", label=f'q{quantum}')
        LoggingUtils.flush_log_header(
            logger=logger,
            message=f"Round Robin Scheduler  |  {quantum=}  {ctx_switch_cost=})",
            processes=processes
        )

        def enqueue(pid: str):
            ready_pids.append(pid)

        while ready_pids or running_pid is not None or next_arrival < len(processes):
            with cls._tick(time=time, logger=logger) as tick:
                next_arrival = cls._enqueue_arrived_processes(
                    time=time,
                    processes=processes,
                    next_arrival=next_arrival,
                    enqueue_func=enqueue,
                    tick=tick
                )

                if switch_remaining > 0:
                    tick.log(
                        event=SchedulingTimelineState.SWITCHING,
                        detail=f"{f'(t={switch_remaining} → {switch_remaining - 1})':<13}"
                    )
                    switch_remaining -= 1
                    time += 1
                    continue

                if running_pid is None:
                    if not ready_pids:
                        tick.log(event=SchedulingTimelineState.IDLE)
                        time += 1
                        last_pid = None
                        continue

                    if last_pid is not None and last_pid != ready_pids[0]:
                        if ctx_switch_cost > 0:
                            switch_remaining = ctx_switch_cost - 1
                            ctx_switch_count += 1
                            last_pid = None
                            tick.log(
                                event=SchedulingTimelineState.SWITCHING,
                                detail=f"{f'(t={switch_remaining+1} → {switch_remaining})':<13}"
                            )
                            time += 1
                            continue
                        last_pid = None

                    running_pid = ready_pids.popleft()
                    q_remaining = quantum
                    if last_pid != running_pid:
                        if start_times[running_pid] == -1:
                            start_times[running_pid] = time
                        tick.log(event=SchedulingTimelineEvent.DISPATCH, pid=running_pid)

                cls._append_execution_step(
                    steps=steps,
                    pid=running_pid,
                    start=time,
                    end=time + 1
                )

                tick.log(
                    event=SchedulingTimelineState.RUNNING,
                    pid=running_pid,
                    detail=(
                        f"{f'(q={q_remaining} → {q_remaining - 1})':<13} "
                        f"{f'(r={remaining_times[running_pid]} → {remaining_times[running_pid] - 1})':<13}"
                    )
                )

                remaining_times[running_pid] -= 1
                q_remaining -= 1
                time += 1

                if remaining_times[running_pid] == 0:
                    tick.log(event=SchedulingTimelineEvent.FINISH, pid=running_pid)
                    finish_times[running_pid] = time
                    last_pid = running_pid
                    running_pid = None
                elif q_remaining == 0:
                    tick.log(
                        event=SchedulingTimelineEvent.PREEMPT,
                        pid=running_pid,
                        detail=f"(r={remaining_times[running_pid]})"
                    )
                    enqueue(running_pid)
                    last_pid = running_pid
                    running_pid = None


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
