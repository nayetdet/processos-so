from pydantic import BaseModel, ConfigDict, computed_field
from typing import List

from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema


class SimulationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    processes: List[SchedulingWorkloadProcessSchema]
    ctx_switch_cost: int
    throughput_window: int
    instant_start: bool = True
    ctx_switch_on_finish: bool = True
    sched_decision_cost: int = 0

    @computed_field
    @property
    def nb_processes(self) -> int:
        return len(self.processes)

    @classmethod
    def from_schema(cls, scheduling: SchedulingSchema, **overrides) -> "SimulationConfig":
        return cls(
            processes=scheduling.workload.processes,
            ctx_switch_cost=scheduling.metadata.context_switch_cost,
            throughput_window=scheduling.metadata.throughput_window_T,
            **overrides,
        )

    @classmethod
    def for_srtf(cls, scheduling: SchedulingSchema, **overrides) -> "SimulationConfig":
        if "SRTF" not in scheduling.metadata.algorithms:
            raise ValueError("SRTF not listed in schema algorithms")
        return cls.from_schema(scheduling, **overrides)

    @classmethod
    def for_rr_variants(cls, scheduling: SchedulingSchema, **overrides) -> list[tuple[int, "SimulationConfig"]]:
        if "RR" not in scheduling.metadata.algorithms:
            raise ValueError("RR not listed in schema algorithms")
        return [
            (q, cls.from_schema(scheduling, **overrides))
            for q in scheduling.metadata.rr_quantums
        ]