from collections import defaultdict
from itertools import pairwise
from typing import DefaultDict, Dict, List, Optional, Set
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_overhead_metrics import SchedulingOverheadMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_performance_metrics import SchedulingPerformanceMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_process_metrics import SchedulingProcessMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema

class SchedulingAnalysis:
    @classmethod
    def get_scheduling_timelines_metrics(cls, scheduling: SchedulingSchema, scheduling_timelines: List[SchedulingTimelineSchema]) -> List[SchedulingMetricsSchema]:
        if not scheduling_timelines:
            return []

        return [
            cls.get_scheduling_timeline_metrics(
                scheduling,
                timeline,
                cls.__group_steps_by_id(scheduling, timeline)
            )
            for timeline in scheduling_timelines
        ]

    @classmethod
    def get_scheduling_timeline_metrics(
        cls,
        scheduling: SchedulingSchema,
        timeline: SchedulingTimelineSchema,
        steps_by_pid: Dict[str, List[SchedulingTimelineStepSchema]],
    ) -> SchedulingMetricsSchema:
        process_metrics: SchedulingProcessMetricsSchema = cls.__get_process_metrics(scheduling, steps_by_pid)
        process_count: int = len(scheduling.workload.processes)

        total_time: int = timeline.steps[-1].end
        busy_time: int = sum(step.end - step.start for step in timeline.steps)
        completed_at_window: int = sum(
            steps_by_pid[process.pid][-1].end <= scheduling.metadata.throughput_window_T
            for process in scheduling.workload.processes
        )

        return SchedulingMetricsSchema(
            process=process_metrics,
            performance=SchedulingPerformanceMetricsSchema(
                total_time=total_time,
                busy_time=float(busy_time),
                utilization=busy_time / total_time if total_time else 0.0,
                throughput_at_window=completed_at_window / scheduling.metadata.throughput_window_T,
                throughput_overall=process_count / total_time if total_time else 0.0
            ),
            overhead=cls.__get_overhead_metrics(scheduling, timeline)
        )

    @staticmethod
    def __get_process_metrics(scheduling: SchedulingSchema, steps_by_pid: Dict[str, List[SchedulingTimelineStepSchema]]) -> SchedulingProcessMetricsSchema:
        processes: List[SchedulingWorkloadProcessSchema] = scheduling.workload.processes
        total_turnaround_time: int = 0
        total_waiting_time: int = 0
        total_response_time: int = 0

        for process in processes:
            process_steps: Optional[List[SchedulingTimelineStepSchema]] = steps_by_pid.get(process.pid)
            if process_steps is None:
                raise ValueError(f"missing execution for pid: {process.pid}")

            runtime: int = sum(step.end - step.start for step in process_steps)
            if runtime != process.burst_time:
                raise ValueError(f"burst_time mismatch for pid: {process.pid}")

            turnaround_time: int = process_steps[-1].end - process.arrival_time
            total_turnaround_time += turnaround_time
            total_waiting_time += turnaround_time - process.burst_time
            total_response_time += process_steps[0].start - process.arrival_time

        process_count: int = len(processes)
        return SchedulingProcessMetricsSchema(
            avg_turnaround_time=total_turnaround_time / process_count,
            avg_waiting_time=total_waiting_time / process_count,
            avg_response_time=total_response_time / process_count
        )

    @staticmethod
    def __get_overhead_metrics(scheduling: SchedulingSchema, timeline: SchedulingTimelineSchema) -> SchedulingOverheadMetricsSchema:
        ctx_switch_count: int = sum(
            previous_step.pid != current_step.pid
            for previous_step, current_step in pairwise(timeline.steps)
        )

        ctx_switch_time: int = ctx_switch_count * scheduling.metadata.context_switch_cost
        return SchedulingOverheadMetricsSchema(
            ctx_switch_count=ctx_switch_count,
            ctx_switch_time=ctx_switch_time,
            scheduler=ctx_switch_time
        )

    @staticmethod
    def __group_steps_by_id(scheduling: SchedulingSchema, timeline: SchedulingTimelineSchema) -> Dict[str, List[SchedulingTimelineStepSchema]]:
        processes_by_pid: Set[str] = {process.pid for process in scheduling.workload.processes}
        steps_by_pid: DefaultDict[str, List[SchedulingTimelineStepSchema]] = defaultdict(list)
        for step in timeline.steps:
            if step.pid not in processes_by_pid:
                raise ValueError(f"unknown pid in timeline: {step.pid}")
            steps_by_pid[step.pid].append(step)
        return dict(steps_by_pid)
