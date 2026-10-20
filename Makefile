.PHONY: help docs docs-check setup catalogue index eval-collect eval-sheets eval-queries eval-check test test-data check

help:
	@echo "make docs        rebuild docs/traceability.md and the README Results, check every ID links up"
	@echo "make docs-check  check links and Results only (used in CI)"
	@echo "make setup       install Python 3.12 and every dependency with uv"
	@echo "make catalogue   download the pinned datasets and build data/catalogue.parquet (US-01)"
	@echo "make index       embed the catalogue with both models and build one FAISS index each (US-02)"
	@echo "make eval-collect  download candidate query photos from Openverse into data/candidates/ (D-26)"
	@echo "make eval-sheets   contact sheets of the candidates, for review by eye"
	@echo "make eval-queries  rebuild eval/queries/ from eval/queries/selections.csv"
	@echo "make eval-check    assign dev/test to new query photos, then check the set (US-03)"
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

eval-collect:
	uv run python -m vsearch.openverse collect eval/openverse-terms.csv

eval-sheets:
	uv run python -m vsearch.openverse sheets

eval-queries:
	uv run python -m vsearch.queries vocabulary
	uv run python -m vsearch.queries build

eval-check:
	uv run python -m vsearch.queries check

test:
	uv run pytest -m "not data"

test-data:
	uv run pytest -m data

check: docs-check test
