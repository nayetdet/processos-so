from pydantic import BaseModel, ConfigDict

from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.schemas.scheduling_runtime.simulation_context import SimulationContext


class SchedulingResultSchema(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    final_context: SimulationContext
    timeline: SchedulingTimelineSchema
    metrics: SchedulingMetricsSchema

