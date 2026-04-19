from typing import List

from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_entry_schema import SchedulingTimelineEntrySchema
from rr_srtf.enums.scheduling_timeline_event import SchedulingTimelineEvent
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema


class SchedulingTimelineFactory:
    @classmethod
    def compress_events(
            cls,
            events: List[SchedulingTimelineEntrySchema],
            detailed: bool = False
    ) -> List[SchedulingTimelineStepSchema]:
        steps: List[SchedulingTimelineStepSchema] = []
        i = 0

        while i < len(events):
            ev: SchedulingTimelineEntrySchema = events[i]

            if not isinstance(ev.type, SchedulingTimelineState):
                if detailed:
                    steps.append(cls.__make_zero_cost_step(ev))
                i += 1
                continue

            inside_steps: List[SchedulingTimelineStepSchema] = []
            j = i + 1
            last_tick_idx = i
            while j < len(events):
                cur: SchedulingTimelineEntrySchema = events[j]
                if cur.type == ev.type and cur.ctx == ev.ctx:
                    last_tick_idx = j
                elif isinstance(cur.type, SchedulingTimelineEvent) and detailed:
                    # Zero-cost event interspersed — skip it, don't break the merge
                    inside_steps.append(cls.__make_zero_cost_step(cur))
                else:
                    break
                j += 1
            steps.append(SchedulingTimelineStepSchema(
                type=ev.type,
                ctx=ev.ctx,
                start=ev.time,
                end=events[last_tick_idx].time + 1,
            ))
            if detailed:
                steps.extend(inside_steps)
            i = j

        return steps

    @staticmethod
    def __make_zero_cost_step(ev: SchedulingTimelineEntrySchema) -> SchedulingTimelineStepSchema:
        point = ev.time if ev.type in (SchedulingTimelineEvent.ARRIVE, SchedulingTimelineEvent.DISPATCH) else ev.time + 1
        return SchedulingTimelineStepSchema(
            type=ev.type,
            ctx=ev.ctx,
            start=point,
            end=point,
        )
