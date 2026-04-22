import heapq
from random import Random
from typing import Dict, List, Optional

from rr_srtf.analysis.scheduling_analysis import SchedulingAnalysis
from rr_srtf.schemas.scheduling.scheduling_result_schema import SchedulingResultSchema
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema
from rr_srtf.simulations.base_simulation import BaseSimulation

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
        context_switch_cost: int = scheduling.metadata.context_switch_cost
        processes: List[SchedulingWorkloadProcessSchema] = scheduling.workload.processes
        steps: List[SchedulingTimelineStepSchema] = []
        remaining_times: Dict[str, int] = {p.pid: p.burst_time for p in processes}
        start_times: Dict[str, int] = {p.pid: -1 for p in processes}
        finish_times: Dict[str, int] = {p.pid: -1 for p in processes}

        rng: Random = Random(cls.SEED)
        time: int = 0
        next_arrival: int = 0
        ready_pids: list[tuple[int, float, str]] = []
        running_pid: Optional[str] = None
        last_pid: Optional[str] = None
        ctx_switch_count: int = 0

        while ready_pids or running_pid is not None or next_arrival < len(processes):
            next_arrival = cls.__enqueue_arrived_processes(
                time=time,
                processes=processes,
                ready_pids=ready_pids,
                remaining_times=remaining_times,
                next_arrival=next_arrival,
                rng=rng
            )

            if running_pid is not None and cls.__should_preempt(
                running_pid=running_pid,
                ready_pids=ready_pids,
                remaining_times=remaining_times
            ):
                heapq.heappush(ready_pids, (remaining_times[running_pid], rng.random(), running_pid))
                last_pid = running_pid
                running_pid = None

            if running_pid is None:
                if not ready_pids:
                    time = processes[next_arrival].arrival_time
                    last_pid = None
                    continue

                if last_pid is not None and last_pid != ready_pids[0][2]:
                    if context_switch_cost > 0:
                        time += context_switch_cost
                        ctx_switch_count += 1
                        last_pid = None
                        continue
                    last_pid = None

                running_pid = cls.__select_next_pid(ready_pids=ready_pids)
                if start_times[running_pid] == -1:
                    start_times[running_pid] = time

            cls._append_execution_step(
                steps=steps,
                pid=running_pid,
                start=time,
                end=time + 1
            )

            remaining_times[running_pid] -= 1
            time += 1

            if remaining_times[running_pid] == 0:
                finish_times[running_pid] = time
                last_pid = running_pid
                running_pid = None

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
    def __enqueue_arrived_processes(
        time: int,
        processes: List[SchedulingWorkloadProcessSchema],
        ready_pids: list[tuple[int, float, str]],
        remaining_times: Dict[str, int],
        next_arrival: int,
        rng: Random
    ) -> int:
        while next_arrival < len(processes) and processes[next_arrival].arrival_time <= time:
            pid: str = processes[next_arrival].pid
            heapq.heappush(ready_pids, (remaining_times[pid], rng.random(), pid))
            next_arrival += 1
        return next_arrival

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

