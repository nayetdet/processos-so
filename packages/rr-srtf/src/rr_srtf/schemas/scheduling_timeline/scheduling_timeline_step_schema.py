from typing import Any, Literal, Callable

from pydantic import BaseModel, ConfigDict, Field
from pydantic.main import IncEx

from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_entry_schema import SchedulingTimelineEntryType

class SchedulingTimelineStepSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    type: SchedulingTimelineEntryType
    ctx: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)