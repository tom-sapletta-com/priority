.PHONY: validate rebuild test verify reproducibility clean

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

clean:
	rm -rf __pycache__ adapters/__pycache__ tests/__pycache__
