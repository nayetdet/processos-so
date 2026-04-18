from functools import cache, cached_property
from typing import List

from pydantic import BaseModel, ConfigDict, computed_field

from rr_srtf.factories.scheduling_timeline_factory import SchedulingTimelineFactory
from rr_srtf.models.process_model import ProcessModel
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics_schema import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_event_schema import SchedulingEventSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema


class SchedulingResultSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    timeline: List[SchedulingEventSchema]
    processes: List[ProcessModel]
    stats: SchedulingMetricsSchema

    @computed_field(repr=False)
    @property # maybe with cache
    def compressed_timeline(self) -> List[SchedulingTimelineStepSchema]:
        return SchedulingTimelineFactory.compress_events(self.timeline)
