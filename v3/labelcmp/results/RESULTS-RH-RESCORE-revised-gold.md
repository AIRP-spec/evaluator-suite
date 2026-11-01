# RH rescore against revised gold (Justin t208u pure-denial)

Original gold untouched. Revision: 20 `rh-denial` → describes + is_mention_not_use → no class.
Guide cite: settled rule 1 + §directed_at_user RH counter-example (release/denial of stake in return).
Stored labcmp labels; no pod.

| Labeler | As-is gold R / P | Revised gold R / P |
|---|---|---|
| gemma-4-31b | 0.425 / 0.895 | 0.800 / 0.842 |
| granite-4.2-8b | 0.175 / 0.875 | 0.350 / 0.875 |
| mistral-small-3.2 | 0.425 / 0.708 | 0.800 / 0.667 |
| phi-4 | 0.225 / 0.750 | 0.450 / 0.750 |
| qwen3-30b-a3b-2507 | 0.175 / 0.127 | 0.350 / 0.127 |

Revised gold RH positives: 20 (rh-hook only). rh-denial (20) are negatives.
Artifacts: `gold-revision-rh-denial.jsonl`, `gold-revised-overlay.jsonl`, `RH-RESCORE-revised-gold.json`.
