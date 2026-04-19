import random
import threading
import time
from programmers.concurrency.fifo_semaphore import FifoSemaphore
from programmers.config.simulation_config import SimulationConfig
from programmers.enums.programmer_state import ProgrammerState
from programmers.utils.console_state_printer import ConsoleStatePrinter

class ProgrammerLabSimulation:
    def __init__(self, config: SimulationConfig) -> None:
        self._config = config
        self._printer = ConsoleStatePrinter(programmer_count=config.programmer_count)
        self._db_slots = FifoSemaphore(initial=2)
        self._compiler = FifoSemaphore(initial=1)
        self._stop_event = threading.Event()
        self._rng = random.Random(config.seed)
        self._rng_lock = threading.Lock()

    def run_forever(self) -> None:
        threads = [
            threading.Thread(target=self._programmer_loop, args=(pid,), daemon=True)
            for pid in range(1, self._config.programmer_count + 1)
        ]
        for thread in threads:
            thread.start()

        try:
            while True:
                time.sleep(1.0)
        except KeyboardInterrupt:
            self._stop_event.set()
            for thread in threads:
                thread.join(timeout=0.5)
            print("\nSimulação encerrada :/ COmeçe outra a qualquer momento!", flush=True)

    def _programmer_loop(self, pid: int) -> None:
        while not self._stop_event.is_set():
            self._printer.update(pid, ProgrammerState.THINKING)
            if self._wait_with_stop(self._random_between(self._config.think_min, self._config.think_max)):
                return

            self._printer.update(pid, ProgrammerState.WAITING_DB)
            self._db_slots.down()
            self._printer.update(pid, ProgrammerState.USING_DB)

            self._printer.update(pid, ProgrammerState.WAITING_COMPILER)
            self._compiler.down()
            self._printer.update(pid, ProgrammerState.COMPILING)

            interrupted = self._wait_with_stop(
                self._random_between(self._config.compile_min, self._config.compile_max)
            )
            self._compiler.up()
            self._db_slots.up()
            if interrupted:
                return

    def _random_between(self, lower: float, upper: float) -> float:
        with self._rng_lock:
            return self._rng.uniform(lower, upper)

    def _wait_with_stop(self, duration: float) -> bool:
        return self._stop_event.wait(timeout=duration)
