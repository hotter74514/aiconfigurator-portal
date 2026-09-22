SHELL := /bin/sh

# Populate these with commands already supported by the project.
DEV_CMD ?= uv run uvicorn portal.app:app --reload
FORMAT_CMD ?= uv run ruff format --check .
LINT_CMD ?= uv run ruff check .
TYPECHECK_CMD ?= uv run mypy src
TEST_CMD ?= uv run pytest
CLIENT_TEST_CMD ?= node --test tests/test_history.mjs
BUILD_CMD ?= docker build --platform linux/amd64 -t serving-configuration-portal:local .
INTEGRATION_CMD ?= uv run pytest -m integration

.PHONY: help status docs check mcp-check dev format lint typecheck test client-test build integration ci

help:
	@echo "Available targets:"
	@echo "  make status       Show the current Git branch and working tree"
	@echo "  make docs         Validate required harness files"
	@echo "  make check        Run configured static and test checks"
	@echo "  make mcp-check    Verify Node.js and the Playwright MCP package"
	@echo "  make dev          Run DEV_CMD"
	@echo "  make format       Run FORMAT_CMD"
	@echo "  make lint         Run LINT_CMD"
	@echo "  make typecheck    Run TYPECHECK_CMD"
	@echo "  make test         Run TEST_CMD"
	@echo "  make client-test  Run browser-local history tests"
	@echo "  make build        Run BUILD_CMD"
	@echo "  make integration  Run INTEGRATION_CMD"
	@echo "  make ci           Run checks, integration, and build when configured"

status:
	@git status --short --branch

docs:
	@test -f AGENTS.md
	@test -f ARCHITECTURE.md
	@test -f DEVELOPMENT.md
	@test -f ROADMAP.md
	@test -f TASKS.md
	@test -f .codex/config.toml
	@test -f docs/project-brief.md
	@test -f docs/DESIGN_DECISIONS.md
	@test -f docs/decisions/000-template.md
	@test -f docs/verification-checklist.md
	@test -f prompts/architect.md
	@test -f prompts/builder.md
	@test -f prompts/debug.md
	@test -f prompts/implement.md
	@test -f prompts/plan.md
	@test -f prompts/review.md

check: docs
	$(if $(strip $(LINT_CMD)),$(LINT_CMD),@echo "LINT_CMD is not configured; skipping.")
	$(if $(strip $(TYPECHECK_CMD)),$(TYPECHECK_CMD),@echo "TYPECHECK_CMD is not configured; skipping.")
	$(if $(strip $(TEST_CMD)),$(TEST_CMD),@echo "TEST_CMD is not configured; skipping.")
	$(if $(strip $(CLIENT_TEST_CMD)),$(CLIENT_TEST_CMD),@echo "CLIENT_TEST_CMD is not configured; skipping.")

mcp-check:
	@command -v node >/dev/null || (echo "Node.js 20+ is required for Playwright MCP."; exit 1)
	@node -e 'const major = Number(process.versions.node.split(".")[0]); if (major < 20) process.exit(1)'
	@command -v npx >/dev/null || (echo "npx is required for Playwright MCP."; exit 1)
	@npx --yes @playwright/mcp@latest --help >/dev/null
	@echo "Playwright MCP package is available."

dev:
	@test -n "$(strip $(DEV_CMD))" || (echo "DEV_CMD is not configured."; exit 1)
	$(DEV_CMD)

format:
	@test -n "$(strip $(FORMAT_CMD))" || (echo "FORMAT_CMD is not configured."; exit 1)
	$(FORMAT_CMD)

lint:
	@test -n "$(strip $(LINT_CMD))" || (echo "LINT_CMD is not configured."; exit 1)
	$(LINT_CMD)

typecheck:
	@test -n "$(strip $(TYPECHECK_CMD))" || (echo "TYPECHECK_CMD is not configured."; exit 1)
	$(TYPECHECK_CMD)

test:
	@test -n "$(strip $(TEST_CMD))" || (echo "TEST_CMD is not configured."; exit 1)
	$(TEST_CMD)

client-test:
	@test -n "$(strip $(CLIENT_TEST_CMD))" || (echo "CLIENT_TEST_CMD is not configured."; exit 1)
	$(CLIENT_TEST_CMD)

build:
	@test -n "$(strip $(BUILD_CMD))" || (echo "BUILD_CMD is not configured."; exit 1)
	$(BUILD_CMD)

integration:
	@test -n "$(strip $(INTEGRATION_CMD))" || (echo "INTEGRATION_CMD is not configured."; exit 1)
	$(INTEGRATION_CMD)

ci: check
	$(if $(strip $(INTEGRATION_CMD)),$(INTEGRATION_CMD),@echo "INTEGRATION_CMD is not configured; skipping.")
	$(if $(strip $(BUILD_CMD)),$(BUILD_CMD),@echo "BUILD_CMD is not configured; skipping.")
