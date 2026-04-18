import json
from pathlib import Path
from typing import Dict, Optional, Any
from rr_srtf.factories.scheduling_mock_factory import SchedulingMockFactory
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema

class SchedulingParseUtils:
    @classmethod
    def parse(cls, path: Optional[Path]) -> SchedulingSchema:
        if path is None:
            return SchedulingMockFactory.mock()
        with path.open("r", encoding="utf-8") as file:
            payload: Dict[str, Any] = json.load(file)
        return SchedulingSchema.model_validate(payload)
