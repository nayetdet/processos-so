from typing import List, Optional

from rr_srtf.factories.scheduling_metrics_factory import SchedulingMetricsFactory
from rr_srtf.models.process_model import ProcessModel
from rr_srtf.schemas.scheduling.scheduling_result_schema import SchedulingResultSchema
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics_schema import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_event_schema import SchedulingEventSchema, Event
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.simulations.base_simulation import BaseSimulation
from rr_srtf.simulations.simulation_context import SimulationContext


class RoundRobinSimulation(BaseSimulation):
    @classmethod
    def simulate(cls, scheduling: SchedulingSchema) -> List[SchedulingTimelineSchema]:
        if "RR" not in scheduling.metadata.algorithms:
            raise ValueError('RR must be listed as one of the algorithms to be able to simulate')
        print("=" * 60)
        print(f"Round Robin Scheduler Runs  |  quantums={scheduling.metadata.rr_quantums}")
        print("=" * 60)
        print()

        timelines: list[SchedulingTimelineSchema] = []
        for q in scheduling.metadata.rr_quantums or []:
            context: SimulationContext = SimulationContext(
                processes=scheduling.workload.processes,
                quantum=q,
                ctx_switch_cost=scheduling.metadata.context_switch_cost,
                throughput_window=scheduling.metadata.throughput_window_T
            )
            result: SchedulingResultSchema = cls.__simulate_once(context)
            timelines.append(SchedulingTimelineSchema(
                algorithm="RR",
                quantum=q,
                steps=result.compressed_timeline
            ))
        print()

        print(timelines[-1].model_dump_json(indent=2))

        return timelines

    @classmethod
    def __simulate_once(cls, context: SimulationContext) -> SchedulingResultSchema:
        print("=" * 60)
        print(f"Round Robin Scheduler  |  quantum={context.quantum}  ctx_switch_cost={context.ctx_switch_cost}")
        print(f"Processes: {[(p.pid, p.arrival_time, p.burst_time) for p in context.processes]}")
        print("=" * 60)

        while context.next_arrival < len(context.processes) or context.ready_queue or context.current is not None:
            context.begin_tick()
            # ARRIVE
            cls.__handle_arrivals(context)

            # RUNNING
            if not context.switching:
                cls.__handle_running(context)

            # CTX_SWITCH
            if context.switching and context.current is not None:
                cls.__handle_ctx_switch(context)

            context.flush_tick()

        context.finish()

        return SchedulingResultSchema(
            timeline=context.timeline,
            processes=context.completed,
            stats=SchedulingMetricsFactory.calc_metrics(context)
        )

    @classmethod
    def __handle_arrivals(cls, context: SimulationContext) -> None:
        while context.next_arrival < len(context.processes) and context.processes[context.next_arrival].arrival_time == context.clock:
            p = ProcessModel.model_validate(context.processes[context.next_arrival].model_dump())
            context.ready_queue.append(p)
            context.add_event(SchedulingEventSchema(time=context.clock, type=Event.ARRIVE, ctx=p.pid))
            context.next_arrival += 1

    @classmethod
    def __handle_tick_start(cls, context: SimulationContext) -> bool:
        # No process running and empty queue -> wait for next arrival
        if context.current is None and not context.ready_queue:
            context.add_event(SchedulingEventSchema(time=context.clock, type=Event.IDLE))
            return True

        # The queue has processes but none is running -> start switching to the next process
        if context.current is None:
            context.current = context.ready_queue.popleft()

            if context.last_pid == context.current.pid:
                # Same process re-scheduled — no context switch needed, restart quantum
                context.inner_clock = context.quantum
                context.just_dispatched = True

            elif context.just_completed and not context.cost_on_finish:
                # Previous process finished and cost_on_finish is off — skip switch penalty.
                context.inner_clock = context.quantum
                context.just_completed = False
                context.just_dispatched = True

            else:
                context.switching = True
                context.inner_clock = context.ctx_switch_cost
                return True

        if context.current is not None and context.just_dispatched:
            context.just_dispatched = False
            if context.current.start_time is None:
                context.current.start_time = context.clock
                context.current.response_time = context.current.start_time - context.current.arrival_time
            context.add_event(SchedulingEventSchema(
                time=context.clock, type=Event.DISPATCH, ctx=context.current.pid,
            ))

        return False

    @classmethod
    def __handle_running(cls, context: SimulationContext) -> None:
        early_return: bool = cls.__handle_tick_start(context)

        if early_return or context.current is None: return

        context.inner_clock -= 1
        context.current.remaining_time -= 1
        context.add_event(SchedulingEventSchema(
            time=context.clock,
            type=Event.RUNNING,
            ctx=context.current.pid,
            detail=(
                f"{f'(q={context.inner_clock + 1} → {context.inner_clock})':<13}  "
                f"{f'(r={context.current.remaining_time + 1} → {context.current.remaining_time})':<13}"
            ),
        ))

        cls.__handle_tick_end(context)

    @classmethod
    def __handle_tick_end(cls, context: SimulationContext) -> None:
        end_event: Optional[SchedulingEventSchema] = None

        if context.current is None: return

        if context.current.remaining_time == 0: # current process also finishes on the end of this clock pulse
            context.current.mark_completed(context.clock)
            context.completed.append(context.current)
            end_event = SchedulingEventSchema(
                time=context.clock, type=Event.FINISH, ctx=context.current.pid,
            )
            context.last_pid = context.current.pid
            context.just_completed = True

        elif context.inner_clock == 0: # current process is also preempted on the end of this clock pulse
            end_event = SchedulingEventSchema(
                time=context.clock,
                type=Event.PREEMPT,
                ctx=context.current.pid,
                detail=f"(r={context.current.remaining_time})",
            )
            context.last_pid = context.current.pid
            context.ready_queue.append(context.current)

        if end_event is not None:
            context.add_event(end_event)
            context.current = None

    @classmethod
    def __handle_ctx_switch(cls, context: SimulationContext) -> None:
        if context.inner_clock > 0:
            context.inner_clock -= 1
            context.add_event(SchedulingEventSchema(
                    time=context.clock,
                    type=Event.SWITCHING,
                    ctx=f"{context.last_pid} → {context.current.pid}",
                    detail=f"{f'(t={context.inner_clock + 1} → {context.inner_clock})':<13}"
            ))

        if context.inner_clock == 0:
            context.switching = False
            context.inner_clock = context.quantum
            context.just_dispatched = True
