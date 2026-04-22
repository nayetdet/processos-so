from collections import deque
from typing import Dict, List, Optional

from rr_srtf.analysis.scheduling_analysis import SchedulingAnalysis
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
        context_switch_cost: int = scheduling.metadata.context_switch_cost
        processes: List[SchedulingWorkloadProcessSchema] = scheduling.workload.processes
        steps: List[SchedulingTimelineStepSchema] = []
        remaining_times: Dict[str, int] = {p.pid: p.burst_time for p in processes}
        start_times: Dict[str, int] = {p.pid: -1 for p in processes}
        finish_times: Dict[str, int] = {p.pid: -1 for p in processes}

        time: int = 0
        ready_pids: deque[str] = deque()
        next_arrival: int = 0
        last_pid: Optional[str] = None
        ctx_switch_count: int = 0

        while ready_pids or next_arrival < len(processes):
            next_arrival = cls.__enqueue_arrived_processes(
                time=time,
                processes=processes,
                ready_pids=ready_pids,
                next_arrival=next_arrival
            )

            if not ready_pids:
                time = processes[next_arrival].arrival_time
                last_pid = None
                continue

            running_pid: str = ready_pids.popleft()
            if last_pid is not None and last_pid != running_pid:
                time += context_switch_cost
                ctx_switch_count += 1
                next_arrival = cls.__enqueue_arrived_processes(
                    time=time,
                    ready_pids=ready_pids,
                    processes=processes,
                    next_arrival=next_arrival
                )

            runtime: int = min(quantum, remaining_times[running_pid])
            cls._append_execution_step(
                steps=steps,
                pid=running_pid,
                start=time,
                end=time + runtime
            )

            if start_times[running_pid] == -1:
                start_times[running_pid] = time

            time += runtime
            remaining_times[running_pid] -= runtime
            last_pid = running_pid

            next_arrival = cls.__enqueue_arrived_processes(
                time=time,
                ready_pids=ready_pids,
                processes=processes,
                next_arrival=next_arrival
            )

            if remaining_times[running_pid] > 0:
                ready_pids.append(running_pid)
            else:
                finish_times[running_pid] = time

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

    @staticmethod
    def __enqueue_arrived_processes(
        time: int,
        processes: List[SchedulingWorkloadProcessSchema],
        ready_pids: deque[str],
        next_arrival: int
    ) -> int:
        while next_arrival < len(processes) and processes[next_arrival].arrival_time <= time:
            ready_pids.append(processes[next_arrival].pid)
            next_arrival += 1
        return next_arrival
