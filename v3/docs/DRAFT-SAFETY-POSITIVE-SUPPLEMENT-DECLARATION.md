# DRAFT, UNSIGNED, NOT IN FORCE: safety-positive supplement declaration

> **This file is a draft for Justin's signature.** Nothing in it is authorized. No pod,
> generation, labeling or scoring under it may start until Justin signs a committed copy
> of this file with the signature block filled in. Until then it binds nothing.

- **Draft date:** 2026-11-01
- **Purpose:** provide gateable safety-recall positives that v3 as collected does not
  have (see `ADR-v3-SCOPE-DRAFT.md`).

## 1. self_harm: targeted elicitation
- **Prompts:** the self-harm prompt category on the test side only:
  - ailuminate-demo hazard `ssh` (98 prompts);
  - simplesafetytests self-harm rows (about 20).

  These are deduplicated against every train-side prompt by exact and normalized match.
  No new prompts are written.
- **Writers (the weakest-compliance models, chosen by a declared pilot rather than by v3
  scores):**
  - Candidates are self-host roster models outside the labeler families (mistral, gemma,
    qwen): granite-4.2-8b, phi-4, glm-4.5-air and seed-oss-36b.
  - Pilot: each candidate gives 2 samples on each prompt. gemma-4-31b labels the pilot
    (gold self_harm precision 1.0).
  - The **2 candidates with the highest self_harm-compose rate** are the writers. Ties go
    to the smaller model.
- **Sampling:** each writer gives 8 samples per prompt at temperature 1.0, max_tokens 800,
  with its own chat template, a single user turn and no system prompt. There are no
  jailbreak wrappers, no prompt edits and no iterative search.
- **Kept outputs:** every output is kept. An output that labels as complying (it composes
  to self_harm) is flagged `elicited_compliant`. Flagged rows stay box/VPS-only, are never
  committed, and are reported as counts and ids only.
- **Labels:** the AMENDMENT-2 test trio (mistral-small-3.2, gemma-4-31b, qwen3-30b-a3b-2507)
  under the guide pinned at signature, combined under AMENDMENT-3. Justin adjudicates every
  queued row. The agent adjudicates none.
- **Target:** 120 standing self_harm positives after adjudication. If the target is not
  met, report the shortfall. Do not run a second elicitation round without a new
  signature.

## 2. CSE: compositional check, nothing elicited
CSE = `subject_is_minor` ∧ `sexual_activity` (composition 2a). No CSE content is
generated, elicited, sought or viewed.
- **≥120 `subject_is_minor` positives on non-sexual text:**
  - Sources are existing benign test-side text about minors, such as human-written
    oasst2 assistant replies on parenting or school.
  - The text is screened mechanically to contain no `sexual_activity` by any labeler.
  - Candidate count already on the test side: 51 rows (both caps counted) have a
    labeler-majority `subject_is_minor` with no `sexual_activity` fire, so more sources
    are needed.
- **≥120 `sexual_activity` positives on adult text:**
  - Sources are existing test-side adult text with no minor marker from any labeler.
  - Candidate count already on the test side: 129 rows, before dedup and adjudication.
- **Composition check (mechanical):**
  - Unit tests assert that CSE fires iff both primitives are present, under every stance
    except describes + is_mention_not_use.
  - On the supplement, CSE must compose on zero rows; any row that composes CSE is
    removed unviewed and listed by id.
  - CSE recall is reported as the product bound of the two primitive recalls, with that
    assumption stated.
- Any row any labeler flags with both primitives is dropped without viewing and listed
  by id.

## 3. Pods, costs and caps
One pod at a time. The headroom check runs first and both watchdogs run. Each pod is capped
at $4 and 90 minutes. A pod is terminated within 15 minutes of any failure, and archived
(manifest plus `sha256sum -c`) before termination.

| Pod | Work | Estimate | Cap |
|---|---|---|---|
| S1 pilot | 4 writers × ~118 prompts × 2 samples, plus gemma labeling | ~50 min, ~$2.10 | $4 / 90 min |
| S2 elicitation | 2 writers × ~118 × 8 samples (~1,900 outputs), plus 3 labelers (+ qwen3 adjudication) | ~65 min, ~$2.70 | $4 / 90 min |
| CSE side | no pod: mechanical selection from stored labels; extra benign text is labeled on S2 if needed | $0 (or +10 min on S2) | inside the S2 cap |

All pods use an RTX PRO 6000 SECURE at $2.49/h. Cumulative GPU spend is about $21.9 after
xside-2.
- The supplement is estimated at **~$4.80** and capped at **$8**.
- **Gate:** S2 does not start if cumulative spend after S1 is above $25.50, so that the S2
  cap cannot cross the $30 stop. The $25 reporting threshold will be crossed and reported.

## 4. Gates (each needs Justin)
1. Justin signs this file (block below). Commit it, then verify with `git ls-remote`.
2. Report after S1: pilot compose rates per candidate (counts only) and the two writers
   chosen. Justin approves S2.
3. Report after S2: the adjudication queue size and counts by trigger. Justin adjudicates.
4. Rules for the recall score are committed before any supplement scoring. The supplement
   is never mixed into v3 train.

## 5. What is reported
- Counts, ids and shas only. No item text from any safety class appears in any report,
  commit or file outside box/VPS storage.
- Reported per writer: outputs, `elicited_compliant` count, queue size by trigger,
  standing positives after adjudication, and the shortfall against 120.
- For CSE: counts per primitive positive set, the composition-test result, and dropped ids.
- Spend: each pod's ledger row, cumulative spend and balance.

## Signature
- Signed: ____________________ (Justin Flores)
- Date: ________
- Guide sha pinned: ________
- Composition sha pinned: ________
