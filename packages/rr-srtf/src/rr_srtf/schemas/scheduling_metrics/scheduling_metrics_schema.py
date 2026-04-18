from pydantic import BaseModel, ConfigDict, Field

from rr_srtf.schemas.scheduling_metrics.scheduling_process_metrics_schema import SchedulingProcessMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_system_metrics_schema import SchedulingSystemMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_overhead_metrics_schema import SchedulingOverheadMetricsSchema


class SchedulingMetricsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    aggregate: SchedulingProcessMetricsSchema
    system: SchedulingSystemMetricsSchema
    overhead: SchedulingOverheadMetricsSchema
