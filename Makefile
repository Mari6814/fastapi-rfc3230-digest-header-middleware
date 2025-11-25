.PHONY: format check test all

all: format check

format:
	uv run ruff format

check:
	uv run ruff check --fix

test:
	uv run --with coverage coverage run --source fastapi_rfc3230_digest_header_middleware/ -m pytest -v tests/
	uv run --with coverage coverage report -m