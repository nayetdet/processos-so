.PHONY: install cats-and-dogs cats-and-dogs-with-ticks programmers rr-srtf

install:
	uv sync --all-groups --all-packages

cats-and-dogs:
	cd packages/cats-and-dogs/src/cats_and_dogs && uv run python animal_without_ticks.py

cats-and-dogs-with-ticks:
	cd packages/cats-and-dogs/src/cats_and_dogs && uv run python animal_ticks.py

programmers:
	uv run python -m programmers

rr-srtf:
	uv run python -m rr_srtf
