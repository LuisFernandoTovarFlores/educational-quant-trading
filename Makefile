.PHONY: help install install-dev test test-all lint format run clean

help:
	@echo "Targets:"
	@echo "  install      Install runtime dependencies (editable)"
	@echo "  install-dev  Install runtime + development dependencies"
	@echo "  test         Run offline unit tests"
	@echo "  test-all     Run all tests, including network integration tests"
	@echo "  lint         Run ruff"
	@echo "  format       Format code with ruff"
	@echo "  run          Run the weekly pipeline"
	@echo "  clean        Remove caches and build artifacts"

install:
	python -m pip install -e .

install-dev:
	python -m pip install -e ".[dev,fred]"
	pre-commit install

test:
	python -m pytest -q

test-all:
	python -m pytest -q -m "integration or not integration"

lint:
	ruff check .

format:
	ruff format .

run:
	python -m src.run_weekly

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
