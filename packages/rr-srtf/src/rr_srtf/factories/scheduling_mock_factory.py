from random import Random
from typing import List, Tuple, Literal
from rr_srtf.schemas.scheduling.scheduling_schema import SchedulingSchema
from rr_srtf.schemas.scheduling.scheduling_workload_schema import SchedulingWorkloadSchema
from rr_srtf.schemas.scheduling.scheduling_workload_process_schema import SchedulingWorkloadProcessSchema
from rr_srtf.schemas.scheduling.scheduling_metadata_schema import SchedulingMetadataSchema

class SchedulingMockFactory:
    SEED: int = 0

    SCHEDULING_SPEC_VERSION: str = "1.0"
    SCHEDULING_CHALLENGE_ID: str = "rr_srtf_preemptivo_demo"

    METADATA_CONTEXT_SWITCH_COST: int = 1
    METADATA_THROUGHPUT_WINDOW_T: int = 100
    METADATA_ALGORITHMS: List[Literal["RR", "SRTF"]] = ["RR", "SRTF"]
    METADATA_RR_QUANTUMS: List[int] = [1, 2, 4, 8, 16]

    WORKLOAD_TIME_UNIT: str = "ticks"
    WORKLOAD_PROCESS_COUNT: int = 5
    WORKLOAD_ARRIVAL_TIME_RANGE: Tuple[int, int] = (0, 12)
    WORKLOAD_SHORT_BURST_RANGE: Tuple[int, int] = (1, 5)
    WORKLOAD_LONG_BURST_RANGE: Tuple[int, int] = (20, 30)

    @classmethod
    def mock(cls) -> SchedulingSchema:
        rng: Random = Random(cls.SEED)
        arrivals: List[int] = cls.__mock_arrivals(rng)
        bursts: List[int] = cls.__mock_bursts(rng)

        return SchedulingSchema(
            spec_version=cls.SCHEDULING_SPEC_VERSION,
            challenge_id=cls.SCHEDULING_CHALLENGE_ID,
            metadata=cls.__mock_metadata(),
            workload=SchedulingWorkloadSchema(
                time_unit=cls.WORKLOAD_TIME_UNIT,
                processes=[
                    SchedulingWorkloadProcessSchema(
                        pid=f"P{index:02d}",
                        arrival_time=arrival_time,
                        burst_time=burst_time
                    )
                    for index, (arrival_time, burst_time) in enumerate(
                        zip(arrivals, bursts),
                        start=1
                    )
                ]
            )
        )

    @classmethod
    def __mock_metadata(cls) -> SchedulingMetadataSchema:
        return SchedulingMetadataSchema(
            context_switch_cost=cls.METADATA_CONTEXT_SWITCH_COST,
            throughput_window_T=cls.METADATA_THROUGHPUT_WINDOW_T,
            algorithms=cls.METADATA_ALGORITHMS,
            rr_quantums=cls.METADATA_RR_QUANTUMS,
        )

    @classmethod
    def __mock_arrivals(cls, rng: Random) -> List[int]:
        start, end = cls.WORKLOAD_ARRIVAL_TIME_RANGE
        return sorted(rng.sample(range(start, end + 1), k=cls.WORKLOAD_PROCESS_COUNT))

    @classmethod
    def __mock_bursts(cls, rng: Random) -> List[int]:
        shorts: int = (cls.WORKLOAD_PROCESS_COUNT + 1) // 2
        longs: int = cls.WORKLOAD_PROCESS_COUNT - shorts
        burst_times: List[int] = [
            *(rng.randint(*cls.WORKLOAD_SHORT_BURST_RANGE) for _ in range(shorts)),
            *(rng.randint(*cls.WORKLOAD_LONG_BURST_RANGE) for _ in range(longs))
        ]

        rng.shuffle(burst_times)
        return burst_times
