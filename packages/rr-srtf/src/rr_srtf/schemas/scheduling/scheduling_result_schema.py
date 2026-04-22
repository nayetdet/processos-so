from pydantic import BaseModel, ConfigDict

from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema


class SchedulingResultSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    timeline: SchedulingTimelineSchema
    metrics: SchedulingMetricsSchema