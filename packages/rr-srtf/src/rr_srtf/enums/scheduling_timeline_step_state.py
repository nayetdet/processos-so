from enum import Enum

class SchedulingTimelineStepState(str, Enum):
    NEW = "NEW"
    RUNNING = "RUNNING"
    READY = "READY"
    WAITING = "WAITING"
    SWITCHING = "SWITCHING"
