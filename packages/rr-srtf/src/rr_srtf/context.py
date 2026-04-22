from logging import Logger
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal

from rr_srtf.utils.file_utils import FileUtils
from rr_srtf.utils.logging_utils import LoggingUtils


class RunContext:
    _instance: Optional["RunContext"] = None

    def __init__(self, challenge_id: str, base_path: Optional[Path] = None, verbose: bool = False):
        self.challenge_id = challenge_id
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_path = base_path
        self.verbose = verbose
        self.figure_file: Path = FileUtils.get_figure_file(challenge_id, self.run_id, base_path)
        self.run_path: Path = FileUtils.get_run_path(challenge_id, self.run_id, base_path)

    @classmethod
    def new_run(cls, challenge_id: str, base_path: Optional[Path] = None, verbose: bool = False) -> "RunContext":
        cls._instance = RunContext(challenge_id, base_path, verbose)
        assert cls._instance is not None
        if not cls._instance.verbose:
            FileUtils.update_latest_symlink(cls._instance.challenge_id, cls._instance.run_id, cls._instance.base_path)
        return cls._instance

    @classmethod
    def current(cls) -> "RunContext":
        if cls._instance is None:
            raise RuntimeError("No active run — call RunContext.new_run() first")
        return cls._instance

    def get_logger(self, alg_name: Literal["RR", "SRTF"], label: str = "") -> Logger:
        return LoggingUtils.get_simulation_logger(
            challenge_id=self.challenge_id,
            algorithm=alg_name,
            run_id=self.run_id,
            label=label,
            log_dir=self.base_path,
            verbose=self.verbose
        )