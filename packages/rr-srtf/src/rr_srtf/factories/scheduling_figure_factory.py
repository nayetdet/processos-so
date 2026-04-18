import matplotlib
import matplotlib.pyplot as plt
from typing import List, Tuple
from matplotlib.figure import Figure
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema

matplotlib.use("Agg")

class SchedulingFigureFactory:
    @staticmethod
    def plot(schedulings: List[Tuple[SchedulingSchema, List[SchedulingTimelineSchema]]]) -> Figure:
        fig, ax = plt.subplots()

        yticks: List[int] = []
        yticklabels: List[str] = []
        row_index: int = 0
        for scheduling, scheduling_timelines in schedulings:
            for scheduling_timeline in scheduling_timelines:
                yticks.append(row_index)
                if scheduling_timeline.algorithm == "RR":
                    yticklabels.append(f"{scheduling.challenge_id} | RR (q={scheduling_timeline.quantum})")
                else:
                    yticklabels.append(f"{scheduling.challenge_id} | {scheduling_timeline.algorithm}")

                for step in scheduling_timeline.steps:
                    duration: int = step.end - step.start
                    ax.barh(
                        y=row_index,
                        width=duration,
                        left=step.start,
                        align="center",
                    )

                    ax.text(
                        x=step.start + duration / 2,
                        y=row_index,
                        s=step.pid,
                        ha="center",
                        va="center",
                    )

                row_index += 1

        ax.set_xlabel("Time")
        ax.set_ylabel("Executions")
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels)
        plt.tight_layout()

        return fig
