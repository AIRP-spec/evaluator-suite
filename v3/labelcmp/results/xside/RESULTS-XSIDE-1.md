# Cross-side labeling, pod xside-1 (AMENDMENT-2, `7b210db4`)

Counts and ids only. No item text is included. Pod `xaoda0meuo1imm`, RTX PRO 6000 SECURE, $2.49/h, ran 16:07–17:30 NPT
(82.2 min), cost $3.413. Raw label files (they carry `raw_text`) are on the VPS only:
`v3-xside-20261101/out-xside-1` (16/16 `sha256sum -c` OK) and `final-xside-1` (4/4 OK).

## Labeled rows by side

| side | labeler | written | valid | invalid | transport errors |
|---|---|---|---|---|---|
| test (5,718 = 2,859 @800 + 2,859 @1500) | mistral-small-3.2 | 5718 | 5715 | 3 | 0 |
| test | gemma-4-31b | 5718 | 5710 | 8 | 0 |
| test | qwen3-30b-a3b-2507 | 5718 | 5717 | 1 | 0 |
| test | qwen3 adjudication | 81 | 81 | 0 | 0 |
| train (5,723) | nemotron-3-super | 5723 | 5723 | 0 | 0 |
| train | seed-oss-36b | 0 | – | – | – (not run: pod time; next pod) |

The same-family skip skipped 0 rows (no labeler shares a family with a writer on the side it labels).

## Test side: final (AMENDMENT-2 §1)

- 5,718 rows fully labeled. 5,637 were decided by majority and 81 adjudicated by qwen3. 0 unresolved.
- Adjudication triggers: any_fire child_sexual_exploitation 36, any_fire self_harm 66, tie hate 1, stance tie 2.
- Adjudicated outcomes: CSE fired 1/36, self_harm fired 4/66, hate fired 1/1. Both stance ties ended with no class.
- Final class counts: criminal_assistance 183, violence 52, simulation_obscured 46, hate 20, persona_claims 10,
  self_harm 4, profanity 2, sycophancy 2, relational_hooks 2, sexual_content 1, child_sexual_exploitation 1.
- 47 rows have final primitives that do not compose to the final classes (`primitives_consistent=false`).
- Top 5 disagreement shapes (class sets per labeler, mistral | gemma | qwen3):
  1. {criminal_assistance} | {} | {}: 125
  2. {criminal_assistance} | {} | {criminal_assistance}: 103
  3. {} | {} | {criminal_assistance}: 53
  4. {hate} | {} | {}: 50
  5. {} | {} | {sycophancy}: 36
- Per-row adjudication record, by id only: `ADJUDICATION-test-xside-1.tsv`.

## Train side

nemotron-3-super (primary) labeled all 5,723 rows. seed-oss-36b has not run yet, so the Zimmer queue is not built.
Nemotron composed-class counts (for sizing only): persona_claims 181, sycophancy 146, simulation_obscured 140,
relational_hooks 65, criminal_assistance 38, hate 31, profanity 26, violence 22, sexual_content 11, self_harm 2,
child_sexual_exploitation 0.

## Per-class recall/precision against gold

Gold is P = 853, measured in labcmp-1 and labcmp-2. See `PER-CLASS-labcmp-1.tsv` and `PER-CLASS-labcmp-2.tsv`.
