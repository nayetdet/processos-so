from itertools import pairwise
from typing import List, Literal, Optional, Self
from pydantic import BaseModel, ConfigDict, Field, model_validator
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_step_schema import SchedulingTimelineStepSchema

class SchedulingTimelineSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    algorithm: Literal["RR", "SRTF"]
    quantum: Optional[int] = Field(default=None, gt=0)
    steps: List[SchedulingTimelineStepSchema] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_timeline(self) -> Self:
        if self.algorithm == "RR" and self.quantum is None:
            raise ValueError("quantum must be provided for RR algorithm")
        if self.algorithm == "SRTF" and self.quantum is not None:
            raise ValueError("quantum must not be provided for SRTF algorithm")

        for index, step in enumerate(self.steps):
            if step.end <= step.start:
                raise ValueError(f"steps[{index}] must have end greater than start")

        for previous_step, current_step in pairwise(self.steps):
            if current_step.start < previous_step.end:
                raise ValueError("steps must be ordered by start time and must not overlap")

        return self
