from enum import Enum


class SchedulingTimelineEvent(str, Enum):
    ARRIVE = 'ARRIVE'
    DISPATCH = 'DISPATCH'
    PREEMPT = 'PREEMPT'
    FINISH = 'FINISH'
