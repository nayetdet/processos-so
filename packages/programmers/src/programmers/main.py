from programmers.config.simulation_config import SimulationConfig
from programmers.services.programmer_lab_simulation import ProgrammerLabSimulation

def main() -> None:
    config = SimulationConfig()
    simulation = ProgrammerLabSimulation(config=config)
    simulation.run_forever()

if __name__ == "__main__":
    main()
