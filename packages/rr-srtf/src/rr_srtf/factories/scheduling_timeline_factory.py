from typing import List

from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_entry_schema import SchedulingTimelineEntrySchema
from rr_srtf.enums.scheduling_timeline_event import SchedulingTimelineEvent
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema


class SchedulingTimelineFactory:
    @classmethod
    def timeline_from_entries(
            cls,
            events: List[SchedulingTimelineEntrySchema],
            detailed: bool = False,
            only_running: bool = True
    ) -> List[SchedulingTimelineStepSchema]:
        steps: List[SchedulingTimelineStepSchema] = []
        i = 0

        while i < len(events):
            ev: SchedulingTimelineEntrySchema = events[i]

            if not isinstance(ev.type, SchedulingTimelineState):
                steps.extend([cls.__make_zero_cost_step(ev)] if detailed else [])
                i += 1
                continue

            inside_steps: List[SchedulingTimelineStepSchema] = []
            j = i + 1
            last_tick_idx = i
            while j < len(events):
                cur: SchedulingTimelineEntrySchema = events[j]
                if cur.type == ev.type and cur.ctx == ev.ctx:
                    last_tick_idx = j
                    j += 1
                elif isinstance(cur.type, SchedulingTimelineEvent):
                    # Zero-cost event interspersed — skip it, don't break the merge
                    if detailed:
                        inside_steps.append(cls.__make_zero_cost_step(cur))
                    j += 1
                else:
                    break
            if not only_running or ev.type == SchedulingTimelineState.RUNNING:
                steps.append(SchedulingTimelineStepSchema(
                    type=ev.type,
                    ctx=ev.ctx,
                    start=ev.time,
                    end=events[last_tick_idx].time + 1,
                ))
            steps.extend(inside_steps if detailed else [])
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
