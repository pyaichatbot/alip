.PHONY: help install test lint format clean demo run-demo

help:
	@echo "ALIP - AI-Assisted Legacy Intelligence Platform"
	@echo ""
	@echo "Available commands:"
	@echo "  make install     - Install package and dependencies"
	@echo "  make test        - Run test suite"
	@echo "  make lint        - Run linter"
	@echo "  make format      - Format code with black"
	@echo "  make clean       - Remove generated files"
	@echo "  make demo        - Create demo data"
	@echo "  make run-demo    - Run complete demo workflow"
	@echo "  make coverage    - Run tests with coverage report"

install:
	pip install -e ".[dev]"

test:
	pytest -v

coverage:
	pytest --cov=alip --cov-report=term-missing --cov-report=html

lint:
	ruff check .
	@echo "Linting complete!"

format:
	black .
	@echo "Code formatted!"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf workspace/
	rm -rf demo_data/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete
	@echo "Cleaned!"

demo:
	python create_demo_data.py

run-demo: demo
	@echo "\n=== Creating Demo Engagement ==="
	alip new --name "Demo Corp" --id demo-001
	@echo "\n=== Ingesting Demo Data ==="
	alip ingest --engagement demo-001 \
		--repo demo_data/sample_repo \
		--db-schema demo_data/schema.sql \
		--query-logs demo_data/queries.json \
		--docs demo_data/docs
	@echo "\n=== Listing Engagements ==="
	alip list
	@echo "\n=== Demo Complete! ==="
	@echo "View artifacts in: workspace/demo-001/artifacts/"
