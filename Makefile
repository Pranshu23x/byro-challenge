PY ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: setup test demo run review learn eval

setup:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install -r requirements.txt
	test -f .env || cp .env.example .env

test:
	$(BIN)/python -m pytest tests/ -q

demo:
	$(BIN)/python -m app demo

run:
	$(BIN)/python -m app run

review:
	$(BIN)/python -m app review

learn:
	$(BIN)/python -m app learn

eval:
	$(BIN)/python -m app eval

# Windows: use `powershell -File setup.ps1 <task>` instead of make.
