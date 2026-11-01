# Amendment 2: cross-side labeling rules (test side and train side)

Decided by Justin, 2026-11-01 16:00 NPT (t206u). Committed **before any cross-side labeling run**. Amends
`DECLARATION-LABELER-COMPARISON.md` (`ba8323be`) and `AMENDMENT-1-THREE-LABELERS.md` (`3278558c`). Where they
conflict, this file governs. Pins are unchanged: guide `5b2908ba…5f21`, composition 2a `59ddf1f6…`,
POLICY_VERIFIED `9f49db7f…`. Nothing here scores on v3 rows or on the held-out suite. The cross-side labels are
training/evaluation *labels*, not scores.

Code: `v3/airp_v3/xside.py` (tests: `v3/tests/test_xside.py`). Labeling itself is the existing
`airp_v3.label_local` (POLICY_VERIFIED gate, OpenAI refusal, self-hosted base URL only, same-family skip).

## 1. Test side (test-role text, labeled by train-role labelers)

"Third labeler" means the trio's **third-ranked** labeler (Justin). Trio in rank order, from labcmp-1:
**mistral-small-3.2, gemma-4-31b, qwen3-30b-a3b-2507**. **qwen3-30b-a3b-2507 adjudicates.**

- All three label every row; the AMENDMENT-1 rules then apply.
- **child_sexual_exploitation, self_harm:** if any of the three fires the class on a row, the row goes to adjudication
  by qwen3 with the full labeling guide. The adjudicated output decides that class on that row.
- **All other classes:** majority of three; the guide breaks ties through the same adjudication.
- **Invalid outputs** (resolving the AMENDMENT-1 wording, whose own example is "an invalid output leaves a 1–1
  split"): an invalid output abstains. Majority is taken over the valid outputs, so with one invalid output a 1–1 split
  is a tie and goes to adjudication. A row with fewer than two valid outputs goes to adjudication for every class. A
  primitive-level stance tie (three different stances) also goes to adjudication. Every invalid output is reported
  by id; none is resampled silently. Transport errors (no model output) are re-run in a later pod, not treated as
  invalid.
- **Adjudication call:** qwen3 (same served model, same pins) gets the labeler system prompt plus the full guide plus
  a fixed adjudication paragraph (`ADJ_SUFFIX` in `xside.py`). The user turn is the item, then the three candidate
  labels as primitives JSON, anonymised as Labeler A/B/C in rank order. It returns one primitives label (no free text
  is requested). Same-family adjudication is refused in code.
- **Final row:** classes come from the rule above (adjudicated classes from the adjudicator's composed classes; the
  rest from the majority). Final primitives are the primitive-level majority on unadjudicated rows and the
  adjudicator's primitives on adjudicated rows. Rows whose final primitives do not compose to the final classes are
  flagged `primitives_consistent=false` and counted in the report. An invalid adjudicator output leaves the row
  unresolved, listed by id.

## 2. Train side (train-role text, labeled by test-role labelers)

**Reason:** only two cross-side labelers are eligible (nemotron-3-super 0.8159, seed-oss-36b 0.7819 class-set exact;
granite and phi-4 fail the 0.95 valid-output floor). GLM-4.5-Air is a train-side (own-side) model, so it is not used.
A trio is not possible, so the rule is a pair plus adjudication against the guide.

- **nemotron-3-super is primary; seed-oss-36b is second.** Both label every row.
- A row goes to adjudication if the two composed class sets differ, if either output is invalid, or if either labeler
  fires **self_harm** or **child_sexual_exploitation**.
- All other rows (both valid, same class set, no safety fire) take the primary's label.
- **Adjudicator: Zimmer**, against the labeling guide, with a one-line reason per row, stored by id only. The executor
  (the subagent running pods) never adjudicates any v3 row. It only writes the queue: ids, both labelers' primitives
  and classes, trigger reasons, and a `cse_fire` flag. **No item text.**
- If a row appears to need CSE-exhibiting content to adjudicate, the adjudicator stops on that row, lists its id, and
  does not view or reproduce it.

## 3. Data (existing filtered, deduplicated prompt-set outputs; no new collection)

Item ids are `<collection id>@cap<800|1500>`, so the two test-side caps never collide. Item files are box-local only
and are never committed.

| side | source | rows | sha256 |
|---|---|---|---|
| test | out800-derived/phi-4 | 715 | `04385676…` |
| test | out800-derived/granite-4.2-8b | 714 | `3702feddc…` |
| test | out800-derived/seed-oss-36b | 715 | `ba634fa9…` |
| test | out800-derived/nemotron-3-super | 715 | `503f3f29…` |
| test | out1500/phi-4 | 715 | `1a658924…` |
| test | out1500/granite-4.2-8b | 714 | `f451c629…` |
| test | out1500/seed-oss-36b | 715 | `43d1ecb3…` |
| test | out1500/nemotron-3-super | 715 | `ea013c51…` |
| train | out800-derived/gemma-4-31b | 1431 | `a9871b3d…` |
| train | out800-derived/glm-4.5-air | 1430 | `1f5f5fe9…` |
| train | out800-derived/mistral-small-3.2 | 1431 | `708d24e2…` |
| train | out800-derived/qwen3-30b-a3b-2507 | 1431 | `6eccb723…` |

Test: 5,718 items (2,859 at the 800 cap and 2,859 at the 1,500 cap), items sha `5e13f235…`. Train: 5,723 items, items
sha `b7844702…`. Full shas are in `xside.SOURCES`. out800-derived is `tools/flag_collected.py` @6163d6e (reasoning
stripped, flags added; `sha256sum -c` OK). The same-family skip has no effect here, because no labeler shares a family
with a writer on the side it labels.

## 4. Pods

The existing machinery (`labcmp2_pod.py` pattern) is used. One pod at a time. Headroom check first (no running pods,
balance ≥ $10, cumulative GPU + $4 ≤ $30, disk). Caps are $4 and 90 minutes per pod, with both watchdogs. A tunnel
health probe runs before each model, and caches are cleared between models (with a df check). Outputs are archived to
the VPS with SHA256SUMS and `sha256sum -c` before terminate. A pod is terminated within 15 minutes of any failure.
STATUS-RESUME.md and SPEND-LEDGER.tsv are updated after every step.

Order: test trio (mistral, gemma, qwen3, then qwen3 adjudication while still served), then train side (nemotron,
seed-oss). A model is started only if the pod has time left for it; leftovers move to the next pod. Report after the
first pod, whenever cumulative GPU crosses $25, and stop at $30.

Committed outputs are counts and ids only (reports, the queue without text). Raw label files carry `meta.raw_text` and
go to the VPS only.
