from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_overhead_metrics import SchedulingOverheadMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_performance_metrics import SchedulingPerformanceMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_process_metrics import SchedulingProcessMetricsSchema
from rr_srtf.simulations.simulation_context import SimulationContext


class SchedulingMetricsFactory:
    @classmethod
    def calc_metrics(cls, context: SimulationContext) -> SchedulingMetricsSchema:
        if not context.finished:
            raise RuntimeError("Cannot calculate metrics for a context that hasn't finished.")

        n = len(context.completed)
        total_time = context.clock - 1
        cpu_busy = sum(p.burst_time for p in context.completed)
        ctx_time = sum(1 for e in context.timeline if e.type == SchedulingTimelineState.SWITCHING)

        return SchedulingMetricsSchema(
            process=SchedulingProcessMetricsSchema(
                avg_turnaround_time=sum(p.turnaround_time for p in context.completed) / n,
                avg_waiting_time=sum(p.waiting_time for p in context.completed) / n,
                avg_response_time=sum(p.response_time for p in context.completed) / n
            ),
            performance=SchedulingPerformanceMetricsSchema(
                total_time=total_time,
                busy_time=cpu_busy,
                utilization=round(cpu_busy / total_time * 100 if total_time else 0, 2),
                throughput_at_window=round(sum(1 for p in context.completed if
                                           p.finish_time <= context.throughput_window) / context.throughput_window, 4),
                throughput_overall=round(n / total_time, 4) if total_time else 0
            ),
            overhead=SchedulingOverheadMetricsSchema(
                ctx_switch_count=int(ctx_time / context.ctx_switch_cost),
                ctx_switch_time=ctx_time,
                scheduler=context.scheduler_overhead
            )
        )