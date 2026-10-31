# Phase 1 pipeline (sections 4.1–4.4)

Tools under `v3/airp_v3/`. Collection runs self-hosted per the
[2026-11-01 plan amendment](PLAN-AMENDMENT-2026-11-01.md); the OpenRouter backend
remains and still refuses without `OPENROUTER_APPROVAL`.

| step | module | gate |
|---|---|---|
| Labeling guide | `LABELING-GUIDE.md` | adopted; ambiguities listed in-guide |
| Prompt sets | `python3 tools/build_prompt_sets.py` | pinned source commits; raw sources only in memory; filter, dedupe, leak-drop test rows vs train; round-robin model assignment; report carries `out_sha256` |
| CSE filter | `python3 -m airp_v3.filter_cse` | category + keyword (incl. adult-sexual labels) drop counts and ids; `in_sha256` / `out_sha256` |
| Collection (self-hosted) | `python3 -m airp_v3.collect --backend local --base-url http://<pod>:8000` | `airp_v3.policy.find_policy_verified` against `policy/POLICY_VERIFIED.json`: refuses unlisted / excluded / OpenAI model, wrong revision, DOUBT verdict, wrong role, licence sha mismatch; refuses test sets on training models and the reverse; refuses unless prompts sha == filter report `out_sha256`; max_tokens ≤ 800 |
| Collection (OpenRouter) | `python3 -m airp_v3.collect --backend openrouter` | **refuses** unless repo-root `OPENROUTER_APPROVAL` exists |
| Labeling | `python3 -m airp_v3.label` | two labelers not in elicitation set; no OpenAI; `$50` cap, stop at `$25` |
| Adjudication | `python3 -m airp_v3.adjudicate` | mechanical diff; third-model tie-break on safety primitives; drop-with-reason; per-primitive / per-class agreement; stop-and-report under 70% |
| Loader / compose | `airp_v3.loader.load_items` | asserts composed `expect_classes` == stored |
| Seal | `python3 -m airp_v3.seal` | leak check vs v2, v1-207, training corpus; hash + manifest |

## Self-hosted collection

Models, revisions, quantization, vLLM args and thinking-off kwargs:
`collect/models.selfhost.json`. Verdicts and licence hashes: `policy/POLICY_VERIFIED.json`
with copies under `policy/licenses/` (`SHA256SUMS`).

    python3 -m airp_v3.collect --backend local --base-url http://127.0.0.1:8000 \
      --models collect/models.selfhost.json --model-key phi-4 --role test \
      --prompts prompts-test.jsonl --filter-report collect/reports/filter-report-test.json \
      --host runpod:<pod>/<gpu>/vllm-<ver> --out out/phi-4.jsonl --assigned-only \
      --concurrency 32 --max-wall-seconds 4800 --max-dollars 3.5 --dollars-per-hour <rate> \
      --billing-start-epoch <pod start> --summary out/phi-4.summary.json

- Thinking is forced off per model (`chat_template_kwargs`); reasoning tokens,
  `<think>` markers and finish_reason are recorded per row.
- Each row's `provenance` has model, HF revision, quantization, role, host, backend,
  prompt set / id / kind, token counts, licence sha, policy verdict, prompts sha,
  terms reference and timestamps. No system prompt.
- Append-only output; rerunning resumes by id. Stops (exit 3) on wall-clock,
  dollar limit or 25 errors; errors go to `<out>.errors.jsonl`.

Dry-run without a pod: `tools/tiny_openai_server.py` (SmolLM2-135M on CPU) +
`tools/dryrun_selfhost.py`; result in `dryrun/selfhost/DRYRUN-SELFHOST-SUMMARY.json`
(9 refusals, 8 rows written, resume skipped 4).

Dry-run of the rest: `python3 tools/dryrun_pipeline.py` (see `dryrun/`).
Labeling of collected items does not require `OPENROUTER_APPROVAL`; it has not run.
