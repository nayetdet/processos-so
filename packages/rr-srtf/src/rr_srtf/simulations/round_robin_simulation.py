from collections import deque
from typing import List, Optional, Any

from rr_srtf.models.process_model import Process
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_schema import SchedulingWorkloadSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_event_schema import SchedulingEventSchema, Event
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.simulations.base_simulation import BaseSimulation


class RoundRobinSimulation(BaseSimulation):
    @staticmethod
    def simulate(scheduling: SchedulingSchema) -> List[SchedulingTimelineSchema]:
        if "RR" not in scheduling.metadata.algorithms:
            raise ValueError('RR must be listed as one of the algorithms to be able to simulate')
        print("=" * 60)
        print(f"Round Robin Scheduler Runs  |  quantums={scheduling.metadata.rr_quantums}")
        print("=" * 60)
        print()

        def round_robin(workload: SchedulingWorkloadSchema,
                        quantum: int,
                        ctx_switch_cost: int,
                        throughput_window: int,
                        cost_on_finish: bool = False) -> dict[str, list[SchedulingEventSchema] | list[Process] | dict[str, Any]]:
            print("=" * 60)
            print(f"Round Robin Scheduler  |  {quantum=}  {ctx_switch_cost=}")
            print(f"Processes: {[(p.pid, p.arrival_time, p.burst_time) for p in workload.processes]}")
            print("=" * 60)

            timeline: List[SchedulingEventSchema] = []
            ready_queue: deque[Process] = deque()
            remaining_procs: deque[Process] = deque(
                sorted([Process.model_validate(p.model_dump()) for p in workload.processes],
                       key=lambda p: p.arrival_time)
            )
            completed: List[Process] = []
            clock: int = 0
            inner_clock: int = 0
            last_pid: Optional[str] = None
            proc: Optional[Process] = None
            tick_done: bool = False
            switching: bool = False
            just_dispatched: bool = False
            just_completed: bool = False
            message: str = ""
            throughput: int = 0

            def add_event(event: SchedulingEventSchema):
                nonlocal message
                timeline.append(event)
                message += f" | {event.no_time_str()}"

            def calc_stats() -> dict[str, Any]:
                n = len(completed)
                avg_tat = sum(p.turnaround_time for p in completed) / n
                avg_w = sum(p.waiting_time for p in completed) / n
                cpu_busy = sum(p.burst_time for p in completed)
                ctx_events = sum(1 for e in timeline if e.event == Event.SWITCHING)
                total_time = clock - 1
                cpu_util = cpu_busy / total_time * 100 if total_time else 0

                return {
                    "total_time": total_time,
                    f"cpu_busy_{workload.time_unit}": cpu_busy,
                    f"ctx_swtich_{workload.time_unit}": ctx_events * ctx_switch_cost,
                    "cpu_utilization": round(cpu_util, 2),
                    "avg_turnaround": round(avg_tat, 2),
                    "avg_waiting": round(avg_w, 2),
                    "throughput_at_window": throughput,
                    "throughput_overall": round(n / total_time, 4) if total_time else 0,
                }

            while remaining_procs or ready_queue or proc is not None:
                message = f"[{clock:03}]"
                if clock == 0:
                    add_event(SchedulingEventSchema(time=clock, event=Event.IDLE))

                # ARRIVE
                if not tick_done:
                    while remaining_procs and remaining_procs[0].arrival_time == clock:
                        p = remaining_procs.popleft()
                        ready_queue.append(p)
                        add_event(SchedulingEventSchema(time=clock, event=Event.ARRIVE, ctx=p.pid))

                # RUNNING
                if not tick_done and not switching:
                    if not ready_queue and proc is None and clock != 0:  # no process running and empty queue -> wait for next arrival
                        add_event(SchedulingEventSchema(time=clock, event=Event.IDLE))

                    elif ready_queue and proc is None:  # the queue has processes but none is running -> start switching to the next process
                        proc = ready_queue.popleft()
                        if proc is not None and last_pid == proc.pid:  # dont need context switch
                            inner_clock = quantum  # just restart the quantum
                        else:
                            if just_completed and cost_on_finish:
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
                        add_event(SchedulingEventSchema(time=clock, event=Event.DISPATCH, ctx=proc.pid))
                    inner_clock -= 1
                    proc.remaining_time -= 1
                    add_event(SchedulingEventSchema(time=clock, event=Event.RUNNING, ctx=proc.pid,
                                                   detail=f"{f'(q={inner_clock + 1} → {inner_clock})':<13}  {f'(r={proc.remaining_time + 1} → {proc.remaining_time})':<13}"))
                    end_ev = None
                    if proc.remaining_time == 0:  # cur_proc also finishes on this clock pulse
                        end_ev = SchedulingEventSchema(time=clock, event=Event.FINISH, ctx=proc.pid)
                        last_pid = proc.pid
                        proc.finish_time = clock
                        proc.turnaround_time = proc.finish_time - proc.arrival_time
                        proc.waiting_time = proc.turnaround_time - proc.burst_time
                        completed.append(proc)
                        just_completed = True
                    if inner_clock == 0 and end_ev is None:  # cur_proc is also preempted on this clock pulse
                        end_ev = SchedulingEventSchema(time=clock, event=Event.PREEMPT, ctx=proc.pid,
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
                        add_event(SchedulingEventSchema(time=clock, event=Event.SWITCHING, ctx=f"{last_pid} → {proc.pid}",
                                                       detail=f"{f'(t={inner_clock + 1} → {inner_clock})':<13}"))
                    if inner_clock == 0:
                        just_dispatched = True
                        switching = False
                        inner_clock = quantum

                if clock == throughput_window:
                    throughput = len(completed)
                clock += 1
                tick_done = False
                print(message)

            # return to idle at the end
            if cost_on_finish:
                inner_clock = ctx_switch_cost
                while inner_clock > 0:
                    message = f"[{clock:03}]"
                    inner_clock -= 1
                    add_event(SchedulingEventSchema(time=clock, event=Event.SWITCHING, ctx=f"{last_pid} → {None}",
                                                    detail=f"{f'(t={inner_clock + 1} → {inner_clock})':<13}"))
                    clock += 1
                    print(message)

            message = f"[{clock:03}]"
            add_event(SchedulingEventSchema(time=clock, event=Event.IDLE))
            print(message)

            if clock <= throughput_window:
                throughput = len(completed)

            return {
                "timeline": timeline,
                "processes": completed,
                "stats": calc_stats(),
            }

        results: dict[str, dict[str, Any]] = {}
        for q in scheduling.metadata.rr_quantums or []:
            results[f"{q=}"] = round_robin(
                workload=scheduling.workload,
                quantum=q,
                ctx_switch_cost=scheduling.metadata.context_switch_cost,
                throughput_window=scheduling.metadata.throughput_window_T
            )
        print()
        for key, result in results.items():
            print(f"{key:<5} | {result['stats']=}")
        raise NotImplementedError("Round Robin is not fully implemented yet.")
