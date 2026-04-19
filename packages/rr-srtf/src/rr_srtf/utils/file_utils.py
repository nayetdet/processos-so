import logging
import tempfile
from pathlib import Path
from typing import Optional

class FileUtils:
    @staticmethod
    def get_run_path(challenge_id: str, run_id: str, output_path: Optional[Path] = None) -> Path:
        base: Path = output_path or Path(tempfile.gettempdir())
        run_dir = base / challenge_id / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    @staticmethod
    def get_log_path(challenge_id: str, run_id: str, alg_name: str, output_path: Optional[Path] = None) -> Path:
        base: Path = output_path or Path(tempfile.gettempdir())
        log_path = base / challenge_id / run_id / "logs" / alg_name
        log_path.mkdir(parents=True, exist_ok=True)
        return log_path

    @staticmethod
    def get_figure_path(challenge_id: str, run_id: str, output_path: Optional[Path] = None) -> Path:
        base: Path = output_path or Path(tempfile.gettempdir())
        figure_path = base / challenge_id / run_id / "figures"
        figure_path.mkdir(parents=True, exist_ok=True)
        return figure_path

    @staticmethod
    def get_figure_file(challenge_id: str, run_id: str, output_path: Optional[Path] = None) -> Path:
        figure_dir = FileUtils.get_figure_path(challenge_id, run_id, output_path)
        return figure_dir / f"{challenge_id}-{run_id}.png"

    @staticmethod
    def update_latest_symlink(challenge_id: str, run_id: str, output_path: Optional[Path] = None) -> None:
        base: Path = output_path or Path(tempfile.gettempdir())
        run_dir = base / challenge_id / run_id
        latest_link = base / challenge_id / "latest"

        try:
            if latest_link.is_symlink():
                latest_link.unlink()
            latest_link.symlink_to(run_dir, target_is_directory=True)
        except (OSError, NotImplementedError):
            logging.getLogger(__name__).warning(
                "Could not create 'latest' symlink — skipping. "
                "On Windows, enable Developer Mode to support symlinks."
            )

