from pathlib import Path
from typing import Any, Dict, List, Optional
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema

class SchedulingReportFactory:
    @staticmethod
    def build(
        scheduling: SchedulingSchema,
        scheduling_timelines: List[SchedulingTimelineSchema],
        scheduling_metrics: List[SchedulingMetricsSchema],
        result_path: Path,
        source: Optional[Path] = None
    ) -> Dict[str, Any]:
        return {
            "source": str(source) if source is not None else "mock",
            "challenge_id": scheduling.challenge_id,
            "result_path": str(result_path),
            "simulations": [
                {
                    "timeline": timeline.model_dump(),
                    "metrics": metrics.model_dump(),
                }
                for timeline, metrics in zip(scheduling_timelines, scheduling_metrics)
            ],
        }
