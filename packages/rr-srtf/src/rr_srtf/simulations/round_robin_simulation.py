from typing import List

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
            if not context.tick_done:
                cls.__handle_arrivals(context)

            # RUNNING
            if not context.switching:
                cls.__handle_running(context)

            # CTX_SWITCH
            if not context.tick_done and context.switching and context.current is not None:
                cls.__handle_ctx_switch(context)

            context.tick_done = False
            context.flush_tick()

        return SchedulingResultSchema(
            timeline=context.timeline,
            processes=context.completed,
            stats=cls.__calc_metrics(context)
        )

    @classmethod
    def __handle_arrivals(cls, context: SimulationContext) -> None:
        while context.next_arrival < len(context.processes) and context.processes[context.next_arrival].arrival_time == context.clock:
            p = ProcessModel.model_validate(context.processes[context.next_arrival].model_dump())
            context.ready_queue.append(p)
            context.add_event(SchedulingEventSchema(time=context.clock, type=Event.ARRIVE, ctx=p.pid))
            context.next_arrival += 1

    @classmethod
    def __handle_running(cls, context: SimulationContext) -> None:
        if not context.tick_done and not context.switching:
            if not context.ready_queue and context.current is None :  # no process running and empty queue -> wait for next arrival
                context.add_event(SchedulingEventSchema(time=context.clock, type=Event.IDLE))

            elif context.ready_queue and context.current is None:  # the queue has processes but none is running -> start switching to the next process
                context.current = context.ready_queue.popleft()
                if context.current is not None and context.last_pid == context.current.pid:  # dont need context switch
                    context.inner_clock = context.quantum  # just restart the quantum
                else:
                    if context.just_completed and not context.cost_on_finish:
                        context.inner_clock = context.quantum
                        context.just_completed = False
                        context.just_dispatched = True
                    else:
                        context.switching = True
                        context.inner_clock = context.ctx_switch_cost

        if not context.tick_done and not context.switching and context.current is not None:
            if context.just_dispatched:
                context.just_dispatched = False
                if context.current.start_time is None:
                    context.current.start_time = context.clock
                    context.current.response_time = context.current.start_time - context.current.arrival_time
                context.add_event(SchedulingEventSchema(
                    time=context.clock,
                    type=Event.DISPATCH,
                    ctx=context.current.pid
                ))
            context.inner_clock -= 1
            context.current.remaining_time -= 1
            context.add_event(SchedulingEventSchema(
                time=context.clock,
                type=Event.RUNNING,
                ctx=context.current.pid,
                detail=f"{f'(q={context.inner_clock + 1} → {context.inner_clock})':<13}  {f'(r={context.current.remaining_time + 1} → {context.current.remaining_time})':<13}"
            ))
            end_ev = None
            if context.current.remaining_time == 0:  # cur_proc also finishes on this clock pulse
                end_ev = SchedulingEventSchema(
                    time=context.clock,
                    type=Event.FINISH,
                    ctx=context.current.pid
                )
                context.last_pid = context.current.pid
                context.current.mark_completed(context.clock)
                context.completed.append(context.current)
                context.just_completed = True
            if context.inner_clock == 0 and end_ev is None:  # cur_proc is also preempted on this clock pulse
                end_ev = SchedulingEventSchema(
                    time=context.clock,
                    type=Event.PREEMPT,
                    ctx=context.current.pid,
                    detail=f"(r={context.current.remaining_time})"
                )
                context.last_pid = context.current.pid
                context.ready_queue.append(context.current)
            if end_ev is not None:
                context.add_event(end_ev)
                context.current = None
            context.tick_done = True

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



    @classmethod
    def __calc_metrics(cls, context: SimulationContext) -> SchedulingMetricsSchema:
        n = len(context.completed)
        total_time = context.clock - 1
        cpu_busy = sum(p.burst_time for p in context.completed)
        ctx_time = sum(1 for e in context.timeline if e.type == Event.SWITCHING)

        result = {
            "aggregate": {
                "avg_tat": sum(p.turnaround_time for p in context.completed) / n,
                "avg_wt": sum(p.waiting_time for p in context.completed) / n,
                "avg_rt": sum(p.response_time for p in context.completed) / n
            },
            "system": {
                "total_time": total_time,
                "busy": cpu_busy,
                "util": round(cpu_busy / total_time * 100 if total_time else 0, 2),
                "thr_at_window": round(sum(1 for p in context.completed if p.finish_time <= context.throughput_window) / context.throughput_window, 4 ),
                "thr_overall": round(n / total_time, 4) if total_time else 0
            },
            "overhead": {
                "ctx_count": ctx_time / context.ctx_switch_cost,
                "ctx_time": ctx_time,
                "scheduler": context.sched_oh
            }
        }
        return SchedulingMetricsSchema.model_validate(result)
