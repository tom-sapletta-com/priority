.PHONY: validate rebuild test verify reproducibility cycle clean

validate:
	python3 adapters/standardctl.py validate --policy priority-evolution.dsl.yaml --schema schemas/priority-evolution.schema.json
	python3 adapters/ecosystemctl.py validate-registry --registry registry/ecosystem-tools.yaml --schema schemas/ecosystem-tool-registry.schema.json

rebuild:
	./scripts/rebuild-generated.sh

test:
	python3 -m unittest discover -s tests -v

verify:
	./scripts/verify.sh

reproducibility:
	./scripts/check-reproducibility.sh

cycle:
	set +e; \
	python3 adapters/autonomyctl.py cycle \
		--request examples/ticket-context-request.json \
		--out-dir runtime/cycle \
		--now 2026-08-19T10:00:00Z; \
	code=$$?; \
	if [ $$code -eq 0 ] || [ $$code -eq 3 ]; then \
		if [ "$${SHADOW_RECORD:-0}" = "1" ]; then \
			./scripts/record-shadow-receipt.sh runtime/cycle; \
		fi; \
		exit 0; \
	fi; \
	exit $$code

clean:
	rm -rf __pycache__ adapters/__pycache__ tests/__pycache__ runtime
