from collections import deque
from typing import Dict, List, Optional
from rr_srtf.enums.scheduling_timeline_step_state import SchedulingTimelineStepState
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema
from rr_srtf.simulations.base_simulation import BaseSimulation

class RoundRobinSimulation(BaseSimulation):
    @classmethod
    def simulate(cls, scheduling: SchedulingSchema) -> List[SchedulingTimelineSchema]:
        if "RR" not in scheduling.metadata.algorithms:
            raise ValueError("Round Robin must be listed as one of the algorithms to be able to simulate")

        timelines: List[SchedulingTimelineSchema] = []
        for quantum in scheduling.metadata.rr_quantums or []:
            timelines.append(
                cls.__simulate_once(
                    quantum=quantum,
                    context_switch_cost=scheduling.metadata.context_switch_cost,
                    processes=scheduling.workload.processes
                )
            )

        return timelines

    @classmethod
    def __simulate_once(
        cls,
        quantum: int,
        context_switch_cost: int,
        processes: List[SchedulingWorkloadProcessSchema]
    ) -> SchedulingTimelineSchema:
        steps: List[SchedulingTimelineStepSchema] = []
        remaining_times: Dict[str, int] = {process.pid: process.burst_time for process in processes}

        time: int = 0
        processes_queue: deque[SchedulingWorkloadProcessSchema] = deque()
        process_index: int = 0
        last_pid: Optional[str] = None

        while processes_queue or process_index < len(processes):
            process_index = cls.__enqueue_arrived_processes(
                time=time,
                processes=processes,
                processes_queue=processes_queue,
                process_index=process_index
            )

            if not processes_queue:
                time = processes[process_index].arrival_time
                last_pid = None
                continue

            process: SchedulingWorkloadProcessSchema = processes_queue.popleft()
            if last_pid is not None and last_pid != process.pid:
                time += context_switch_cost
                process_index = cls.__enqueue_arrived_processes(
                    time=time,
                    processes_queue=processes_queue,
                    processes=processes,
                    process_index=process_index
                )

            runtime: int = min(quantum, remaining_times[process.pid])
            cls.__append_execution_step(
                steps=steps,
                pid=process.pid,
                start=time,
                end=time + runtime
            )

            time += runtime
            remaining_times[process.pid] -= runtime
            last_pid = process.pid

            process_index = cls.__enqueue_arrived_processes(
                time=time,
                processes_queue=processes_queue,
                processes=processes,
                process_index=process_index
            )

            if remaining_times[process.pid] > 0:
                processes_queue.append(process)

        return SchedulingTimelineSchema(
            algorithm="RR",
            quantum=quantum,
            steps=steps
        )

    @staticmethod
    def __enqueue_arrived_processes(
        time: int,
        processes: List[SchedulingWorkloadProcessSchema],
        processes_queue: deque[SchedulingWorkloadProcessSchema],
        process_index: int
    ) -> int:
        while process_index < len(processes) and processes[process_index].arrival_time <= time:
            processes_queue.append(processes[process_index])
            process_index += 1
        return process_index

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
