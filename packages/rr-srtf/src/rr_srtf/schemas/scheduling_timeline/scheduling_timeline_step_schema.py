from pydantic import BaseModel, ConfigDict, Field
from rr_srtf.enums.scheduling_timeline_step_state import SchedulingTimelineStepState

class SchedulingTimelineStepSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: SchedulingTimelineStepState
    pid: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
