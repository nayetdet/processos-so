from pydantic import BaseModel, ConfigDict, Field

from rr_srtf.enums.scheduling_timeline_event import SchedulingTimelineEvent
from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState

type SchedulingTimelineEntryType = SchedulingTimelineEvent | SchedulingTimelineState


class SchedulingTimelineEntrySchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    time: int = Field(ge=0)
    type: SchedulingTimelineEntryType
    ctx: str = ""
    detail: str = ""

    def no_time_str(self):
        return f'{f"{self.type.value:<10} [{self.ctx:-^11}]  {'' if self.detail == '' else f'{self.detail}'}":<55}'
