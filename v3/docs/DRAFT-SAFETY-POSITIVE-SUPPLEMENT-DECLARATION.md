# Safety-positive supplement declaration (SIGNED)

> **Signed and in force.** Justin signed the amended declaration in t207u (2026-11-01 19:35 NPT): "Supplement declaration signed as amended. Pod one may start after item 1's pod is done." This committed copy with the signature block below is the authorization for S1 and the later gates.

- **Signed date:** 2026-11-01 19:35 NPT (amended with source S-MIN; signature recorded 2026-11-01 after guide-reader pod completed)
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
- **Source S-MIN (added 2026-11-01, Justin t206u): benign collected outputs filtered for minor
  markers.**
  - **Pool:** v3 test-side collected outputs with `prompt_kind = benign` (oasst2-firstturn and
    xstest benign prompts), writers phi-4, granite-4.2-8b, seed-oss-36b and nemotron-3-super, at
    both caps (3,028 rows; source files sha-pinned in `xside.SOURCES["test"]`). Train-role
    outputs are excluded (train/test overlap); the trio writes those itself, except glm-4.5-air
    (76 marker hits, excluded for role, information only).
  - **Marker filter** (code: `v3/airp_v3/minor_supplement.py`, `AGE_KEYWORDS`, `SCHOOL_KEYWORDS`,
    `REGEXES`; whole-word, case-insensitive; only generic age and school terms, per guide settled
    rules 5 and 6). Text is scanned in memory only, never printed, logged or written.
    - Age keywords (25): child, children, kid, kids, toddler(s), infant(s), baby, babies, teen(s),
      teenager(s), preteen, pre-teen, adolescent(s), minors, underage, under-age, juvenile(s),
      youngster(s).
    - School keywords (22): kindergarten, preschool, pre-school, nursery school, elementary school,
      primary school, middle school, junior high, high school, secondary school, grade school,
      classroom, classmate(s), schoolchild, schoolchildren, schoolkid(s), pupil(s), homework, recess.
    - Regexes (7): numeric age 1–17 with "year(s) old"; "age/aged" + 1–17; ordinal grade 1st–12th
      ("5th grade", "3rd-grader"); "grade" + 1–12; spelled-out first–twelfth grade(r); "a minor" as a noun (followed by punctuation or who/under/is/was/in/or/and, so not "a minor issue");
      "under 13/16/18" (digits or words).
  - **Label screen (mechanical, before any labeling):** a marker hit is dropped unviewed and
    listed by id if any stored trio label carries object `sexual_activity` or composes
    `child_sexual_exploitation`, `sexual_content` or `self_harm`.
  - **Labeling:** the test-side trio (mistral-small-3.2, gemma-4-31b, qwen3-30b-a3b-2507) re-labels
    every remaining candidate under the guide pinned at signature, combined under AMENDMENT-3 as
    narrowed by AMENDMENT-4, qwen3 adjudicating. Positives (`subject_is_minor` in the final
    primitives) are kept. One row per prompt × writer counts toward the target (the cap-1500
    sample where both caps qualify).
  - **Composition check (mechanical):** every kept positive must compose no
    `child_sexual_exploitation` and carry no `sexual_activity` from any labeler; a row failing
    it is removed unviewed and listed by id. Unit test: CSE never composes on a kept row.
  - **Target:** 120 unique prompt × writer positives. Report the shortfall if not met.
  - **Counts now (code only, stored labels, guide `5b2908ba`, AMENDMENT-4 combine):**
    - Marker hits in the benign pool: 275 rows.
    - Dropped by the label screen: 21 rows (ids only).
    - Candidates: 254 rows (oasst2 206, xstest 48), 171 unique prompt × writer. By writer and cap:
      nemotron 43 / 47, seed-oss 41 / 40, granite 32 / 27, phi-4 11 / 13 (cap 800 / 1500).
    - Trio labelers marking `subject_is_minor` on a candidate: 0 of 3 on 168, 1 on 66, 2 on 12,
      3 on 8.
    - Stored-label positives (final primitives carry `subject_is_minor`): 20 rows, 13 unique
      prompt × writer.
  - **Expected yield:** the stored labels predate the signature guide, and the labelers
    under-apply settled rule 6 (a school marker alone is `subject_is_minor`). Even so, 120
    needs at least 120 of the 171 unique candidates (70%) to come out positive after
    re-labeling. A shortfall is likely; it is reported, and widening the pool needs a new
    signature.
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
| S2 elicitation + S-MIN | 2 writers × ~118 × 8 samples (~1,900 outputs), plus 3 labelers (+ qwen3 adjudication); the same loaded trio also re-labels the 254 S-MIN candidates (~+5 min) | ~70 min, ~$2.90 | $4 / 90 min |
| CSE side | no pod: mechanical selection from stored labels (sexual_activity adult set, S-MIN filter and label screen) | $0 | — |

If S2 is not approved, S-MIN alone is one pod (three model loads plus 254 rows × 3 labelers and
adjudication): ~30 min, ~$1.25, cap $4 / 90 min.

All pods use an RTX PRO 6000 SECURE at $2.49/h. Cumulative GPU spend was **$22.20** after xside-2; **$22.99** after greader-1 (ledger) at signature recording.
- The supplement is estimated at **~$5.00** (S1 $2.10 + S2 $2.90) and capped at **$8**
  (two pods × $4). The cap alone would cross the $30 stop ($22.20 + $8 = $30.20), so the gate
  below binds.
- **Gate:** S2 does not start if cumulative spend after S1 is above $25.50, so that the S2
  cap cannot cross the $30 stop. Expected cumulative: ~$24.30 after S1, ~$27.20 after S2.
  The $25 reporting threshold will be crossed and reported.

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
- For S-MIN: marker hits, label-screen drops (ids), candidates, positives after re-labeling
  (rows and unique prompt × writer), and the shortfall against 120.
- Spend: each pod's ledger row, cumulative spend and balance.

## Signature
- Signed: Justin Flores (per owner message t207u, 2026-11-01 19:35 NPT: "Supplement declaration signed as amended. Pod one may start after item 1's pod is done.")
- Date: 2026-11-01 19:35 NPT (signature recorded in this commit)
- Guide sha pinned: e5b7b56cd466b2f503ad15178ef1b1b8d44a1dde20523898546ed3c4ceca6aa6 (v3/LABELING-GUIDE.md at signature)
- Composition sha pinned: 59ddf1f630ec2dcd81d40dd01f2adb53f1310fe42128d3ccc9b90de61e28ab9e (composition 2a)
- Cumulative GPU spend at signature recording: $22.99 (after greader-1); S2 gate unchanged ($25.50 after S1).
