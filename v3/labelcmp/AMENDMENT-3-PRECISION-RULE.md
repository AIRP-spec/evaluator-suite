# Amendment 3: high-precision safety fires stand; primitives-only decisions; disputed classes

Decided by Justin, 2026-11-01 17:53 NPT (t207u). This file is committed **before the rules are applied** to any
stored label or to the train-side queue. It amends AMENDMENT-2 (`7b210db4`); where they conflict, this file governs.
Pins are unchanged. Code: `v3/airp_v3/xside.py` (`decide_test_a3`, `combine_test_a3`, `train_queue_a3`,
`combine_train_a3`, `mark_disputed_a2`) and `v3/airp_v3/score.py` (`disputed_classes`). Tests: `v3/tests/test_xside.py`.

## 1. Disputed classes (B1)

- On the AMENDMENT-2 test-side outputs, a row where a labeler fired self_harm or child_sexual_exploitation and
  adjudication overturned the fire is marked `disputed` for that class (`disputed_classes`).
- AMENDMENT-2 sent 36 CSE rows to adjudication; 1 stood and 35 were overturned. It sent 66 self_harm rows; 4 stood
  and 62 were overturned.
- Under §2 below, `disputed` means: a labeler fired the class, and the final label does not carry it.
- **Scoring:** an item whose gold carries `disputed_classes` is excluded from scoring on each listed class: no tp,
  fp or fn on that class, and no self_harm primitive miss when self_harm is disputed. Its other classes are scored
  normally. The scorer reports `disputed_excluded_by_class`.

## 2. Precision rule (B2)

- A safety fire (child_sexual_exploitation or self_harm) from a labeler whose **gold precision on that class is
  ≥ 0.95** stands, unless guide-based adjudication records a **mention** or **refusal** reason for that row and class.
- **The third labeler adds recall only.** qwen3's adjudication output cannot remove a standing high-precision fire.
  A fire from a labeler below 0.95 on that class does not stand on its own; it goes to guide-based adjudication.
- **Gold precisions** (P = 853, PER-CLASS-labcmp-1/2.tsv; pinned in `GOLD_PRECISION`):

  | labeler | CSE | self_harm |
  |---|---|---|
  | mistral-small-3.2 | 1.00 HP | 1.00 HP |
  | gemma-4-31b | 1.00 HP | 1.00 HP |
  | qwen3-30b-a3b-2507 | 0.9677 HP | 0.7273 |
  | nemotron-3-super | 0.9841 HP | 0.8889 |
  | seed-oss-36b | 1.00 HP | 0.2051 |

  qwen3, nemotron and seed-oss all clear 0.95 on CSE, so their CSE fires are high-precision under the rule as worded.
- **Test side:** no mention or refusal reason is recorded yet (qwen3 adjudication records no reasons). Every
  high-precision fire therefore stands. If such reasons are recorded later, they go in a reasons file
  (`id, class, reason`), and the combine is re-run.
- **Train side:** queue triggers are:
  - `hp_fire_stands_unless_mention_or_refusal:<class>`: the adjudicator records only whether a mention or refusal
    reason applies;
  - `lp_fire:<class>`: full guide-based adjudication;
  - `class_disagreement`, `primary_invalid`, `second_invalid`: as before.

  Rows with no trigger take the primary's primitives. Justin adjudicates the queue; the executor never does.

## 3. Primitives only; no class vote (B3)

- Every final label is a **primitives** label. All classes are derived from it through composition 2a. There is no
  separate class vote, so final primitives and final classes are consistent by construction.
- **Test-side decision, per row:**
  1. If a high-precision fire stands (§2), the final primitives are those of the highest-ranked labeler (mistral,
     gemma, qwen3) that fired a standing class.
  2. Otherwise, take a primitive-level majority over the valid outputs: stance by plurality, each object and
     qualifier by a strict majority. Invalid outputs abstain. A tie on the stance or on any primitive, fewer than two
     valid outputs, or a low-precision safety fire sends the row to adjudication. The stored qwen3 adjudication label
     is used where one exists. Otherwise the row is `needs_adjudication`: it is listed by id, unscored, and not
     adjudicated by the executor.
- Everything is recomputed from the stored label files. No new labeling and no item text is needed. Rows flagged
  CSE are never opened. Only ids are listed.

## 4. Reporting

Counts and ids only. The report gives AMENDMENT-2 vs AMENDMENT-3 counts for test-side final classes,
disputed-by-class, statuses, and the train-side queue by trigger.
