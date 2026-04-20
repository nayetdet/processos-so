import heapq
from random import Random
from typing import List

from rr_srtf.enums.scheduling_timeline_event import SchedulingTimelineEvent
from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.factories.scheduling_metrics_factory import SchedulingMetricsFactory
from rr_srtf.factories.scheduling_timeline_factory import SchedulingTimelineFactory
from rr_srtf.schemas.scheduling.scheduling_result_schema import SchedulingResultSchema
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_runtime.run_context import RunContext
from rr_srtf.schemas.scheduling_runtime.runtime_process import RuntimeProcess
from rr_srtf.schemas.scheduling_runtime.simulation_config import SimulationConfig
from rr_srtf.schemas.scheduling_runtime.simulation_context import SimulationContext
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_entry_schema import SchedulingTimelineEntrySchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.simulations.base_simulation import BaseSimulation


class ShortestRemainingTimeFirstSimulation(BaseSimulation):
    SEED: int = 0

    @classmethod
    def simulate(cls, scheduling: SchedulingSchema) -> List[SchedulingResultSchema]:
        if "SRTF" not in scheduling.metadata.algorithms:
            raise ValueError("Shortest Remaining Time First must be listed as one of the algorithms to be able to simulate")

        context: SimulationContext = SimulationContext(
            config=SimulationConfig.for_srtf(scheduling),
            logger=RunContext.current().get_logger("SRTF")
        )
        metrics: SchedulingMetricsSchema = cls.__simulate_once(ctx=context)
        timeline: SchedulingTimelineSchema = SchedulingTimelineSchema(
            algorithm="SRTF",
            steps=SchedulingTimelineFactory.timeline_from_entries(context.timeline.entries)
        )

        return [SchedulingResultSchema(final_context=context, timeline=timeline, metrics=metrics)]

    @classmethod
    def __simulate_once(cls, ctx: SimulationContext) -> SchedulingMetricsSchema:
        ctx.flush_log_header("Shortest Remaining Time First Scheduler")

        rng: Random = Random(cls.SEED)
        ready_queue: list[tuple[int, float, str, RuntimeProcess]] = []

        while not ctx.state.finished:
            with ctx.tick():
                cls.__enqueue_arrived_processes(ctx=ctx, ready_queue=ready_queue, rng=rng)

                if ctx.state.ongoing_event != SchedulingTimelineState.SWITCHING:
                    cls.__handle_running(ctx=ctx, ready_queue=ready_queue, rng=rng)

                if ctx.state.ongoing_event == SchedulingTimelineState.SWITCHING:
                    cls.__handle_ctx_switch(ctx=ctx)

                if ctx.state.next_arrival >= ctx.config.nb_processes and not ready_queue and ctx.state.current is None:
                    ctx.state.finish()

        return SchedulingMetricsFactory.calc_metrics(ctx=ctx)

    @staticmethod
    def __enqueue_arrived_processes(
        ctx: SimulationContext,
        ready_queue: list[tuple[int, float, str, RuntimeProcess]],
        rng: Random
    ) -> None:
        while ctx.state.next_arrival < ctx.config.nb_processes and ctx.config.processes[int(ctx.state.next_arrival)].arrival_time <= ctx.state.clock:
            p = RuntimeProcess(schema=ctx.config.processes[int(ctx.state.next_arrival)])
            heapq.heappush(ready_queue, (p.remaining_time, rng.random(), p.pid, p))
            ctx.timeline.add_entry(SchedulingTimelineEntrySchema(
                time=ctx.state.clock,
                type=SchedulingTimelineEvent.ARRIVE,
                ctx=p.pid
            ))
            ctx.state.next_arrival += 1

    @classmethod
    def __handle_running(
        cls,
        ctx: SimulationContext,
        ready_queue: list[tuple[int, float, str, RuntimeProcess]],
        rng: Random
    ) -> None:
        if cls.__should_skip_running(ctx=ctx, ready_queue=ready_queue):
            return

        cls.__dispatch_if_needed(ctx=ctx, ready_queue=ready_queue)

        if ctx.state.current is None:
            return

        if cls.__try_preempt(ctx=ctx, ready_queue=ready_queue, rng=rng):
            return

        ctx.state.current.remaining_time -= 1
        ctx.timeline.add_entry(SchedulingTimelineEntrySchema(
            time=ctx.state.clock,
            type=SchedulingTimelineState.RUNNING,
            ctx=ctx.state.current.pid,
            detail=f"{f'(r={ctx.state.current.remaining_time + 1} → {ctx.state.current.remaining_time})':<13}",
        ))

        if ctx.state.current.remaining_time == 0:
            cls.__handle_finish(ctx)

    @staticmethod
    def __should_skip_running(
        ctx: SimulationContext,
        ready_queue: list[tuple[int, float, str, RuntimeProcess]]
    ) -> bool:
        if ctx.state.current is None and not ready_queue:
            ctx.timeline.add_entry(SchedulingTimelineEntrySchema(
                time=ctx.state.clock,
                type=SchedulingTimelineState.IDLE
            ))
            return True

        if ctx.state.current is None:
            if ctx.state.ongoing_event == SchedulingTimelineEvent.DISPATCH:
                return False
            if (ctx.state.ongoing_event == SchedulingTimelineEvent.FINISH and not ctx.config.ctx_switch_on_finish) or (
                    ctx.state.ongoing_event == SchedulingTimelineState.IDLE and ctx.config.instant_start):
                ctx.state.ongoing_event = SchedulingTimelineEvent.DISPATCH
            else:
                ctx.state.ongoing_event = SchedulingTimelineState.SWITCHING
                ctx.state.inner_clock = ctx.config.ctx_switch_cost
                return True

        return False

    @staticmethod
    def __dispatch_if_needed(
        ctx: SimulationContext,
        ready_queue: list[tuple[int, float, str, RuntimeProcess]]
    ) -> None:
        if ctx.state.ongoing_event != SchedulingTimelineEvent.DISPATCH:
            return

        *_, ctx.state.current = heapq.heappop(ready_queue)
        ctx.state.ongoing_event = SchedulingTimelineState.RUNNING

        if not ctx.state.current.has_responded:
            ctx.state.current.start_time = ctx.state.clock
            ctx.state.current.response_time = ctx.state.clock - ctx.state.current.arrival_time

        ctx.timeline.add_entry(SchedulingTimelineEntrySchema(
            time=ctx.state.clock,
            type=SchedulingTimelineEvent.DISPATCH,
            ctx=ctx.state.current.pid,
        ))

    @staticmethod
    def __try_preempt(
        ctx: SimulationContext,
        ready_queue: list[tuple[int, float, str, RuntimeProcess]],
        rng: Random
    ) -> bool:
        if not ready_queue or ready_queue[0][0] >= ctx.state.current.remaining_time:
            return False

        ctx.timeline.add_entry(SchedulingTimelineEntrySchema(
            time=ctx.state.clock,
            type=SchedulingTimelineEvent.PREEMPT,
            ctx=ctx.state.current.pid,
            detail=f"(r={ctx.state.current.remaining_time})",
        ))

        heapq.heappush(ready_queue,(ctx.state.current.remaining_time, rng.random(), ctx.state.current.pid, ctx.state.current))
        ctx.state.last_pid = ctx.state.current.pid
        ctx.state.current = None

        if ctx.config.ctx_switch_cost > 0:
            ctx.state.ongoing_event = SchedulingTimelineState.SWITCHING
            ctx.state.inner_clock = ctx.config.ctx_switch_cost
        else:
            ctx.state.ongoing_event = SchedulingTimelineEvent.DISPATCH

        return True

    @staticmethod
    def __handle_finish(ctx: SimulationContext) -> None:
        if ctx.state.current is None:
            return
        ctx.state.current.mark_completed(ctx.state.clock)
        ctx.state.completed.append(ctx.state.current)
        ctx.timeline.add_entry(SchedulingTimelineEntrySchema(
            time=ctx.state.clock, type=SchedulingTimelineEvent.FINISH, ctx=ctx.state.current.pid,
        ))
        ctx.state.last_pid = ctx.state.current.pid
        ctx.state.ongoing_event = SchedulingTimelineEvent.FINISH
        ctx.state.current = None

    @staticmethod
    def __handle_ctx_switch(ctx: SimulationContext) -> None:
        if ctx.state.inner_clock > 0:
            ctx.state.inner_clock -= 1
            ctx.timeline.add_entry(SchedulingTimelineEntrySchema(
                time=ctx.state.clock,
                type=SchedulingTimelineState.SWITCHING,
                detail=f"{f'(t={ctx.state.inner_clock + 1} → {ctx.state.inner_clock})':<13}"
            ))

        if ctx.state.inner_clock == 0:
            ctx.state.ongoing_event = SchedulingTimelineEvent.DISPATCH

