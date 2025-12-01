.PHONY: test lint

BIN_DIR := /Users/vincentgibson/Library/Python/3.9/bin
export PYTHONPATH := src

test:
	$(BIN_DIR)/pytest tests/ -v

lint:
	$(BIN_DIR)/ruff check .
	$(BIN_DIR)/black --check .
