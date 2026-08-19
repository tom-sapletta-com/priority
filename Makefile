PYTHON ?= python3
POLICY ?= priority-evolution.dsl.yaml
SCHEMA ?= schemas/priority-evolution.schema.json
STATE ?= examples/state.json
HEALTHY ?= examples/state-healthy.json
NOW ?= 2026-08-19T10:00:00Z

.PHONY: deps test validate evaluate evaluate-healthy compile demo

deps:
	$(PYTHON) -m pip install -r requirements.txt

test:
	$(PYTHON) -m unittest discover -s tests -v

validate:
	$(PYTHON) adapters/standardctl.py validate --policy $(POLICY) --schema $(SCHEMA)

evaluate:
	$(PYTHON) adapters/standardctl.py evaluate --policy $(POLICY) --state $(STATE) --now $(NOW) --out receipts/priority-decision.json

evaluate-healthy:
	$(PYTHON) adapters/standardctl.py evaluate --policy $(POLICY) --state $(HEALTHY) --now $(NOW) --out receipts/healthy-decision.json

compile: evaluate
	$(PYTHON) adapters/standardctl.py compile-context --policy $(POLICY) --receipt receipts/priority-decision.json --out-dir generated-context

demo: test validate evaluate evaluate-healthy compile
	@echo "demo complete"
