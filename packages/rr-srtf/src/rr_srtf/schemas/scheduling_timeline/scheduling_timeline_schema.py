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

        return self
