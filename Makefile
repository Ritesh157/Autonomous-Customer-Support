# CloudDesk developer commands (CLAUDE.md section 14).
# Windows: run from Git Bash. PYTHONPATH uses ';' there and ':' elsewhere.

ifeq ($(OS),Windows_NT)
PY := .venv/Scripts/python.exe
SEP := ;
else
PY := .venv/bin/python
SEP := :
endif

export PYTHONPATH := backend$(SEP)$(PYTHONPATH)
export PYTHONIOENCODING := utf-8
TICKET ?= CD-1002

.PHONY: help setup seed ingest backend demo mcp test lint smoke terraform-validate

help:
	@echo "setup seed ingest backend demo mcp test lint smoke terraform-validate"

setup:  ## venv + deps + .env
	uv sync
	@test -f .env || cp .env.example .env

backend:  ## FastAPI on :8000
	$(PY) -m uvicorn app.main:app --reload --port 8000

test:  ## offline pytest
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check .

seed:    ; @echo "not implemented yet (Phase 2)"; exit 1
ingest:  ; @echo "not implemented yet (Phase 5)"; exit 1
demo:    ; @echo "not implemented yet (Phase 9) - TICKET=$(TICKET)"; exit 1
mcp:     ; @echo "not implemented yet (Phase 6)"; exit 1
smoke:   ; @echo "not implemented yet (Phase 13)"; exit 1
terraform-validate: ; @echo "not implemented yet (Phase 13)"; exit 1
