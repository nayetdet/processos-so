from collections import deque
from typing import List

from rr_srtf.context import RunContext
from rr_srtf.enums.scheduling_timeline_event import SchedulingTimelineEvent
from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.factories.scheduling_metrics_factory import SchedulingMetricsFactory
from rr_srtf.factories.scheduling_timeline_factory import SchedulingTimelineFactory
from rr_srtf.schemas.scheduling.scheduling_result_schema import SchedulingResultSchema
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_entry_schema import SchedulingTimelineEntrySchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.simulations.base_simulation import BaseSimulation
from rr_srtf.simulations.runtime_process import RuntimeProcess
from rr_srtf.simulations.simulation_context import SimulationContext


class RoundRobinSimulation(BaseSimulation):
    @classmethod
    def simulate(cls, scheduling: SchedulingSchema) -> List[SchedulingResultSchema]:
        if "RR" not in scheduling.metadata.algorithms:
            raise ValueError('Round Robin must be listed as one of the algorithms to be able to simulate')

        results: list[SchedulingResultSchema] = []
        for q in scheduling.metadata.rr_quantums or []:
            context: SimulationContext = SimulationContext(
                processes=scheduling.workload.processes,
                ctx_switch_cost=scheduling.metadata.context_switch_cost,
                throughput_window=scheduling.metadata.throughput_window_T,
                logger=RunContext.current().get_logger("RR", f"q{q}")
            )
            metrics: SchedulingMetricsSchema = cls.__simulate_once(context, q)
            timeline: SchedulingTimelineSchema = SchedulingTimelineSchema(
                algorithm="RR",
                quantum=q,
                steps=SchedulingTimelineFactory.timeline_from_entries(context.entry_timeline)
            )
            results.append(SchedulingResultSchema(final_context=context, metrics=metrics, timeline=timeline))

        return results

    @classmethod
    def __simulate_once(cls, context: SimulationContext, quantum: int) -> SchedulingMetricsSchema:
        context.flush_log_header(f"Round Robin Scheduler  |  quantum={quantum}  ctx_switch_cost={context.ctx_switch_cost}")

        ready_queue: deque[RuntimeProcess] = deque()

        while context.next_arrival < context.nb_processes or ready_queue or context.current is not None:
            context.begin_tick()

            cls.__handle_arrivals(context, ready_queue)

            if context.ongoing_event != SchedulingTimelineState.SWITCHING:
                cls.__handle_running(context, ready_queue, quantum)

            if context.ongoing_event == SchedulingTimelineState.SWITCHING and context.current is not None:
                cls.__handle_ctx_switch(context, quantum)

            context.flush_tick()
            context.tick_clock()

        context.finish()

        return SchedulingMetricsFactory.calc_metrics(context)

    @staticmethod
    def __handle_arrivals(context: SimulationContext, ready_queue: deque[RuntimeProcess]) -> None:
        while context.next_arrival < context.nb_processes and context.processes[
            context.next_arrival].arrival_time == context.clock:
            p = RuntimeProcess.from_schema(context.processes[context.next_arrival])
            ready_queue.append(p)
            context.add_timeline_entry(
                SchedulingTimelineEntrySchema(time=context.clock, type=SchedulingTimelineEvent.ARRIVE, ctx=p.pid))
            context.next_arrival += 1

    @staticmethod
    def __should_skip_running(context: SimulationContext, ready_queue: deque[RuntimeProcess], quantum: int) -> bool:
        # No process running and empty queue -> wait for next arrival
        if context.current is None and not ready_queue:
            context.add_timeline_entry(SchedulingTimelineEntrySchema(time=context.clock, type=SchedulingTimelineState.IDLE))
            return True

        # The queue has processes but none is running -> start switching to the next process
        if context.current is None:
            context.current = ready_queue.popleft()

            if context.last_pid == context.current.pid:
                # Same process re-scheduled — no context switch needed, restart quantum
                context.inner_clock = quantum

            elif (context.ongoing_event == SchedulingTimelineEvent.FINISH and not context.ctx_switch_on_finish) or (
                    context.ongoing_event == SchedulingTimelineState.IDLE and context.instant_start):
                # Previous process finished and cost_on_finish is off — skip switch penalty.
                context.inner_clock = quantum
                context.ongoing_event = SchedulingTimelineEvent.DISPATCH

            else:
                context.ongoing_event = SchedulingTimelineState.SWITCHING
                context.inner_clock = context.ctx_switch_cost
                return True

        return False

    @staticmethod
    def __dispatch_if_needed(context: SimulationContext) -> None:
        if context.ongoing_event != SchedulingTimelineEvent.DISPATCH:
            return
        context.ongoing_event = SchedulingTimelineState.RUNNING
        if context.current is not None:
            if not context.current.has_responded:
                context.current.start_time = context.clock
                context.current.response_time = context.current.start_time - context.current.arrival_time
            context.add_timeline_entry(SchedulingTimelineEntrySchema(
                time=context.clock, type=SchedulingTimelineEvent.DISPATCH, ctx=context.current.pid,
            ))

    @classmethod
    def __handle_running(cls, context: SimulationContext, ready_queue: deque[RuntimeProcess], quantum: int) -> None:
        if cls.__should_skip_running(context, ready_queue, quantum) or context.current is None:
            return

        cls.__dispatch_if_needed(context)

        if context.current is None:
            return

        context.inner_clock -= 1
        context.current.remaining_time -= 1
        context.add_timeline_entry(SchedulingTimelineEntrySchema(
            time=context.clock,
            type=SchedulingTimelineState.RUNNING,
            ctx=context.current.pid,
            detail=(
                f"{f'(q={context.inner_clock + 1} → {context.inner_clock})':<13} "
                f"{f'(r={context.current.remaining_time + 1} → {context.current.remaining_time})':<13}"
            ),
        ))

        if context.current.remaining_time == 0:
            cls.__handle_finish(context)
        elif context.inner_clock == 0:
            cls.__handle_preempt(context, ready_queue)

    @staticmethod
    def __handle_preempt(context: SimulationContext, ready_queue: deque[RuntimeProcess]) -> None:
        if context.current is None:
            return

        context.add_timeline_entry(SchedulingTimelineEntrySchema(
            time=context.clock,
            type=SchedulingTimelineEvent.PREEMPT,
            ctx=context.current.pid,
            detail=f"(r={context.current.remaining_time})",
        ))
        context.last_pid = context.current.pid
        ready_queue.append(context.current)
        context.current = None

    @staticmethod
    def __handle_finish(context: SimulationContext) -> None:
        if context.current is None:
            return
        context.current.mark_completed(context.clock)
        context.completed.append(context.current)
        context.add_timeline_entry(SchedulingTimelineEntrySchema(
            time=context.clock, type=SchedulingTimelineEvent.FINISH, ctx=context.current.pid,
        ))
        context.last_pid = context.current.pid
        context.ongoing_event = SchedulingTimelineEvent.FINISH
        context.current = None

    @staticmethod
    def __handle_ctx_switch(context: SimulationContext, quantum: int) -> None:
        if context.inner_clock > 0:
            context.inner_clock -= 1
            context.add_timeline_entry(SchedulingTimelineEntrySchema(
                time=context.clock,
                type=SchedulingTimelineState.SWITCHING,
                ctx=f"{context.last_pid} → {context.current.pid}",
                detail=f"{f'(t={context.inner_clock + 1} → {context.inner_clock})':<13}"
            ))

        if context.inner_clock == 0:
            context.inner_clock = quantum
            context.ongoing_event = SchedulingTimelineEvent.DISPATCH
