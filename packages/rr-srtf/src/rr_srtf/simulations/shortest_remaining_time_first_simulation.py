from random import Random
from typing import Dict, List, Optional, Set
from rr_srtf.enums.scheduling_timeline_step_state import SchedulingTimelineStepState
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema
from rr_srtf.simulations.base_simulation import BaseSimulation

class ShortestRemainingTimeFirstSimulation(BaseSimulation):
    SEED: int = 0

    @classmethod
    def simulate(cls, scheduling: SchedulingSchema) -> List[SchedulingTimelineSchema]:
        if "SRTF" not in scheduling.metadata.algorithms:
            raise ValueError("Shortest Remaining Time First must be listed as one of the algorithms to be able to simulate")

        return [
            cls.__simulate_once(
                context_switch_cost=scheduling.metadata.context_switch_cost,
                processes=scheduling.workload.processes
            )
        ]

    @classmethod
    def __simulate_once(cls, context_switch_cost: int, processes: List[SchedulingWorkloadProcessSchema]) -> SchedulingTimelineSchema:
        steps: List[SchedulingTimelineStepSchema] = []
        remaining_times: Dict[str, int] = {process.pid: process.burst_time for process in processes}

        rng: Random = Random(cls.SEED)
        time: int = 0
        process_index: int = 0
        ready_pids: Set[str] = set()
        running_pid: Optional[str] = None
        last_pid: Optional[str] = None

        while ready_pids or running_pid is not None or process_index < len(processes):
            process_index = cls.__enqueue_arrived_processes(
                time=time,
                processes=processes,
                ready_pids=ready_pids,
                process_index=process_index
            )

            if running_pid is not None and cls.__should_preempt(
                running_pid=running_pid,
                ready_pids=ready_pids,
                remaining_times=remaining_times
            ):
                ready_pids.add(running_pid)
                last_pid = running_pid
                running_pid = None

            if running_pid is None:
                if not ready_pids:
                    time = processes[process_index].arrival_time
                    last_pid = None
                    continue

                next_pid: str = cls.__select_next_pid(
                    ready_pids=ready_pids,
                    remaining_times=remaining_times,
                    rng=rng
                )

                if last_pid is not None and last_pid != next_pid:
                    if context_switch_cost > 0:
                        time += context_switch_cost
                        last_pid = None
                        continue
                    last_pid = None

                ready_pids.remove(next_pid)
                running_pid = next_pid

            cls.__append_execution_step(
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
        ready_pids: Set[str],
        process_index: int
    ) -> int:
        while process_index < len(processes) and processes[process_index].arrival_time <= time:
            ready_pids.add(processes[process_index].pid)
            process_index += 1
        return process_index

    @staticmethod
    def __should_preempt(
        running_pid: str,
        ready_pids: Set[str],
        remaining_times: Dict[str, int]
    ) -> bool:
        running_remaining_time: int = remaining_times[running_pid]
        return any(
            remaining_times[pid] < running_remaining_time
            for pid in ready_pids
        )

    @staticmethod
    def __select_next_pid(
        ready_pids: Set[str],
        remaining_times: Dict[str, int],
        rng: Random
    ) -> str:
        shortest_remaining_time: int = min(remaining_times[pid] for pid in ready_pids)
        candidates: List[str] = sorted(
            pid
            for pid in ready_pids
            if remaining_times[pid] == shortest_remaining_time
        )

        return rng.choice(candidates)

    @staticmethod
    def __append_execution_step(
        steps: List[SchedulingTimelineStepSchema],
        pid: str,
        start: int,
        end: int
    ) -> None:
        if (
            steps
            and steps[-1].state == SchedulingTimelineStepState.RUNNING
            and steps[-1].pid == pid
            and steps[-1].end == start
        ):
            steps[-1] = SchedulingTimelineStepSchema(
                state=SchedulingTimelineStepState.RUNNING,
                pid=pid,
                start=steps[-1].start,
                end=end
            )

            return

        steps.append(
            SchedulingTimelineStepSchema(
                state=SchedulingTimelineStepState.RUNNING,
                pid=pid,
                start=start,
                end=end
            )
        )
