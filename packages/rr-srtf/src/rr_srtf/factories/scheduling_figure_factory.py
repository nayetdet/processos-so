import matplotlib
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from typing import Tuple, List
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema

matplotlib.use("Agg")

class SchedulingFigureFactory:
    @staticmethod
    def plot(schedulings: List[Tuple[SchedulingSchema, List[SchedulingTimelineSchema]]]) -> Figure:
        fig, ax = plt.subplots()

        yticks: List[int] = []
        yticklabels: List[str] = []
        for i, (scheduling, scheduling_timelines) in enumerate(schedulings):
            yticks.append(i)
            yticklabels.append(scheduling.challenge_id)

            for scheduling_timeline in scheduling_timelines:
                duration: int = scheduling_timeline.end - scheduling_timeline.start
                ax.barh(
                    y=i,
                    width=duration,
                    left=scheduling_timeline.start,
                    align="center"
                )

                ax.text(
                    x=scheduling_timeline.start + duration / 2,
                    y=i,
                    s=scheduling_timeline.pid,
                    ha="center",
                    va="center"
                )

        ax.set_xlabel("Time")
        ax.set_ylabel("Executions")
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels)
        plt.tight_layout()

        return fig
