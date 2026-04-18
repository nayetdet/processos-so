from rr_srtf.schemas.scheduling_metrics.scheduling_metrics_schema import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_event_schema import Event
from rr_srtf.simulations.simulation_context import SimulationContext


class SchedulingMetricsFactory:
    @classmethod
    def calc_metrics(cls, context: SimulationContext) -> SchedulingMetricsSchema:
        if not context.finished:
            raise RuntimeError("Cannot calculate metrics for a context that hasn't finished.")

        n = len(context.completed)
        total_time = context.clock - 1
        cpu_busy = sum(p.burst_time for p in context.completed)
        ctx_time = sum(1 for e in context.timeline if e.type == Event.SWITCHING)

        return SchedulingMetricsSchema.model_validate({
            "aggregate": {
                "avg_tat": sum(p.turnaround_time for p in context.completed) / n,
                "avg_wt": sum(p.waiting_time for p in context.completed) / n,
                "avg_rt": sum(p.response_time for p in context.completed) / n
            },
            "system": {
                "total_time": total_time,
                "busy": cpu_busy,
                "util": round(cpu_busy / total_time * 100 if total_time else 0, 2),
                "thr_at_window": round(sum(1 for p in context.completed if
                                           p.finish_time <= context.throughput_window) / context.throughput_window, 4),
                "thr_overall": round(n / total_time, 4) if total_time else 0
            },
            "overhead": {
                "ctx_count": ctx_time / context.ctx_switch_cost,
                "ctx_time": ctx_time,
                "scheduler": context.sched_oh
            }
        })