from dataclasses import dataclass
from programmers.enums.programmer_state import ProgrammerState

@dataclass(slots=True)
class ProgrammerSnapshot:
    programmer_id: int
    state: ProgrammerState
