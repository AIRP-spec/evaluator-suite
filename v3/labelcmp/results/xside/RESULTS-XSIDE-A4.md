# Cross-side results under AMENDMENT-4 (test side): HP rows narrowed

Rule: `AMENDMENT-4-HP-ROWS-NARROWED.md`, committed `f1ad6684` before this run. Recomputed from the stored
label files (trio labels and the stored qwen3 adjudication) with `python3 -m airp_v3.xside combine-test-a4`.
No pod, no new labeling, no item text viewed, nothing adjudicated by the agent. Counts and ids only.

- Inputs: A3 combined `089ecbde…` (reproduced bit-for-bit before the run), A2 combined (disputed-marked)
  `2e11dd6a…`. Output: combined A4 `94c542ae…` (box/VPS only); report `report-test-a4.json`; per-row ids and
  changes `A4-HP-ROWS-test.tsv`.

## Status
- primitive_majority 5627, hp_fire_stands_a4 47, adjudicated 34, needs_adjudication 10 (same 10 ids as A3).
- The 47 HP rows: all have 3 valid labels and no tie in the majority, so every base is the primitive majority.
- Standing HP fires unchanged: CSE 36, self_harm 11. Standing fires that fail to compose: 0.
- Inconsistent rows (final classes ≠ composition of final primitives): **0**.

## Overlay changes on the 47 rows (from the HP labeler; nothing else taken from it)
| change | rows |
|---|---|
| CSE: add object `sexual_activity` | 29 |
| CSE: add qualifier `subject_is_minor` | 31 |
| CSE: drop `is_mention_not_use` (majority describes + mention would suppress) | 2 |
| CSE: stance describes → conveys_method (mention gate, labeler also carried mention) | 1 |
| self_harm: add object `self_harm` | 5 |
| self_harm: stance describes → conveys_method | 5 |
| self_harm: stance describes → endorses | 2 |

The stance and mention-gate changes (10 row-changes) are the recorded interpretation in AMENDMENT-4 §2: without
them 10 standing fires would not compose.

## Final class counts, all 5,718 test rows
| class | A2 | A3 | A4 | A4−A2 | A4−A3 |
|---|---|---|---|---|---|
| child_sexual_exploitation | 1 | 36 | 36 | +35 | 0 |
| criminal_assistance | 183 | 179 | 164 | −19 | −15 |
| hate | 20 | 55 | 29 | +9 | −26 |
| persona_claims | 10 | 8 | 8 | −2 | 0 |
| profanity | 2 | 27 | 2 | 0 | −25 |
| relational_hooks | 2 | 2 | 2 | 0 | 0 |
| self_harm | 4 | 36 | 12 | +8 | −24 |
| sexual_content | 1 | 8 | 7 | +6 | −1 |
| simulation_obscured | 46 | 57 | 57 | +11 | 0 |
| sycophancy | 2 | 2 | 2 | 0 | 0 |
| violence | 52 | 77 | 52 | 0 | −25 |

On the 47 HP rows alone: A3 carried CSE 36, criminal_assistance 25, hate 27, profanity 25, self_harm 35,
sexual_content 6, violence 30; A4 carries CSE 36, criminal_assistance 10, hate 1, self_harm 11,
sexual_content 5, violence 5 (A2: CSE 1, criminal_assistance 10, hate 1, persona_claims 2, self_harm 3,
violence 5).

## Disputed marking
- The rule is unchanged (`disputed` = a labeler fired the class and the final label does not carry it).
- Counts: A3 self_harm 30, CSE 0. A4 self_harm **54**, CSE 0. Rows whose marking differs from A3: 24.
- All 24 are CSE-standing rows where qwen3 (gold self_harm precision 0.7273, below 0.95) also fired
  self_harm. Under A3 that low-precision fire rode in with qwen3's full primitive set. Under A4 it is not a
  standing fire, so it is not overlaid; the stored qwen3 adjudication label for each of the 24 carries no
  self_harm, so the fire is overturned and the row is disputed for self_harm. (AMENDMENT-4 said "expected 0";
  that expectation was wrong, the rule was not changed.)

## Train side
No HP safety fire exists on the train side (no CSE fire; nemotron and seed-oss are below 0.95 on self_harm), so
AMENDMENT-4 changes nothing there.
