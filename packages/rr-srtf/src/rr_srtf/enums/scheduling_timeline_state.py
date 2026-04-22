from enum import Enum, StrEnum


class SchedulingTimelineState(StrEnum):
    RUNNING = 'RUNNING'
    READY = 'READY'
    WAITING = 'WAITING'
    SWITCHING = 'SWITCHING'
