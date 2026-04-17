from typing import Optional, Any
from pydantic import BaseModel, Field

class Process(BaseModel):
    pid: str = Field(min_length=1)
    arrival_time: int = Field(ge=0)
    burst_time: int = Field(gt=0)
    # tracked internally
    remaining_time: int = Field(default=None, init=False)
    start_time: int = Field(default=None, init=False)
    finish_time: int = Field(default=None, init=False)
    waiting_time: int = Field(default=0, init=False)
    turnaround_time: int = Field(default=0, init=False)

    def model_post_init(self, context) -> None:
        self.remaining_time = self.burst_time