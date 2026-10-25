PY ?= python3
PYTHON := .venv/bin/python
PIP    := .venv/bin/pip

.PHONY: help setup test test-py test-node demo verify clean

help:
	@echo "setup      create .venv and install python/ (editable, dev extras)"
	@echo "test       run python and node suites"
	@echo "demo       render fixtures/reporter/ops.json -> .scratch/demo.docx"
	@echo "verify     verify the rendered demo"
	@echo "clean      remove generated output (.scratch, .pytest-work)"

setup:
	$(PY) -m venv .venv
	$(PIP) install -q -e "python/[dev]"
	cd node && npm install --no-audit --no-fund --silent || true

test: test-py test-node

test-py:
	cd python && ../$(PYTHON) -m pytest

test-node:
	cd node && node --test test/core.test.mjs test/plugin.test.mjs

demo:
	mkdir -p .scratch
	$(PYTHON) -m office_core.cli fill fixtures/templates/report.docx fixtures/reporter/ops.json -o .scratch/demo.docx

verify:
	$(PYTHON) -m office_core.cli verify .scratch/demo.docx fixtures/reporter/ops.json

clean:
	rm -rf .scratch .pytest-work .node-work-*
