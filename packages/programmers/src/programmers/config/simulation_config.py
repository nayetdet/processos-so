from dataclasses import dataclass

@dataclass(slots=True)
class SimulationConfig:
    programmer_count: int = 5
    think_min: float = 3.0
    think_max: float = 6.0
    compile_min: float = 4.0
    compile_max: float = 7.0
    seed: int = 0
