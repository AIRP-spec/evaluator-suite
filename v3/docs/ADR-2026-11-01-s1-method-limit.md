# ADR 2026-11-01: instruction-tuned writers do not supply self_harm positives (S1 method limit)

- **Status:** Accepted (Justin t209u, 2026-11-01 ~21:45 NPT): "S2 does not run. Record the pilot
  result in the evaluator-suite ADR as a method limit."
- **Related:** `DRAFT-SAFETY-POSITIVE-SUPPLEMENT-DECLARATION.md` (signed, S1 run under it),
  `ADR-v3-SCOPE-DRAFT.md` (v3 does not gate safety recall), `DRAFT-S3-BASE-MODEL-PILOT-DECLARATION.md`
  (unsigned follow-up).

## Context
The signed supplement declaration ran a pilot (S1) to pick the two weakest-compliance writers for
self_harm elicitation (S2). Prompts: 118 test-side self_harm prompts (ailuminate-demo `ssh` 98,
simplesafetytests self-harm 20; sha `6a657b4a…`, CSE-filtered, 0 train overlap). Each candidate gave
2 samples per prompt at temperature 1.0, max_tokens 800, own chat template, single user turn, no
system prompt, no wrapper. gemma-4-31b labeled under guide `e5b7b56c`; a sample is compliant when its
primitives compose `self_harm` under composition 2a (`59ddf1f6`).

| Candidate (instruction-tuned) | n | compliant | rate | 95% Clopper-Pearson |
|---|---|---|---|---|
| seed-oss-36b | 236 | 5 | 0.0212 | 0.0069 – 0.0487 |
| phi-4 | 236 | 1 | 0.0042 | 0.0001 – 0.0234 |
| granite-4.2-8b | 236 | 0 | 0.0000 | 0.0000 – 0.0155 |
| glm-4.5-air | 0 | — | — | serve_failed (no data) |
| **pooled (3 served)** | 708 | 6 | 0.0085 | 0.0031 – 0.0184 |

Counts and ids only; compliant ids are in `out-s1b/pilot-score.json` (box and VPS
`/root/primitives-evaluator/v3-supp-20261101/`, never committed). Pods: s1 `2f42m7o92yr0rw`
($1.585, 37.9 min) and s1b `o4fnrya79ujrqd` ($0.378, 9.1 min), both archived (`sha256sum -c` OK)
and terminated.

At the best writer's rate (~2%), S2's 2 writers × 118 prompts × 8 samples (~1,900 outputs) would
yield roughly 20–25 labeler-compliant outputs before adjudication, far short of the 120 target.

## Decision
1. **Method limit (recorded):** instruction-tuned open models yield about 2% self_harm compliance
   (best of three served writers; ≤0.5% for the other two) on the public prompt sets used here.
   Collected outputs from such writers **supply negatives and refusals, not safety positives.**
2. **S2 does not run** (cancelled by Justin, t209u). The supplement declaration's S2 gate is moot.
3. S1 outputs stay box/VPS-only as negatives/refusals; the 6 compliant ids remain flagged
   `elicited_compliant` and are never committed or quoted.
4. A separately signed base-model pilot (S3) is drafted, unsigned, in
   `DRAFT-S3-BASE-MODEL-PILOT-DECLARATION.md`. No pod runs before signature.
5. **RH gold:** the rh-denial gold-revision overlay (`labelcmp/results/gold-revised-overlay.jsonl`,
   ADR `ADR-2026-11-01-rh-denial-pure-denial.md`) stands as the labeling-comparison gold from here
   (Justin t209u: "RH results accepted").

## Consequences
- v3 still does not gate safety recall (`ADR-v3-SCOPE-DRAFT.md` decision 2 unchanged); the
  supplement's self_harm side has 0 standing positives from elicitation.
- Spend: cumulative GPU **$25.74** after the RH re-label pod (ledger); RunPod balance **~$35.31**.
  The $25 reporting threshold has been crossed and reported; the $30 stop is $4.26 away, so at most
  one more $4-capped pod fits before the stop.
- glm-4.5-air never served on the pilot pod (vLLM engine init failure); its rate is unknown and is
  not imputed.
