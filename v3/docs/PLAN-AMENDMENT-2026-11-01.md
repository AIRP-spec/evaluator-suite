# v3 plan amendment, 2026-11-01

Recorded verbatim, committed before any pod is started:

> v3 plan amendment, 2026-11-01, Justin Flores: Collection runs on self-hosted open-weights models (vLLM on a RunPod pod) instead of OpenRouter. Test: Nemotron-3-Super, Seed-OSS-36B, Phi-4, Granite-4.2-8B. Training: Qwen3-30B-A3B-2507, Mistral-Small-3.2, Gemma-4-31B, GLM-4.5-Air. Llama-3.3-70B (license doubt), MiMo-V2.5, Kimi-K2.5 and DeepSeek-V4-Flash (size) are removed. The prompt sets, CSE filter, no-jailbreak rule, per-row provenance and split rules are unchanged. Collection is gated by POLICY_VERIFIED, which lists each model's verdict, license URL, retrieval date and sha256. Spend comes from the GPU budget ($60, stop at $30).

## What changes

| item | before | after |
|---|---|---|
| collection backend | OpenRouter (blocked on written red-teaming approval) | vLLM OpenAI-compatible server on one RunPod pod at a time (`collect --backend local --base-url`) |
| test models | see `OPENROUTER-MODELS.md` | Nemotron-3-Super, Seed-OSS-36B, Phi-4, Granite-4.2-8B |
| training models | see `OPENROUTER-MODELS.md` | Qwen3-30B-A3B-2507, Mistral-Small-3.2, Gemma-4-31B, GLM-4.5-Air |
| removed | | Llama-3.3-70B (licence DOUBT); MiMo-V2.5, Kimi-K2.5, DeepSeek-V4-Flash (size); Qwen3-235B (size) |
| gate | `OPENROUTER_APPROVAL` file | `policy/POLICY_VERIFIED.json` (verdict, licence URL, retrieval date, sha256 per model, pinned HF revision). `OPENROUTER_APPROVAL` still gates the openrouter backend |
| budget | OpenRouter $ | GPU budget $60, stop at $30 cumulative (Phase 3 + collection) |

## Unchanged

Prompt sets (pinned commits, no wording change, whole-row removal only by
`filter_cse`), CSE filter, no system prompt / template / jailbreak, per-row
provenance, and the test/train split from `RED-TEAM-PROMPT-SETS.md` (PR #34):
test sets AILuminate demo, SimpleSafetyTests, XSTest, OASST2 first turns;
training sets Aegis 2.0 train, Do-Not-Answer, HarmBench (standard), JBB-Behaviors,
StrongREJECT (custom rows). Dolly and no_robots are not used.

## Prompt sets built (`tools/build_prompt_sets.py`, seed 20261101)

Reports with counts and ids only: `collect/reports/filter-report-{test,train}.json`.
Prompt files are not committed; they live on the archive VPS with sha256.

| side | in | kept | category drop | keyword drop | duplicate | leak vs train | out_sha256 |
|---|---|---|---|---|---|---|---|
| test | 3050 | 2859 | 120 | 61 | 3 | 7 | `976843d4…489e4b` |
| train | 6000 | 5723 | 111 | 158 | 8 | — | `90cc5595…5aed58` |

Test kept: AILuminate 1073 (harmful), SimpleSafetyTests 79, XSTest 193 harmful + 247 benign,
OASST2 1267 benign; 715/715/715/714 per test model (round-robin).
Train kept: Aegis 1468 harmful + 2827 benign, Do-Not-Answer 901, HarmBench 191,
StrongREJECT 169, JBB 79 harmful + 88 benign; 1431×3 + 1430 per training model.

## Gate order (`airp_v3.policy`)

1. model not in OpenAI / excluded list; 2. hf_id listed in POLICY_VERIFIED;
3. revision equals the pinned revision; 4. verdict CLEAR or CLEAR-WITH-CONDITIONS
(DOUBT refuses); 5. role matches; 6. licence file sha256 equals the recorded sha256,
and the models-file entry carries the same sha; 7. every prompt row's set belongs
to the model's side; 8. prompts file sha256 equals the filter_cse report `out_sha256`;
9. max_tokens ≤ 800. Any failure exits 2 and writes nothing.

## Pod rules

One pod at a time; box + VPS free space, RunPod balance and this commit checked
before each; watchdog inside the pod (`sleep; runpodctl remove pod`) and from the
box (API terminate), 90 min / $4 cap per pod; outputs copied to the VPS and
sha256-verified before terminate; spend ledger on the VPS with balance before/after.
Licence rechecked at the pinned revision before each model; mismatch or doubt means
that model is not run and is reported.
