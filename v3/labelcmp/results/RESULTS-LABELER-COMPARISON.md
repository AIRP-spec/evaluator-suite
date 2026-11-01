# Labeler comparison — results (pod labcmp-1, 2026-11-01)

Declared in `../DECLARATION-LABELER-COMPARISON.md` at commit `ba8323be` before any pod. Scored by
`tools/labelcmp_score.py` → `SCORES-labcmp-1.json` (metrics, counts and ids only; no item text, no labeler output text).
Gold = data-v9 val (`964c2b21…`), P = 853 composed rows (primary), W = 20 writer rows (reported only).

## Run

- Pod `267s9l02n59nvw`, RTX PRO 6000 Blackwell Server Edition, SECURE EU-RO-1, $2.49/h, network volume `rmn62wuuzx`.
  Created 11:14 NPT, terminated 11:42 NPT (27.8 min), cost $1.154 (balance $46.006 → $44.868). Pod list empty after.
- Both watchdogs ran (box `watchdog.py`, in-pod `runpodctl remove pod`). vLLM 0.32.0, `--max-model-len 8192`.
- Raw label files (sha256) archived to the VPS at `v3-labcmp-20261101/out-labcmp-1/` with `SHA256SUMS`, `sha256sum -c` 17/17 OK:
  qwen3 `bea6be69…2674`, mistral `503dd70e…ec60`, gemma `947d5b75…7fec`, phi-4 `6729b415…0505`, granite `6cf2f427…a096`.

## Per-labeler results on P (n = 853)

| labeler | role | valid | class-set exact | stance acc | primitives exact | CSE recall | SH recall (P) | min safety recall |
|---|---|---|---|---|---|---|---|---|
| mistral-small-3.2 | train | 850 (99.65%) | **0.8476** (723) | 0.8417 | 0.5381 | 52/66 | 13/24 | 0.542 |
| gemma-4-31b | train | 853 (100%) | **0.8124** (693) | 0.8617 | 0.2814 | 57/66 | 13/24 | 0.542 |
| qwen3-30b-a3b-2507 | train | 853 (100%) | 0.7186 (613) | 0.8394 | 0.4291 | 60/66 | 16/24 | 0.667 |
| phi-4 | test | 769 (90.15%) — ineligible | 0.6706 | 0.7456 | 0.4760 | 12/66 | 10/24 | 0.182 |
| granite-4.2-8b | test | **not measured** (transport failure, below) | — | — | — | — | — | — |
| seed-oss-36b | test | **not run** (download ENOSPC) | — | — | — | — | — | — |
| nemotron-3-super | test | **not run** (download ENOSPC) | — | — | — | — | — | — |

Safety-class false positives: CSE fp mistral 0, gemma 0, qwen3 2, phi-4 0; SH fp mistral 0, gemma 0, qwen3 6, phi-4 4.
CSE miss upper bound (one-sided 95%): mistral 0.312, gemma 0.226, qwen3 0.172. Miss/extra ids are in `SCORES-labcmp-1.json`.
Primitives under 70% agreement: gemma `q:is_mention_not_use`; none for the others.
W (20 qwen-written self_harm rows, non-qwen labelers only, reported only): class-set exact mistral 7/20, gemma 9/20, phi-4 4/20.

## Selection (declared rule, applied mechanically)

- **Labels test-side rows (train-role labelers): pair = mistral-small-3.2 + gemma-4-31b, tiebreaker = qwen3-30b-a3b-2507.**
  All three eligible; mistral leads gemma by 3.5 pp (outside the 0.5 pp tie band).
- **Labels train-side rows (test-role labelers): no pair.** Only phi-4 was measured and it is ineligible (valid 0.9015 < 0.95:
  63 outputs with no JSON, mostly refusals, and 21 with an invalid object name).

## What failed and why

- **granite-4.2-8b:** 811 of 873 requests got `Connection refused` from the box-side SSH tunnel; the vLLM log shows the
  engine idle with 0 waiting requests. The tunnel failed, not the model. Of the 62 completed requests, 59 were valid. The
  scorer counts this run as invalid; it is not a measurement of granite.
- **seed-oss-36b, nemotron-3-super:** `hf download` failed with `No space left on device` (250 GB container disk). The
  previous models' hub directories were deleted after use. The likely cause is the hf-xet cache under `HF_HOME`, which
  was not cleared. This was not confirmed before termination.
- Fixes for any re-run: clear `HF_HOME/xet` after each model and log `df`; check the tunnel's health and restart it on
  `Connection refused` before labeling.
