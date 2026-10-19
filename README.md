# AIRP evaluator suite

Public, open held-out suites and corpus tooling for the AIRP local evaluator
(protocol and reference client: [AIRP-spec/inference-advocate](https://github.com/AIRP-spec/inference-advocate)).

Each suite version is a top-level directory:

| dir | status |
|---|---|
| [`v3/`](v3/) | in preparation: definitions (PRIMITIVES, classes, composition 2a), composition and scoring tools, blind leak check, prompt-set and model shortlists. No items collected yet. |

**Not included: the v2 suite and the v1-207 items.** Both have been public on `main` of
AIRP-spec/inference-advocate since 2026-09-11 (`data/evaluator-gate/held-out-suite.v2.json`,
`held-out-suite.v1.json`). They are deliberately kept out of this repository so v3 is authored without
them; `v3/tools/check_no_protected.py` (hash fingerprints only, no text) checks that no v2/v1-207 id or text
enters this repo, and `v3/airp_v3/leakcheck.py` lets an operator check any item file against them blindly.
The protected files themselves are never committed here.

Start with [`v3/README.md`](v3/README.md). Licence: Apache-2.0 (as AIRP-spec/inference-advocate).
