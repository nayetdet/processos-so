import heapq
from random import Random
from typing import Dict, List, Optional

from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema
from rr_srtf.simulations.base_simulation import BaseSimulation
from rr_srtf.simulations.simulation_context import SimulationContext


class ShortestRemainingTimeFirstSimulation(BaseSimulation):
    SEED: int = 0

    @classmethod
    def simulate(cls, scheduling: SchedulingSchema) -> List[SchedulingResultSchema]:
        if "SRTF" not in scheduling.metadata.algorithms:
            raise ValueError("Shortest Remaining Time First must be listed as one of the algorithms to be able to simulate")

        context: SimulationContext = SimulationContext(
            processes=scheduling.workload.processes,
            ctx_switch_cost=scheduling.metadata.context_switch_cost,
            throughput_window=scheduling.metadata.throughput_window_T,
            logger=RunContext.current().get_logger("SRTF")
        )

        timeline: SchedulingTimelineSchema = cls.__simulate_once(
            context_switch_cost=scheduling.metadata.context_switch_cost,
            processes=scheduling.workload.processes
        )

        metrics: SchedulingMetricsSchema = SchedulingAnalysis.get_scheduling_timelines_metrics(scheduling, [timeline])[0]

        return [SchedulingResultSchema(final_context=context, timeline=timeline, metrics=metrics)]

    @classmethod
    def __simulate_once(cls, context_switch_cost: int, processes: List[SchedulingWorkloadProcessSchema]) -> SchedulingTimelineSchema:
        steps: List[SchedulingTimelineStepSchema] = []
        remaining_times: Dict[str, int] = {process.pid: process.burst_time for process in processes}

        rng: Random = Random(cls.SEED)
        time: int = 0
        process_index: int = 0
        ready_pids: list[tuple[int, float, str]] = []
        running_pid: Optional[str] = None
        last_pid: Optional[str] = None

        while ready_pids or running_pid is not None or process_index < len(processes):
            process_index = cls.__enqueue_arrived_processes(
                time=time,
                processes=processes,
                ready_pids=ready_pids,
                remaining_times=remaining_times,
                process_index=process_index,
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
                    time = processes[process_index].arrival_time
                    last_pid = None
                    continue

                next_pid: str = cls.__select_next_pid(ready_pids=ready_pids)

                if last_pid is not None and last_pid != next_pid:
                    if context_switch_cost > 0:
                        time += context_switch_cost
                        running_pid = next_pid
                        last_pid = None
                        continue
                    last_pid = None

                running_pid = next_pid

            cls._append_execution_step(
                steps=steps,
                pid=running_pid,
                start=time,
                end=time + 1
            )

            remaining_times[running_pid] -= 1
            time += 1

            if remaining_times[running_pid] == 0:
                last_pid = running_pid
                running_pid = None

        return SchedulingTimelineSchema(
            algorithm="SRTF",
            steps=steps
        )

    @staticmethod
    def __enqueue_arrived_processes(
        time: int,
        processes: List[SchedulingWorkloadProcessSchema],
        ready_pids: list[tuple[int, float, str]],
        remaining_times: Dict[str, int],
        process_index: int,
        rng: Random
    ) -> int:
        while process_index < len(processes) and processes[process_index].arrival_time <= time:
            pid: str = processes[process_index].pid
            heapq.heappush(ready_pids, (remaining_times[pid], rng.random(), pid))
            process_index += 1
        return process_index

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

    @staticmethod
    def __append_execution_step(
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
