from typing import List

from pydantic import BaseModel, ConfigDict

from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_entry_schema import SchedulingTimelineEntrySchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema


class SchedulingResultSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    entry_timeline: List[SchedulingTimelineEntrySchema]
    timeline: SchedulingTimelineSchema
    metrics: SchedulingMetricsSchema
