import logging
from pathlib import Path
from typing import Optional, Literal, List

from rr_srtf.enums.scheduling_timeline_event import SchedulingTimelineEvent
from rr_srtf.enums.scheduling_timeline_state import SchedulingTimelineState
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.utils.file_utils import FileUtils


class LoggingUtils:
    @staticmethod
    def get_simulation_logger(
        challenge_id: str,
        run_id: str,
        algorithm: Literal["RR", "SRTF"],
        label: str = "",
        log_dir: Optional[Path] = None,
        verbose: bool = False
    ) -> logging.Logger:
        if not verbose:
            return logging.getLogger("null")

        algo_dir = FileUtils.get_log_path(challenge_id, run_id, algorithm.lower(), log_dir)

        suffix = f"_{label}" if label else ""
        log_file = algo_dir / f"{algorithm.lower()}{suffix}_{run_id}.log"

        logger = logging.getLogger(f"simulations.{algorithm.lower()}{suffix}")
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()
        logger.addHandler(logging.FileHandler(log_file, mode="w"))
        logger.addHandler(logging.StreamHandler())
        return logger

    @staticmethod
    def get_log_part(
        event: SchedulingTimelineState | SchedulingTimelineEvent,
        pid: str = "",
        detail: str = ""
    ) -> str:
        event_pid: str = f"{event.value:<8}   [{pid}]" if pid != "" else f"{event.value}"
        return f"{f"{event_pid:<16}  {"" if detail == "" else f'{detail}'}":<45}"

    @staticmethod
    def flush_log_header(logger: logging.Logger, message: str, processes: List[SchedulingWorkloadProcessSchema]) -> None:
        logger.info("=" * 60)
        logger.info(message)
        logger.info(f"Processes: {[(p.pid, p.arrival_time, p.burst_time) for p in processes]}")
        logger.info("=" * 60)

    @staticmethod
    def flush_log_parts(logger: logging.Logger, parts: List[str]) -> None:
        logger.debug(" | ".join(parts))