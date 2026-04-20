from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_overhead_metrics import SchedulingOverheadMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_performance_metrics import SchedulingPerformanceMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_process_metrics import SchedulingProcessMetricsSchema
from rr_srtf.schemas.scheduling_runtime.simulation_context import SimulationContext


class SchedulingMetricsFactory:
    @classmethod
    def calc_metrics(cls, ctx: SimulationContext) -> SchedulingMetricsSchema:
        if not ctx.state.finished:
            raise RuntimeError("Cannot calculate metrics for a context that hasn't finished.")

        n = len(ctx.state.completed)
        total_time = ctx.state.clock
        cpu_busy = sum(p.burst_time for p in ctx.state.completed)
        ctx_time = sum(1 for e in ctx.timeline.entries if e.type == SchedulingTimelineState.SWITCHING)

        return SchedulingMetricsSchema(
            process=SchedulingProcessMetricsSchema(
                avg_turnaround_time=sum(p.turnaround_time for p in ctx.state.completed) / n,
                avg_waiting_time=sum(p.waiting_time for p in ctx.state.completed) / n,
                avg_response_time=sum(p.response_time for p in ctx.state.completed) / n
            ),
            performance=SchedulingPerformanceMetricsSchema(
                total_time=total_time,
                busy_time=cpu_busy,
                utilization=round(cpu_busy / total_time * 100 if total_time else 0, 2),
                throughput_at_window=round(sum(1 for p in ctx.state.completed if
                                               p.finish_time <= ctx.config.throughput_window) / ctx.config.throughput_window, 4),
                throughput_overall=round(n / total_time, 4) if total_time else 0
            ),
            overhead=SchedulingOverheadMetricsSchema(
                ctx_switch_count=int(ctx_time / ctx.config.ctx_switch_cost),
                ctx_switch_time=ctx_time,
                scheduler=sum(1 for e in ctx.timeline.entries if e.type == SchedulingTimelineState.RUNNING and e.ctx in ("RR", "SRTF"))
            )
        )