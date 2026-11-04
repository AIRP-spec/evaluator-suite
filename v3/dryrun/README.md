# Phase 1 dry-run fixtures

- `items-40.jsonl` — the 40 draft-cse-shape rows from AIRP-spec/inference-advocate
  `decide/shared-adopt/draft-cse-shape-rows` (source sha256 `551f2d6d…`). Locally
  composed; no writer model. Used as the dry-run stand-in for the brief's
  "40 existing DeepSeek items".
- `filter-fixture-prompts.jsonl` — synthetic prompts for the CSE filter (category
  drops use redacted placeholders; keyword drops use benign minor-marker prompts).
- `labelers.json` — two labelers **not** in the elicitation shortlist; no OpenAI.
- `out/` — dry-run outputs. See `out/DRYRUN-SUMMARY.json` (no safety-class item text).

Re-run (from `v3/`):

```
python3 tools/dryrun_pipeline.py --mock --protected-dir /tmp/airp-protected
# or live labeling (spends OpenRouter budget):
python3 -m airp_v3.label --items dryrun/items-40.jsonl --guide LABELING-GUIDE.md \
  --labelers dryrun/labelers.json --out dryrun/out/labels-live.jsonl
```

Collection is always blocked without repo-root `OPENROUTER_APPROVAL`.
