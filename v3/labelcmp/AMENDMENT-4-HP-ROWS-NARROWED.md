# Amendment 4: high-precision rows take the majority plus only the safety primitives

Decided by Justin, 2026-11-01 18:36 NPT (t206u). This file and its code are committed **before the rule is
applied** to any stored label. It amends AMENDMENT-3 (`6d1e80b4`) §3 step 1 only; everything else in AMENDMENT-3
(disputed marking, the 0.95 precision rule, "third labeler adds recall only", the train-side triggers) is
unchanged. Pins are unchanged (composition 2a `59ddf1f6…`, guide as in AMENDMENT-3).
Code: `v3/airp_v3/xside.py` (`a4_overlay`, `decide_test_a4`, `combine_test_a4`, CLI `combine-test-a4`).
Tests: `v3/tests/test_xside.py` (`test_a4_*`).

## The narrowing

AMENDMENT-3 §3.1 gave a row where a high-precision (HP) safety fire stands the **full** primitive set of the
highest-ranked HP labeler that fired. That imported the labeler's non-safety primitives too. AMENDMENT-4 replaces it:

1. **Base** = the primitive-level majority of the three test-side labels (AMENDMENT-3 §3.2 procedure: stance by
   plurality, each object and qualifier by strict majority, invalid outputs abstain). If the base itself has a tie,
   the stored qwen3 adjudication label is the base; if none exists the row is `needs_adjudication` (listed by id,
   not adjudicated by the executor).
2. **Overlay**, for each standing class, from the highest-ranked HP labeler that fired that class: add **only**
   the primitives composition 2a reads for that class, nothing else from that labeler.
   - `child_sexual_exploitation`: object `sexual_activity` and qualifier `subject_is_minor` (the rule is
     stance-free).
   - `self_harm`: object `self_harm`; and the labeler's stance **only if** the base stance is not one of the
     self_harm rule's stances (`endorses`, `encourages`, `conveys_method`).
   - Suppression gate: composition 2a's only negative rule suppresses every class when the stance is `describes`
     and `is_mention_not_use` is present. If the overlaid base would be suppressed and the HP labeler's label is
     not, `is_mention_not_use` is dropped from the base when the labeler lacks it (otherwise the labeler's stance
     is taken).
   - Interpretation recorded for Justin: the stance and the mention gate are treated as "safety primitives" only
     where they are needed for the standing fire to compose. Without them a standing fire would not compose on
     some rows and would be lost, contradicting AMENDMENT-3 §2. Every such change is logged per row
     (`a4_changes`) and counted in the report.
3. **Classes** are derived from the final primitives through composition 2a. There is no class vote, so
   inconsistent rows stay at 0 by construction (the report re-checks it).
4. **Disputed marking** is unchanged: `disputed` = a labeler fired the class and the final label does not carry
   it. Because every standing fire is made to compose, the A4 disputed set equals the A3 disputed set; the report
   counts any row whose marking differs from A3 (expected 0).

## Scope

- Test side only. On the train side no row has an HP safety fire (no CSE fire from either labeler; neither
  nemotron, 0.8889, nor seed-oss, 0.2051, is HP on self_harm), so AMENDMENT-4 changes nothing there.
- Rows that are not `hp_fire_stands` under AMENDMENT-3 are decided exactly as under AMENDMENT-3 (test
  `test_a4_non_hp_rows_identical_to_a3`).
- Recomputed from the stored label files only. No pod, no new labeling, no item text viewed. Counts and ids only.

## Reporting

`results/xside/report-test-a4.json` and `RESULTS-XSIDE-A4.md`: status counts, per-class final counts with deltas
versus AMENDMENT-2 and AMENDMENT-3 (all rows, and the HP rows alone), counts of each overlay change, standing
fires that fail to compose (expected 0), disputed-by-class, inconsistent rows.
