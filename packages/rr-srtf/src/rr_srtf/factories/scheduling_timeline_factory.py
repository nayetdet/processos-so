from typing import List

from rr_srtf.schemas.scheduling_timeline.scheduling_event_schema import SchedulingEventSchema, Event
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema


class SchedulingTimelineFactory:
    @staticmethod
    def compress_events(
            events: List[SchedulingEventSchema],
    ) -> List[SchedulingTimelineStepSchema]:
        steps: List[SchedulingTimelineStepSchema] = []
        notice_events = (Event.ARRIVE, Event.DISPATCH, Event.FINISH, Event.PREEMPT)
        tick_events = (Event.RUNNING, Event.SWITCHING, Event.IDLE)
        i = 0

        while i < len(events):
            ev: SchedulingEventSchema = events[i]

            if ev.type in tick_events:
                inside_steps: List[SchedulingTimelineStepSchema] = []
                j = i + 1
                last_tick_idx = i
                while j < len(events):
                    cur: SchedulingEventSchema = events[j]
                    if cur.type == ev.type and cur.ctx == ev.ctx:
                        last_tick_idx = j
                        j += 1
                    elif cur.type in notice_events:
                        # Zero-cost event interspersed — skip it, don't break the merge
                        inside_steps.append(SchedulingTimelineStepSchema(
                            event=cur.type,
                            ctx=cur.ctx,
                            start=cur.time,
                            end=cur.time,
                        ))
                        j += 1
                    else:
                        break
                steps.append(SchedulingTimelineStepSchema(
                    event=ev.type,
                    ctx=ev.ctx,
                    start=ev.time,
                    end=events[last_tick_idx].time + 1,
                ))
                # steps.extend(inside_steps)
                i = j

            else:
                steps.append(SchedulingTimelineStepSchema(
                    event=ev.type,
                    ctx=ev.ctx,
                    start=ev.time,
                    end=ev.time,
                ))
                i += 1

        return steps
