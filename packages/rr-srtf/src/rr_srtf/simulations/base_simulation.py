from abc import ABC, abstractmethod
from typing import List
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema

class BaseSimulation(ABC):
    @staticmethod
    @abstractmethod
    def simulate(scheduling: SchedulingSchema) -> List[SchedulingTimelineSchema]:
        pass
