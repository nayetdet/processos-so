.PHONY: install cats-and-dogs programmers rr-srtf

install:
	uv sync --all-groups --all-packages

cats-and-dogs:
	uv run python -m cats-and-dogs

programmers:
	uv run python -m programmers

rr-srtf:
	uv run python -m rr_srtf
