# Cross-side results under AMENDMENT-3 (test side) and the B4 relational_hooks rescore

All numbers come from stored labels. No item text was viewed for B1–B3, no row was
adjudicated by the agent, and no pod was used. The files here hold counts and ids only.

## B1: disputed rows (A2)
- An A2 test-side row where a safety fire was overturned in adjudication is marked `disputed`
  for that class. It is excluded from v3 scoring on that class only, by `score.py` through
  `disputed_classes`.
- Disputed under A2: self_harm 62, CSE 35.
  - Of the 36 CSE rows sent to adjudication, 1 stood.
  - Of the 66 self_harm rows sent, 4 stood.
- Disputed under A3: self_harm 30, CSE 0.
- Files: `DISPUTED-COUNTS.json`, `DISPUTED-IDS-test.tsv`.

## B2/B3: AMENDMENT-3 on the stored test-side labels
- **Status:** primitive_majority 5627, hp_fire_stands 47, adjudicated (stored qwen3
  adjudication) 34, needs_adjudication 10. The 10 ids are in the report.
- **Standing HP fires:** CSE 36, self_harm 11.
- **Inconsistent rows:** 0. Classes now come only from composed primitives; there is no
  separate class vote.
- **Final class counts, A2 → A3:**

| Class | A2 | A3 |
|---|---|---|
| criminal_assistance | 183 | 179 |
| violence | 52 | 77 |
| simulation_obscured | 46 | 57 |
| child_sexual_exploitation | 1 | 36 |
| hate | 20 | 55 |
| profanity | 2 | 27 |
| self_harm | 4 | 36 |
| sexual_content | 1 | 8 |
| persona_claims | 10 | 8 |
| sycophancy | 2 | 2 |
| relational_hooks | 2 | 2 |

- **Side effect.** On the 47 rows where a high-precision fire stands, A3 takes that labeler's
  full primitive set. That also adds these classes: hate +26, violence +25, profanity +25,
  criminal_assistance +15, sexual_content +6. It removes persona_claims on 2 rows.
- **Alternative for Justin.** On those rows, keep the majority primitives and add only the
  minimal safety primitives.

The guide-based "mention or refusal" override has no stored reasons yet. It is applied only
when Justin's adjudication records one (`combine-test-a3 --reasons`).

## B4: relational_hooks rescore (guide 5b2908ba → e5b7b56c)
This rescores *stored* labcmp-1 outputs, which were produced under guide 5b2908ba.
Before and after are identical by construction, because no labeler was re-run.

| Labeler | Gold as-is R / P | Sensitivity: rh-denial as negative, R / P |
|---|---|---|
| mistral-small-3.2 | 0.425 / 0.708 | 0.800 / 0.667 |
| gemma-4-31b | 0.425 / 0.895 | 0.800 / 0.842 |
| qwen3-30b-a3b-2507 | 0.175 / 0.127 | 0.350 / 0.127 |

- **Gold finding:**
  - 20 of the 40 gold RH positives are kind `rh-denial`.
  - Their source scaffold, `inference-advocate tools/evaluator-training/recipe.json`
    group `rh-denial-vs-hook`, declares them `class: null, expect: []`. In other words,
    they are **not** hooks.
  - The gold primitives (encourages + directed_at_user) contradict the source.
  - The labelers missed 19, 19 and 20 of these rows, which is most of the "recall < 0.45".
  - The gold has not been changed. Correcting it is Justin's call.
- **Rows that need re-labeling under the revised guide** are listed by id in
  `rh-relabel-flags.tsv`, scored against the sensitivity gold:
  - mistral: 4 misses, 8 false fires;
  - gemma: 4 misses, 3 false fires;
  - qwen3: 13 misses, 48 false fires, 45 of them on safety-kind gold rows.
