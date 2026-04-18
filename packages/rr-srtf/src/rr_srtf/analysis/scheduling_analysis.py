from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema

class SchedulingAnalysis:
    @staticmethod
    def analyze_metrics(timelines: SchedulingTimelineSchema) -> SchedulingMetricsSchema:
        pass
