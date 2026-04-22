import json
import typer
from pathlib import Path
from typing import List, Optional
from pydantic import ValidationError

from rr_srtf.schemas.scheduling.scheduling_result_schema import SchedulingResultSchema
from rr_srtf.schemas.scheduling_metrics.scheduling_metrics import SchedulingMetricsSchema
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.analysis.scheduling_analysis import SchedulingAnalysis
from rr_srtf.factories.scheduling_report_factory import SchedulingReportFactory
from rr_srtf.simulations.round_robin_simulation import RoundRobinSimulation
from rr_srtf.simulations.shortest_remaining_time_first_simulation import ShortestRemainingTimeFirstSimulation
from rr_srtf.utils.figure_utils import FigureUtils
from rr_srtf.utils.file_utils import FileUtils
from rr_srtf.utils.scheduling_parse_utils import SchedulingParseUtils

def main(
    input_path: Optional[Path] = typer.Argument(
        default=None,
        exists=True,
        dir_okay=False,
        file_okay=True,
        readable=True,
        resolve_path=True,
        help="Scheduling JSON file. Uses the mock workload when omitted.",
    ),
    output_figure_path: Optional[Path] = typer.Option(
        None,
        "--output-figure",
        "-o",
        dir_okay=False,
        file_okay=True,
        writable=True,
        resolve_path=True,
        help="Path to save the generated figure.",
    ),
    show_figure: bool = typer.Option(
        True,
        "--show/--no-show",
        help="Open the generated figure in the default viewer.",
    ),
) -> None:
    try:
        scheduling: SchedulingSchema = SchedulingParseUtils.parse(input_path)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Invalid JSON in {input_path}: {exc.msg}") from exc
    except ValidationError as exc:
        raise typer.BadParameter(f"Invalid scheduling in {input_path}: {exc}") from exc
    except OSError as exc:
        raise typer.BadParameter(f"Could not read {input_path}: {exc}") from exc

    scheduling_results: List[SchedulingResultSchema] = []
    if "RR" in scheduling.metadata.algorithms:
        scheduling_results.extend(RoundRobinSimulation.simulate(scheduling))
    if "SRTF" in scheduling.metadata.algorithms:
        scheduling_results.extend(ShortestRemainingTimeFirstSimulation.simulate(scheduling))

    figure_path: Path = FileUtils.get_figure_path(scheduling.challenge_id, output_figure_path)
    FigureUtils.save_scheduling_figure(
        scheduling=scheduling,
        scheduling_timelines=[sr.timeline for sr in scheduling_results],
        figure_path=figure_path
    )

    report = SchedulingReportFactory.build(
        scheduling=scheduling,
        scheduling_timelines=[sr.timeline for sr in scheduling_results],
        scheduling_metrics=[sr.metrics for sr in scheduling_results],
        figure_path=figure_path,
        source=input_path,
    )

    typer.echo(json.dumps(report, indent=2, ensure_ascii=False))
    if show_figure and typer.launch(str(figure_path)) != 0:
        typer.echo(
            f"Could not open the figure automatically. File saved at: {figure_path}",
            err=True,
        )
