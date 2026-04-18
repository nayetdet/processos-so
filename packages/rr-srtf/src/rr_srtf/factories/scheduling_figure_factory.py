import os
import tempfile
from typing import Dict, List, Tuple

os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema

class SchedulingFigureFactory:
    MIN_FIGURE_WIDTH: float = 10.0
    MAX_FIGURE_WIDTH: float = 20.0
    BASE_FIGURE_HEIGHT: float = 2.4
    ARRIVAL_STRIP_HEIGHT: float = 1.1
    ROW_HEIGHT: float = 1.0
    BAR_HEIGHT: float = 0.7

    @staticmethod
    def plot(schedulings: List[Tuple[SchedulingSchema, List[SchedulingTimelineSchema]]]) -> Figure:
        total_rows: int = sum(len(scheduling_timelines) for _, scheduling_timelines in schedulings)
        max_time: int = max(
            (
                step.end
                for _, scheduling_timelines in schedulings
                for scheduling_timeline in scheduling_timelines
                for step in scheduling_timeline.steps
            ),
            default=0,
        )

        fig, (arrival_ax, timeline_ax) = plt.subplots(
            nrows=2,
            ncols=1,
            sharex=True,
            figsize=SchedulingFigureFactory.__get_figure_size(total_rows, max_time),
            layout="constrained",
            gridspec_kw={
                "height_ratios": [SchedulingFigureFactory.ARRIVAL_STRIP_HEIGHT, max(total_rows, 1)],
            },
        )

        fig.patch.set_facecolor("#f8fafc")
        arrival_ax.set_facecolor("#f8fafc")
        timeline_ax.set_facecolor("#ffffff")

        yticks: List[int] = []
        yticklabels: List[str] = []
        colors_by_pid = SchedulingFigureFactory.__get_colors_by_pid(schedulings)
        row_index: int = 0

        challenge_ids = {scheduling.challenge_id for scheduling, _ in schedulings}
        show_challenge_id_in_row_label = len(challenge_ids) > 1

        for scheduling, scheduling_timelines in schedulings:
            for scheduling_timeline in scheduling_timelines:
                yticks.append(row_index)
                yticklabels.append(
                    SchedulingFigureFactory.__get_row_label(
                        scheduling=scheduling,
                        scheduling_timeline=scheduling_timeline,
                        show_challenge_id=show_challenge_id_in_row_label,
                    )
                )

                for step in scheduling_timeline.steps:
                    SchedulingFigureFactory.__plot_step(
                        ax=timeline_ax,
                        row_index=row_index,
                        pid=step.pid,
                        start=step.start,
                        end=step.end,
                        color=colors_by_pid.get(step.pid),
                    )

                row_index += 1

        figure_title = SchedulingFigureFactory.__get_figure_title(schedulings)
        fig.suptitle(
            figure_title,
            fontsize=14,
            fontweight="bold",
        )

        SchedulingFigureFactory.__style_timeline_axis(
            ax=timeline_ax,
            yticks=yticks,
            yticklabels=yticklabels,
            schedulings=schedulings,
            max_time=max_time,
            total_rows=total_rows,
        )

        SchedulingFigureFactory.__style_arrivals_axis(
            ax=arrival_ax,
        )

        SchedulingFigureFactory.__plot_arrivals(
            ax=arrival_ax,
            schedulings=schedulings,
            colors_by_pid=colors_by_pid,
            show_challenge_id=show_challenge_id_in_row_label,
        )

        if colors_by_pid:
            legend_handles = [
                Line2D(
                    [],
                    [],
                    marker="o",
                    linestyle="None",
                    markerfacecolor=color,
                    markeredgecolor="#1f2933",
                    markeredgewidth=0.6,
                    markersize=8,
                    label=pid,
                )
                for pid, color in colors_by_pid.items()
            ]
            fig.legend(
                handles=legend_handles,
                loc="upper center",
                bbox_to_anchor=(0.5, 0.965),
                ncol=min(6, len(legend_handles)),
                frameon=False,
                fontsize=9,
                handletextpad=0.4,
                columnspacing=1.2,
            )

        return fig

    @staticmethod
    def __get_figure_size(total_rows: int, max_time: int) -> Tuple[float, float]:
        width = min(
            SchedulingFigureFactory.MAX_FIGURE_WIDTH,
            max(SchedulingFigureFactory.MIN_FIGURE_WIDTH, 4.0 + max_time * 0.35),
        )

        height = max(
            SchedulingFigureFactory.BASE_FIGURE_HEIGHT + SchedulingFigureFactory.ARRIVAL_STRIP_HEIGHT,
            1.6 + total_rows * SchedulingFigureFactory.ROW_HEIGHT + SchedulingFigureFactory.ARRIVAL_STRIP_HEIGHT,
        )

        return (width, height)

    @staticmethod
    def __get_figure_title(schedulings: List[Tuple[SchedulingSchema, List[SchedulingTimelineSchema]]]) -> str:
        challenge_ids = {scheduling.challenge_id for scheduling, _ in schedulings}
        if len(challenge_ids) == 1:
            return next(iter(challenge_ids))
        return "Scheduling Comparison"

    @staticmethod
    def __get_colors_by_pid(schedulings: List[Tuple[SchedulingSchema, List[SchedulingTimelineSchema]]]) -> Dict[str, Tuple[float, float, float, float]]:
        pids: List[str] = []
        seen_pids: set[str] = set()

        for scheduling, _ in schedulings:
            for process in scheduling.workload.processes:
                if process.pid in seen_pids:
                    continue
                seen_pids.add(process.pid)
                pids.append(process.pid)

        colormap = plt.get_cmap("tab20", max(len(pids), 1))
        return {
            pid: colormap(index)
            for index, pid in enumerate(pids)
        }

    @staticmethod
    def __get_row_label(
        scheduling: SchedulingSchema,
        scheduling_timeline: SchedulingTimelineSchema,
        show_challenge_id: bool,
    ) -> str:
        algorithm_label = scheduling_timeline.algorithm
        if scheduling_timeline.algorithm == "RR":
            algorithm_label = f"RR (q={scheduling_timeline.quantum})"

        if show_challenge_id:
            return f"{scheduling.challenge_id} | {algorithm_label}"
        return algorithm_label

    @staticmethod
    def __plot_step(
        ax: Axes,
        row_index: int,
        pid: str,
        start: int,
        end: int,
        color: Tuple[float, float, float, float] | None,
    ) -> None:
        duration: int = end - start
        bar_color = color or "#64748b"
        ax.barh(
            y=row_index,
            width=duration,
            left=start,
            height=SchedulingFigureFactory.BAR_HEIGHT,
            align="center",
            color=bar_color,
            edgecolor="#1f2933",
            linewidth=0.8,
        )

        label_rotation: int = 0
        label_font_size: int = 9
        if duration < 2:
            label_rotation = 90
            label_font_size = 7

        ax.text(
            x=start + duration / 2,
            y=row_index,
            s=pid,
            ha="center",
            va="center",
            color="#ffffff",
            fontsize=label_font_size,
            fontweight="bold",
            rotation=label_rotation,
            clip_on=True,
        )

    @staticmethod
    def __style_timeline_axis(
        ax: Axes,
        yticks: List[int],
        yticklabels: List[str],
        schedulings: List[Tuple[SchedulingSchema, List[SchedulingTimelineSchema]]],
        max_time: int,
        total_rows: int,
    ) -> None:
        time_units = {scheduling.workload.time_unit for scheduling, _ in schedulings}
        ax.set_xlabel(
            f"Time ({next(iter(time_units))})" if len(time_units) == 1 else "Time",
            fontsize=11,
        )

        ax.set_ylabel("Algorithm", fontsize=11)
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticklabels)
        ax.set_xlim(0, max(max_time, 1))
        ax.set_ylim(max(total_rows - 0.35, 0.65), -0.65)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.grid(axis="x", linestyle="--", linewidth=0.7, color="#cbd5e1")
        ax.tick_params(axis="y", length=0)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    @staticmethod
    def __style_arrivals_axis(ax: Axes) -> None:
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.tick_params(axis="x", bottom=False, labelbottom=False)
        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.axhline(
            y=0.18,
            color="#cbd5e1",
            linewidth=1.0,
        )
        ax.text(
            0.0,
            0.92,
            "Arrivals",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=10,
            fontweight="bold",
            color="#334155",
        )

    @staticmethod
    def __plot_arrivals(
        ax: Axes,
        schedulings: List[Tuple[SchedulingSchema, List[SchedulingTimelineSchema]]],
        colors_by_pid: Dict[str, Tuple[float, float, float, float]],
        show_challenge_id: bool,
    ) -> None:
        level_by_arrival_count: List[float] = [0.42, 0.62, 0.82]
        stacked_arrivals_by_time: Dict[int, int] = {}

        for scheduling, _ in schedulings:
            for process in scheduling.workload.processes:
                color = colors_by_pid.get(process.pid, "#64748b")
                label = process.pid
                if show_challenge_id:
                    label = f"{scheduling.challenge_id}:{process.pid}"

                stacked_index = stacked_arrivals_by_time.get(process.arrival_time, 0)
                stacked_arrivals_by_time[process.arrival_time] = stacked_index + 1
                arrival_level = level_by_arrival_count[stacked_index % len(level_by_arrival_count)]

                ax.vlines(
                    x=process.arrival_time,
                    ymin=0.18,
                    ymax=arrival_level - 0.05,
                    colors=[color],
                    linewidth=1.1,
                    alpha=0.8,
                    zorder=1,
                )
                ax.scatter(
                    process.arrival_time,
                    arrival_level,
                    color=[color],
                    marker="o",
                    s=42,
                    edgecolors="#1f2933",
                    linewidths=0.5,
                    zorder=3,
                )
                ax.text(
                    x=process.arrival_time,
                    y=arrival_level + 0.08,
                    s=label,
                    ha="center",
                    va="bottom",
                    color=color,
                    fontsize=8,
                    fontweight="bold",
                )
