from typing import List, Literal, Optional, Self
from pydantic import BaseModel, ConfigDict, Field, model_validator

class SchedulingMetadataSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    context_switch_cost: int = Field(ge=0)
    throughput_window_T: int = Field(gt=0)
    algorithms: List[Literal["RR", "SRTF"]] = Field(min_length=1)
    rr_quantums: Optional[List[int]] = None

    @model_validator(mode="after")
    def validate_metadata(self) -> Self:
        if len(set(self.algorithms)) != len(self.algorithms):
            raise ValueError("algorithms must not contain duplicates")

        if "RR" in self.algorithms:
            if not self.rr_quantums:
                raise ValueError("rr_quantums is required when RR is enabled")
            if any(quantum <= 0 for quantum in self.rr_quantums):
                raise ValueError("rr_quantums must contain only positive integers")
            if len(set(self.rr_quantums)) != len(self.rr_quantums):
                raise ValueError("rr_quantums must not contain duplicates")

        return self
