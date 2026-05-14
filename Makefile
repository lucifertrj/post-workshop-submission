.PHONY: install setup dev test format lint build run-api run-dash benchmark health clean

install:
	uv pip install --system -e .

setup:
	@echo "Setting up ATTCO environment..."
	python scripts/bootstrap.py

dev:
	uv pip install --system -e ".[dev,dashboard,research]"

test:
	pytest tests/

format:
	ruff check . --fix

lint:
	ruff check .
	mypy . --strict

build:
	docker compose build

run-api:
	attco-api

run-dash:
	@echo "Launching ATTCO optimization dashboard..."
	streamlit run dashboard/app.py

benchmark:
	@echo "Running ATTCO benchmark suite..."
	python scripts/run_benchmark.py

health:
	@echo "Performing system health check..."
	python -m infrastructure.health.runtime_check

clean:
	@echo "Cleaning artifacts and cache..."
	rm -rf artifacts/*.json artifacts/*.parquet artifacts/*.duckdb
	find . -type d -name "__pycache__" -exec rm -rf {} +
