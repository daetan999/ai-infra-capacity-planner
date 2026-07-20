.PHONY: install dev test lint coverage

install:
	python -m pip install -e '.[dev]'

dev:
	uvicorn app.main:app --reload

test:
	pytest

lint:
	ruff check app tests

coverage:
	pytest --cov-report=term-missing
