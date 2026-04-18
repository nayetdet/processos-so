from collections import deque, defaultdict
from dataclasses import dataclass
from typing import List, Optional, Deque, Callable, cast

from rr_srtf.models.process_model import ProcessModel
from rr_srtf.schemas.scheduling.scheduling_result_schema import SchedulingResultSchema
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_schema import SchedulingWorkloadSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics_schema import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_event_schema import SchedulingEventSchema, Event
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.simulations.base_simulation import BaseSimulation


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
            result: SchedulingResultSchema = cls.__simulate_once(
                workload=scheduling.workload,
                quantum=q,
                ctx_switch_cost=scheduling.metadata.context_switch_cost,
                throughput_window=scheduling.metadata.throughput_window_T
            )
            timelines.append(SchedulingTimelineSchema(
                algorithm="RR",
                quantum=q,
                steps=result.compressed_timeline
            ))
        print()

        print(timelines[-1].model_dump_json(indent=2))

        return timelines

    @classmethod
    def __simulate_once(
            cls,
            workload: SchedulingWorkloadSchema,
            quantum: int,
            ctx_switch_cost: int,
            throughput_window: int,
            cost_on_finish: bool = False
    ) -> SchedulingResultSchema:

        print("=" * 60)
        print(f"Round Robin Scheduler  |  {quantum=}  {ctx_switch_cost=}")
        print(f"Processes: {[(p.pid, p.arrival_time, p.burst_time) for p in workload.processes]}")
        print("=" * 60)

        timeline: List[SchedulingEventSchema] = []
        ready_queue: deque[ProcessModel] = deque()
        remaining_procs: deque[ProcessModel] = deque([ProcessModel.model_validate(p.model_dump()) for p in workload.processes])
        completed: List[ProcessModel] = []
        clock: int = 0
        inner_clock: int = 0
        last_pid: Optional[str] = None
        proc: Optional[ProcessModel] = None
        tick_done: bool = False
        switching: bool = False
        just_dispatched: bool = False
        just_completed: bool = False
        sched_oh: int = 0  # amount of ticks the scheduler was in the cpu

        def add_event(event: SchedulingEventSchema):
            timeline.append(event)
            message_parts.append(event.no_time_str())

        while remaining_procs or ready_queue or proc is not None:
            message_parts: List[str] = [f"[{clock:03}]"]

            # ARRIVE
            if not tick_done:
                cls.__handle_arrivals(remaining_procs, ready_queue, clock, add_event)

            if clock == 0 and not ready_queue:
                add_event(SchedulingEventSchema(time=clock, type=Event.IDLE))

            # RUNNING
            if not tick_done and not switching:
                if not ready_queue and proc is None and clock != 0:  # no process running and empty queue -> wait for next arrival
                    add_event(SchedulingEventSchema(time=clock, type=Event.IDLE))

                elif ready_queue and proc is None:  # the queue has processes but none is running -> start switching to the next process
                    proc = ready_queue.popleft()
                    if proc is not None and last_pid == proc.pid:  # dont need context switch
                        inner_clock = quantum  # just restart the quantum
                    else:
                        if just_completed and not cost_on_finish:
                            inner_clock = quantum
                            just_completed = False
                            just_dispatched = True
                        else:
                            switching = True
                            inner_clock = ctx_switch_cost

            if not tick_done and not switching and proc is not None:
                if just_dispatched:
                    just_dispatched = False
                    if proc.start_time is None:
                        proc.start_time = clock
                        proc.response_time = proc.start_time - proc.arrival_time
                    add_event(SchedulingEventSchema(time=clock, type=Event.DISPATCH, ctx=proc.pid))
                inner_clock -= 1
                proc.remaining_time -= 1
                add_event(SchedulingEventSchema(time=clock, type=Event.RUNNING, ctx=proc.pid,
                                                detail=f"{f'(q={inner_clock + 1} → {inner_clock})':<13}  {f'(r={proc.remaining_time + 1} → {proc.remaining_time})':<13}"))
                end_ev = None
                if proc.remaining_time == 0:  # cur_proc also finishes on this clock pulse
                    end_ev = SchedulingEventSchema(time=clock, type=Event.FINISH, ctx=proc.pid)
                    last_pid = proc.pid
                    proc.mark_completed(clock)
                    completed.append(proc)
                    just_completed = True
                if inner_clock == 0 and end_ev is None:  # cur_proc is also preempted on this clock pulse
                    end_ev = SchedulingEventSchema(time=clock, type=Event.PREEMPT, ctx=proc.pid,
                                                   detail=f"(r={proc.remaining_time} {workload.time_unit})")
                    last_pid = proc.pid
                    ready_queue.append(proc)
                if end_ev is not None:
                    add_event(end_ev)
                    proc = None
                tick_done = True

            # CTX_SWITCH
            if not tick_done and switching and proc is not None:
                if inner_clock > 0:
                    inner_clock -= 1
                    add_event(
                        SchedulingEventSchema(time=clock, type=Event.SWITCHING, ctx=f"{last_pid} → {proc.pid}",
                                              detail=f"{f'(t={inner_clock + 1} → {inner_clock})':<13}"))
                if inner_clock == 0:
                    just_dispatched = True
                    switching = False
                    inner_clock = quantum

            tick_done = False
            print(" | ".join(message_parts))
            clock += 1

        return SchedulingResultSchema(
            timeline=timeline,
            processes=completed,
            stats=cls.__calc_metrics(completed, clock - 1, timeline, throughput_window, ctx_switch_cost, sched_oh)
        )

    @classmethod
    def __handle_arrivals(
            cls,
            remaining_procs: Deque[ProcessModel],
            ready_queue: Deque[ProcessModel],
            clock: int,
            add_event: Callable[[SchedulingEventSchema], None]
    ) -> None:
        while remaining_procs and remaining_procs[0].arrival_time == clock:
            p = remaining_procs.popleft()
            ready_queue.append(p)
            add_event(SchedulingEventSchema(time=clock, type=Event.ARRIVE, ctx=p.pid))

    @classmethod
    def __calc_metrics(
            cls,
            completed: list[ProcessModel],
            total_time: int,
            timeline: list[SchedulingEventSchema],
            throughput_window: int,
            ctx_switch_cost: int,
            sched_oh: int
    ) -> SchedulingMetricsSchema:

        n = len(completed)
        cpu_busy = sum(p.burst_time for p in completed)
        ctx_time = sum(1 for e in timeline if e.type == Event.SWITCHING)

        result = {
            "aggregate": {
                "avg_tat": sum(p.turnaround_time for p in completed) / n,
                "avg_wt": sum(p.waiting_time for p in completed) / n,
                "avg_rt": sum(p.response_time for p in completed) / n
            },
            "system": {
                "total_time": total_time,
                "busy": cpu_busy,
                "util": round(cpu_busy / total_time * 100 if total_time else 0, 2),
                "thr_at_window": round(sum(1 for p in completed if p.finish_time <= throughput_window) / throughput_window, 4 ),
                "thr_overall": round(n / total_time, 4) if total_time else 0
            },
            "overhead": {
                "ctx_count": ctx_time / ctx_switch_cost,
                "ctx_time": ctx_time,
                "scheduler": sched_oh
            }
        }
        return SchedulingMetricsSchema.model_validate(result)
