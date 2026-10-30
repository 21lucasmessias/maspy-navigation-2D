# VENV: virtual environment path (default: .venv)
VENV ?= .venv
# PYTHON: Python interpreter used by setup (default: $(VENV)/bin/python)
PYTHON ?= $(VENV)/bin/python

.PHONY: setup run test mutate clean help

setup: ## Create the virtual environment and install project dependencies
	uv venv $(VENV) --python 3.12
	uv pip install --python $(PYTHON) -e ".[dev]"

run: ## Run the 2D navigation simulation
	$(PYTHON) src/Walker_Main.py

test: ## Run the test suite
	$(PYTHON) -m pytest

mutate: ## Mutation-test update_walls against the test suite
	$(PYTHON) tests/mutate_update_walls.py

clean: ## Remove the virtual environment
	rm -rf $(VENV)

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_.-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)