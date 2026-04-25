from enum import StrEnum


class SchedulingTimelineEvent(StrEnum):
    ARRIVE = 'ARRIVE'
    DISPATCH = 'DISPATCH'
    PREEMPT = 'PREEMPT'
    FINISH = 'FINISH'