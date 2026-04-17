from enum import Enum
from pydantic import BaseModel, ConfigDict, Field

class Event(Enum):
    IDLE = 'IDLE'
    ARRIVE = 'ARRIVE'
    RUNNING = 'RUNNING'
    SWITCHING = 'SWITCHING'
    COMPLETED = 'COMPLETED'
    PREEMPT = 'PREEMPT'
    DISPATCHED = 'DISPATCHED'

class SchedulingEventSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    time: int = Field(ge=0)
    event: Event
    ctx: str = ""
    detail: str = ""

    def no_time_str(self):
        return f'{f"{self.event:<10} [{self.ctx:-^11}]  {'' if self.detail == '' else f'{self.detail}'}":<55}'