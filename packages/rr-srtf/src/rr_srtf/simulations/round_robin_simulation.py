from collections import deque
from typing import List

from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling_runtime.run_context import RunContext
from rr_srtf.enums.scheduling_timeline_event import SchedulingTimelineEvent
from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.factories.scheduling_metrics_factory import SchedulingMetricsFactory
from rr_srtf.factories.scheduling_timeline_factory import SchedulingTimelineFactory
from rr_srtf.schemas.scheduling.scheduling_result_schema import SchedulingResultSchema
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_runtime.simulation_config import SimulationConfig
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_entry_schema import SchedulingTimelineEntrySchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.simulations.base_simulation import BaseSimulation
from rr_srtf.schemas.scheduling_runtime.runtime_process import RuntimeProcess
from rr_srtf.schemas.scheduling_runtime.simulation_context import SimulationContext


class RoundRobinSimulation(BaseSimulation):
    @classmethod
    def simulate(cls, scheduling: SchedulingSchema) -> List[SchedulingResultSchema]:
        if "RR" not in scheduling.metadata.algorithms:
            raise ValueError('Round Robin must be listed as one of the algorithms to be able to simulate')

        results: list[SchedulingResultSchema] = []
        for q, config in SimulationConfig.for_rr_variants(scheduling):
            context: SimulationContext = SimulationContext(
                config=config,
                logger=RunContext.current().get_logger("RR", f"q{q}")
            )
            metrics: SchedulingMetricsSchema = cls.__simulate_once(context, q)
            timeline: SchedulingTimelineSchema = SchedulingTimelineSchema(
                algorithm="RR",
                quantum=q,
                steps=SchedulingTimelineFactory.timeline_from_entries(context.timeline.entries)
            )
            results.append(SchedulingResultSchema(final_context=context, metrics=metrics, timeline=timeline))

        return results

    @classmethod
    def __simulate_once(cls, ctx: SimulationContext, quantum: int) -> SchedulingMetricsSchema:
        ctx.flush_log_header(f"Round Robin Scheduler  |  quantum={quantum}  ctx_switch_cost={ctx.config.ctx_switch_cost}")

        ready_queue: deque[RuntimeProcess] = deque()

        while not ctx.state.finished:
            with ctx.tick():
                cls.__handle_arrivals(ctx, ready_queue)

                if ctx.state.ongoing_event != SchedulingTimelineState.SWITCHING:
                    cls.__handle_running(ctx, ready_queue, quantum)

                if ctx.state.ongoing_event == SchedulingTimelineState.SWITCHING and ctx.state.current is not None:
                    cls.__handle_ctx_switch(ctx, quantum)

                if ctx.state.next_arrival >= ctx.config.nb_processes and not ready_queue and ctx.state.current is None:
                    ctx.state.finish()

        return SchedulingMetricsFactory.calc_metrics(ctx)

    @staticmethod
    def __handle_arrivals(ctx: SimulationContext, ready_queue: deque[RuntimeProcess]) -> None:
        while (
                ctx.state.next_arrival < ctx.config.nb_processes
                and ctx.config.processes[int(ctx.state.next_arrival)].arrival_time == ctx.state.clock
        ):
            p = ctx.config.processes[int(ctx.state.next_arrival)]
            ready_queue.append(RuntimeProcess(schema=p))
            ctx.timeline.add_entry(
                SchedulingTimelineEntrySchema(time=ctx.state.clock, type=SchedulingTimelineEvent.ARRIVE, ctx=p.pid))
            ctx.state.next_arrival += 1

    @staticmethod
    def __should_skip_running(ctx: SimulationContext, ready_queue: deque[RuntimeProcess], quantum: int) -> bool:
        # No process running and empty queue -> wait for next arrival
        if ctx.state.current is None and not ready_queue:
            ctx.timeline.add_entry(SchedulingTimelineEntrySchema(time=ctx.state.clock, type=SchedulingTimelineState.IDLE))
            return True

        # The queue has processes but none is running -> start switching to the next process
        if ctx.state.current is None:
            ctx.state.current = ready_queue.popleft()

            if ctx.state.last_pid == ctx.state.current.pid:
                # Same process re-scheduled — no context switch needed, restart quantum
                ctx.state.inner_clock = quantum

            elif (ctx.state.ongoing_event == SchedulingTimelineEvent.FINISH and not ctx.config.ctx_switch_on_finish) or (
                    ctx.state.ongoing_event == SchedulingTimelineState.IDLE and ctx.config.instant_start):
                # Previous process finished and cost_on_finish is off — skip switch penalty.
                ctx.state.inner_clock = quantum
                ctx.state.ongoing_event = SchedulingTimelineEvent.DISPATCH

            else:
                ctx.state.ongoing_event = SchedulingTimelineState.SWITCHING
                ctx.state.inner_clock = ctx.config.ctx_switch_cost
                return True

        return False

    @staticmethod
    def __dispatch_if_needed(ctx: SimulationContext) -> None:
        if ctx.state.ongoing_event != SchedulingTimelineEvent.DISPATCH:
            return
        ctx.state.ongoing_event = SchedulingTimelineState.RUNNING
        if ctx.state.current is not None:
            if not ctx.state.current.has_responded:
                ctx.state.current.start_time = ctx.state.clock
                ctx.state.current.response_time = ctx.state.current.start_time - ctx.state.current.arrival_time
            ctx.timeline.add_entry(SchedulingTimelineEntrySchema(
                time=ctx.state.clock, type=SchedulingTimelineEvent.DISPATCH, ctx=ctx.state.current.pid,
            ))

    @classmethod
    def __handle_running(cls, ctx: SimulationContext, ready_queue: deque[RuntimeProcess], quantum: int) -> None:
        if cls.__should_skip_running(ctx, ready_queue, quantum) or ctx.state.current is None:
            return

        cls.__dispatch_if_needed(ctx)

        if ctx.state.current is None:
            return

        ctx.state.inner_clock -= 1
        ctx.state.current.remaining_time -= 1
        ctx.timeline.add_entry(SchedulingTimelineEntrySchema(
            time=ctx.state.clock,
            type=SchedulingTimelineState.RUNNING,
            ctx=ctx.state.current.pid,
            detail=(
                f"{f'(q={ctx.state.inner_clock + 1} → {ctx.state.inner_clock})':<13} "
                f"{f'(r={ctx.state.current.remaining_time + 1} → {ctx.state.current.remaining_time})':<13}"
            ),
        ))

        if ctx.state.current.remaining_time == 0:
            cls.__handle_finish(ctx)
        elif ctx.state.inner_clock == 0:
            cls.__handle_preempt(ctx, ready_queue)

    @staticmethod
    def __handle_preempt(ctx: SimulationContext, ready_queue: deque[RuntimeProcess]) -> None:
        if ctx.state.current is None:
            return

        ctx.timeline.add_entry(SchedulingTimelineEntrySchema(
            time=ctx.state.clock,
            type=SchedulingTimelineEvent.PREEMPT,
            ctx=ctx.state.current.pid,
            detail=f"(r={ctx.state.current.remaining_time})",
        ))
        ctx.state.last_pid = ctx.state.current.pid
        ready_queue.append(ctx.state.current)
        ctx.state.current = None

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
    def __handle_ctx_switch(ctx: SimulationContext, quantum: int) -> None:
        if ctx.state.inner_clock > 0:
            ctx.state.inner_clock -= 1
            ctx.timeline.add_entry(SchedulingTimelineEntrySchema(
                time=ctx.state.clock,
                type=SchedulingTimelineState.SWITCHING,
                ctx=f"{ctx.state.last_pid} → {ctx.state.current.pid}",
                detail=f"{f'(t={ctx.state.inner_clock + 1} → {ctx.state.inner_clock})':<13}"
            ))

        if ctx.state.inner_clock == 0:
            ctx.state.inner_clock = quantum
            ctx.state.ongoing_event = SchedulingTimelineEvent.DISPATCH
