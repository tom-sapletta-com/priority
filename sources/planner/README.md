# Pinned todo2code contract

`intent.graph.json` and `diagnostics.json` are a bounded extract of this
package (`adapters/`, `tests/`, recent Git, registry config). They are
not a production workspace graph and are not a claim that planning
succeeded.

Regenerate:

```bash
T2C=../todo2code/dist/src/cli.js
node "$T2C" extract ast adapters --out sources/planner/ast.intent.jsonl
node "$T2C" extract ast tests --out sources/planner/ast-tests.intent.jsonl
node "$T2C" extract git --root . --count 4 --out sources/planner/git.intent.jsonl
node "$T2C" link sources/planner/*.intent.jsonl --out sources/planner/intent.graph.json
node "$T2C" diagnose sources/planner/intent.graph.json --out sources/planner/diagnostics.json
rm -f sources/planner/*.intent.jsonl
```
