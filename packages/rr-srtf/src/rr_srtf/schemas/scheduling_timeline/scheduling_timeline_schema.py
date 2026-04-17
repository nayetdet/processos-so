from pydantic import BaseModel, ConfigDict, Field

class SchedulingTimelineSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pid: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
