.PHONY: help docs docs-check setup catalogue index test test-data check

help:
	@echo "make docs        rebuild docs/traceability.md and the README Results, check every ID links up"
	@echo "make docs-check  check links and Results only (used in CI)"
	@echo "make setup       install Python 3.12 and every dependency with uv"
	@echo "make catalogue   download the pinned datasets and build data/catalogue.parquet (US-01)"
	@echo "make index       embed the catalogue with both models and build one FAISS index each (US-02)"
	@echo "make test        unit tests on the generated fixture (what CI runs)"
	@echo "make test-data   checks on the real catalogue and indexes (needs make catalogue and make index)"
	@echo "make check       everything CI runs: docs and unit tests"

docs:
	python3 scripts/docs_check.py
	python3 scripts/results.py

docs-check:
	python3 scripts/docs_check.py --check
	python3 scripts/results.py --check

setup:
	uv sync

catalogue:
	uv run python -m vsearch.catalogue

index:
	uv run python -m vsearch.index

test:
	uv run pytest -m "not data"

test-data:
	uv run pytest -m data

check: docs-check test
