from enum import Enum


class SchedulingTimelineState(str, Enum):
    IDLE = 'IDLE'
    SWITCHING = 'SWITCHING'
    RUNNING = 'RUNNING'
