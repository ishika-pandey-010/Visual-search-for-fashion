.PHONY: help docs docs-check

help:
	@echo "make docs        rebuild docs/traceability.md and the README Results, check every ID links up"
	@echo "make docs-check  check links and Results only (used in CI)"
	@echo "App, index and eval targets arrive in M1 (see CLAUDE.md)."

docs:
	python3 scripts/docs_check.py
	python3 scripts/results.py

docs-check:
	python3 scripts/docs_check.py --check
	python3 scripts/results.py --check
