# ADR (proposed, draft text): what the v3 suite as collected gates

- **Status:** Proposed. This is draft text for Justin's review and is not accepted.
- **Date:** 2026-11-01
- **Branch:** v3/phase1-pipeline (PR #2, draft)

## Context
The v3 collection (prompt shas: test 976843d4…, train 90cc5595…) was labeled across sides
under AMENDMENT-2 and AMENDMENT-3. After adjudication the test side has very few standing
safety positives:

| Class | A2 positives | A3 positives | Fires overturned under A2 (`disputed`) |
|---|---|---|---|
| child_sexual_exploitation | 1 | 36 | 35 |
| self_harm | 4 | 36 | 62 |

Under A3 the remaining disputed fires are self_harm 30 and CSE 0. Most self_harm fires came
from low-precision labelers. A recall estimate on a few dozen positives is too wide to gate on,
and the CSE count depends on which precision rule applies. The collection was never designed
to elicit safety positives, and it must not be. Every v3 prompt was a natural or benchmark
prompt answered by self-hosted models.

## Decision
1. v3 as collected **gates**:
   - recall and precision for every non-safety class: violence, criminal_assistance,
     sexual_content, hate, profanity, persona_claims, relational_hooks, sycophancy and
     simulation_obscured;
   - the **false-positive rate** for both safety classes (CSE and self_harm). Rows
     marked `disputed` for a class are excluded from scoring on that class only.
2. v3 as collected **does not gate safety recall** (CSE or self_harm). Safety recall is gated
   only by a separately declared, signed safety-positive supplement (see
   `DRAFT-SAFETY-POSITIVE-SUPPLEMENT-DECLARATION.md`). Until it is signed and collected, no
   safety-recall claim is made from v3.
3. No v3 or held-out row is used to score before the rules for that score are committed
   (standing rule).

## Consequences
- Reports on v3 show safety-class recall as "not gated (insufficient positives)", not as a
  number.
- The scorer already supports `disputed_classes` (commit 6d1e80b4). The safety FP rate is
  computed on non-disputed rows.
- Any later change to which rows count as safety positives (for example, Justin's
  train-side adjudication) updates the FP-rate denominators, not the decision.
- 2026-11-01 (Justin t209u): the S1 pilot found instruction-tuned writers at about 2% self_harm
  compliance; S2 was cancelled. See `ADR-2026-11-01-s1-method-limit.md` (method limit) and the unsigned
  `DRAFT-S3-BASE-MODEL-PILOT-DECLARATION.md`.
