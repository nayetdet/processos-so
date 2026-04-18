from pathlib import Path
from typing import List
from rr_srtf.factories.scheduling_figure_factory import SchedulingFigureFactory
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema

class FigureUtils:
    @staticmethod
    def save_scheduling_figure(
        scheduling: SchedulingSchema,
        scheduling_timelines: List[SchedulingTimelineSchema],
        figure_path: Path,
    ) -> None:
        figure = SchedulingFigureFactory.plot([(scheduling, scheduling_timelines)])
        figure.savefig(figure_path)
        figure.clear()
