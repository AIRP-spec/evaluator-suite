# Phase 1 pipeline (sections 4.1–4.4)

Tools under `v3/airp_v3/` implement the standing brief without collecting until
OpenRouter written approval exists.

| step | module | gate |
|---|---|---|
| Labeling guide | `LABELING-GUIDE.md` | adopted; ambiguities listed in-guide |
| CSE filter | `python3 -m airp_v3.filter_cse` | records category + keyword drop counts |
| Collection | `python3 -m airp_v3.collect` | **refuses** unless repo-root `OPENROUTER_APPROVAL` exists with Justin's written approval |
| Labeling | `python3 -m airp_v3.label` | two labelers not in elicitation set; no OpenAI; `$50` cap, stop at `$25` |
| Adjudication | `python3 -m airp_v3.adjudicate` | mechanical diff; third-model tie-break on safety primitives; drop-with-reason; per-primitive / per-class agreement; stop-and-report under 70% |
| Loader / compose | `airp_v3.loader.load_items` | asserts composed `expect_classes` == stored |
| Seal | `python3 -m airp_v3.seal` | leak check vs v2, v1-207, training corpus; hash + manifest |

Dry-run entrypoint: `python3 tools/dryrun_pipeline.py` (see `dryrun/`).

Collection stays blocked until Justin places the OpenRouter approval text in
`OPENROUTER_APPROVAL` at the repo root. Labeling of already-collected items does
not require that file (labeling is not Red Teaming under OpenRouter ToS §7(11)).
