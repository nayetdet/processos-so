from pydantic import BaseModel, ConfigDict
from rr_srtf.schemas.scheduling_metrics.scheduling_overhead_metrics import SchedulingOverheadMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_performance_metrics import SchedulingPerformanceMetricsSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_process_metrics import SchedulingProcessMetricsSchema

class SchedulingMetricsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    process: SchedulingProcessMetricsSchema
    performance: SchedulingPerformanceMetricsSchema
    overhead: SchedulingOverheadMetricsSchema
