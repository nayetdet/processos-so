from rr_srtf.schemas.scheduling_timeline.scheduling_timeline_entry_schema import SchedulingTimelineEntrySchema


class SimulationTimeline:
    def __init__(self) -> None:
        self._entries: list[SchedulingTimelineEntrySchema] = []
        self._parts: list[str] = []

    def add_entry(self, entry: SchedulingTimelineEntrySchema) -> None:
        self._entries.append(entry)
        self._parts.append(entry.no_time_str())

    def begin_tick(self, clock: int) -> None:
        self._parts = [f"[{clock:03}]"]

    def flush_parts(self) -> str:
        return " | ".join(self._parts)

    @property
    def entries(self) -> list[SchedulingTimelineEntrySchema]:
        return list(self._entries)