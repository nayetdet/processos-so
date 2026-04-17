from pydantic import BaseModel, ConfigDict, Field
from rr_srtf.schemas.scheduling.scheduling_metadata_schema import SchedulingMetadataSchema
from rr_srtf.schemas.scheduling.scheduling_workload_schema import SchedulingWorkloadSchema

class SchedulingSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spec_version: str = Field(min_length=1)
    challenge_id: str = Field(min_length=1)
    metadata: SchedulingMetadataSchema
    workload: SchedulingWorkloadSchema
