import threading
import time

from programmers.enums.programmer_state import ProgrammerState
from programmers.models.programmer_snapshot import ProgrammerSnapshot


class ConsoleStatePrinter:
    _SHORT_STATE = {
        ProgrammerState.THINKING: "PENSANDO",
        ProgrammerState.WAITING_DB: "ESPERA_DB",
        ProgrammerState.USING_DB: "USA_DB",
        ProgrammerState.WAITING_COMPILER: "ESPERA_COMP",
        ProgrammerState.COMPILING: "COMPILANDO",
    }

    def __init__(self, programmer_count: int) -> None:
        self._start = time.perf_counter()
        self._lock = threading.Lock()
        self._states = {
            pid: ProgrammerSnapshot(programmer_id=pid, state=ProgrammerState.THINKING)
            for pid in range(1, programmer_count + 1)
        }
        self._print_header()

    def update(self, pid: int, new_state: ProgrammerState) -> None:
        with self._lock:
            self._states[pid].state = new_state
            elapsed = time.perf_counter() - self._start
            snapshot = " | ".join(
                f"P{programmer_id}:{self._SHORT_STATE[self._states[programmer_id].state]}"
                for programmer_id in sorted(self._states)
            )
            event = f"t={elapsed:6.2f}s | evento: P{pid:02d} -> {self._SHORT_STATE[new_state]}"
            print(event, flush=True)
            print(f"            estados: {snapshot}", flush=True)
            print("-" * 120, flush=True)

    @staticmethod
    def _print_header() -> None:
        print("=" * 120)
        print("Simulaçao dos Programadores :)") 
        print("=" * 120, flush=True)
