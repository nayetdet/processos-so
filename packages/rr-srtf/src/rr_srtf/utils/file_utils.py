import tempfile
from pathlib import Path
from typing import Optional

class FileUtils:
    @staticmethod
    def get_figure_path(challenge_id: str, output_path: Optional[Path]) -> Path:
        figure_path: Path = output_path or Path(
            tempfile.NamedTemporaryFile(
                prefix=f"{challenge_id}-",
                suffix=".png",
                delete=False
            ).name
        )

        figure_path.parent.mkdir(parents=True, exist_ok=True)
        return figure_path
