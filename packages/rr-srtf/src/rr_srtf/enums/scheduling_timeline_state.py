from enum import StrEnum


class SchedulingTimelineState(StrEnum):
    IDLE = 'IDLE'
    RUNNING = 'RUNNING'
    READY = 'READY'
    WAITING = 'WAITING'
    SWITCHING = 'SWITCHING'
