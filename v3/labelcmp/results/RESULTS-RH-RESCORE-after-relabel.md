# RH rescore after re-label pod (Justin t208u)

Guide `e5b7b56c`. Re-labeled 72 flagged gold ids from `rh-relabel-flags.tsv`.
Baseline = labcmp-1/2 stored labels; overlay = new valid labels only (invalid re-label keeps baseline).
Gold = `gold-revised-overlay` (rh-denial pure-denial; RH positives = 20 rh-hook).
Pod `kf1vp33i42uqup` 18.9 min $0.784; all five complete; transport errors 0.

| Labeler | Before R / P | After R / P | n_overlaid / 72 |
|---|---|---|---|
| mistral-small-3.2 | 0.800 / 0.667 | 1.000 / 0.741 | 72 |
| gemma-4-31b | 0.800 / 0.842 | 0.950 / 1.000 | 72 |
| phi-4 | 0.450 / 0.750 | 0.550 / 0.688 | 41 |
| granite-4.2-8b | 0.350 / 0.875 | 0.800 / 0.800 | 47 |
| qwen3-30b-a3b-2507 | 0.350 / 0.127 | 0.900 / 0.281 | 72 |

Valid rates on the 72: granite 47, phi-4 41, mistral/qwen3/gemma 72.
Artifacts: `out-rh-relabel/` (VPS `v3-labcmp-20261101/out-rh-relabel-1`, sha256sum -c OK), `RH-RESCORE-after-relabel.json`.
