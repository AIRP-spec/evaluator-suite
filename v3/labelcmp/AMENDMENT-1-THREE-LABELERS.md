# Amendment 1 to the labeler-comparison declaration: three labelers per row

Decided by Justin, 2026-11-01 15:26 NPT (t205u). Committed before the second comparison pod (labcmp-2) and before any
cross-side labeling. Amends `DECLARATION-LABELER-COMPARISON.md` (commit `ba8323be`). Where the two conflict, this file
governs. Pins are unchanged: guide `5b2908ba…5f21`, composition 2a `59ddf1f6…`, POLICY_VERIFIED `9f49db7f…`, gold
`964c2b21…` (P = 853 composed rows, W = 20 writer rows reported only).

**Reason (Justin):** the mistral + gemma pair catches 13 of 24 self_harm positives each. A pair rule would under-label
the class the certification depends on.

## 1. Labeling design for cross-side labeling (later; not started by this amendment)

- **Three labelers on every row.** Each side's trio is chosen as in §2. A labeler never labels text from its own
  family (same-family skip, unchanged).
- **child_sexual_exploitation and self_harm:** if **any** of the three labelers fires the class on a row, the row goes
  to adjudication by the trio's **third** labeler (rank 3 in §2) with the full labeling guide. The adjudicated output
  decides that class on that row.
- **All other classes:** majority of three. When the three outputs do not yield a majority (for example, an invalid
  output leaves a 1–1 split), the guide breaks the tie in adjudication by the third labeler.
- Invalid or missing outputs count as "not fired". They are never resampled silently, and each one is reported by id.
- **Reporting:** per-labeler, per-class recall and precision against gold (counts tp/fn/fp/gold_pos plus rates) are
  reported next to the exact-match metrics. Implemented in `tools/labelcmp_score.py` as `per_class_table` (`--table`
  writes TSV). Counts only, no item text.

## 2. Trio per side

- Eligibility is unchanged: valid-output rate ≥ 0.95 on P. Ranking is unchanged: class-set exact on P, ties within
  0.5 pp broken by min safety recall, then primitives exact, then key.
- **Labeling test-side text (train-role labelers): mistral-small-3.2, gemma-4-31b, qwen3-30b-a3b-2507** (measured on
  labcmp-1; all three eligible; ranked in that order, so qwen3 is the third/adjudicator).
- **Labeling train-side text (test-role labelers):** the three eligible test-role labelers, ranked by the same rule.
  Candidates are phi-4 (measured on labcmp-1; ineligible at valid 0.9015), granite-4.2-8b, seed-oss-36b and
  nemotron-3-super (measured on labcmp-2). **If fewer than three clear the 95% bar, report and stop.** No other
  candidate is added and glm-4.5-air stays out.
- The scorer outputs `trio` (top three eligible) and `trio_stop` (true when fewer than three are eligible).

## 3. labcmp-2 procedure (one pod)

- Same declared labeling procedure as §3 of the declaration: same prompt, guide, temperature 0, max_tokens 300,
  `--max-model-len 8192`, vLLM 0.32.0, one RTX PRO 6000 (96 GB). Pod caps: SECURE, $4 / 90 min, both watchdogs,
  headroom check first.
- Models in order: granite-4.2-8b (**re-run from scratch**; the labcmp-1 granite file is void because of tunnel
  failures, not used), seed-oss-36b, nemotron-3-super. Each is downloaded only after the previous one is deleted.
- Between models, the Hugging Face cache (`HF_HOME`, hub and xet) is cleared, and free disk is checked and logged. If
  free disk is below the next model's size plus 20 GB, that model is not run and the shortfall is reported. There is
  no improvised workaround.
- Before labeling, a health probe goes through the SSH tunnel (`GET /health` and one `/v1/models` call via the
  tunnel port). If the probe fails, that model is aborted and recorded as `tunnel_probe_failed`. After labeling, any
  transport error (connection refused/reset) marks that model's run transport-tainted and reported, not a measurement.
- Results are scored with the same scorer on P, then archived to the VPS with SHA256SUMS and `sha256sum -c`.
