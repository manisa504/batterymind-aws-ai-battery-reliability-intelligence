.PHONY: install test lint api ingest export web showcase

install:
	python3 -m pip install -e '.[dev]'

test:
	python3 -m pytest

lint:
	python3 -m ruff check apps packages tests scripts

api:
	python3 -m uvicorn apps.api.main:app --reload

ingest:
	python3 scripts/ingest_nasa.py --archive .local-data/nasa-battery-data.zip

export:
	python3 scripts/export_showcase.py

web:
	npm --prefix apps/web run dev

showcase:
	npm --prefix showcase run dev

