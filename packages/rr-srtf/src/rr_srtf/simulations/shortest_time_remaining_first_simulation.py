from typing import List
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_schema import SchedulingTimelineSchema
from rr_srtf.simulations.base_simulation import BaseSimulation

class ShortestTimeRemainingFirstSimulation(BaseSimulation):
    @staticmethod
    def simulate(scheduling: SchedulingSchema) -> List[SchedulingTimelineSchema]:
        raise NotImplementedError("Shortest Time Remaining First Simulation is not implemented yet.")
