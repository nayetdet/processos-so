import logging
from pathlib import Path
from typing import Optional, Literal

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