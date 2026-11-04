# DECLARATION: labeler comparison on gold rows (self-hosted, before cross-side labeling)

Written 2026-11-01 (NPT, UTC+5:45). **Declared before any pod or request.** Committed and pushed to
`v3/phase1-pipeline` (evaluator-suite draft PR #2) and verified with `git ls-remote` before the pod is created.
Authority: Justin 2026-11-01 — "Labeler comparison approved (several model families against gold-labeled rows, picked
on measured accuracy, a few cents). Then self-hosted labeling: training-side models label test rows and the reverse,
two families per row, same adjudication" — and t204u ("Next, one pod at a time: labeler comparison, then cross-side
labeling"). This run measures labelers only. **It labels no v3 or corpus row, scores no evaluator, and touches no
held-out suite.** Cross-side labeling is not started by this declaration; its results are reported first.

## 1. Candidate labelers (all self-hosted open weights, POLICY_VERIFIED gate, no OpenAI)

`labelcmp/labelers.labelcmp.json`. Every candidate must pass `airp_v3.policy.find_policy_verified` at its verified
revision and role (verdict CLEAR / CLEAR-WITH-CONDITIONS, license document sha256 on disk equal to the recorded one),
checked in code (`airp_v3/label_local.gate`) before any request; the base URL must be a self-hosted vLLM server.

| key | family | verified side | labels (later) | license (POLICY_VERIFIED) |
|---|---|---|---|---|
| qwen3-30b-a3b-2507 | qwen | train | test-side rows | Apache-2.0 |
| mistral-small-3.2 | mistral | train | test-side rows | Apache-2.0 (card) |
| gemma-4-31b | google-gemma | train | test-side rows | Apache-2.0 (Gemma 4 page) |
| phi-4 | microsoft-phi | test | train-side rows | MIT |
| granite-4.2-8b | ibm-granite | test | train-side rows | Apache-2.0 (card) |
| seed-oss-36b | bytedance-seed | test | train-side rows | Apache-2.0 |
| nemotron-3-super (NVFP4) | nvidia-nemotron | test | train-side rows | NVIDIA Nemotron Open Model License |

- **Not run: glm-4.5-air** (verified, train side). It needs ≈ 110 GB (online FP8) and ran on an H200; it does not fit
  the one 96 GB pod this comparison uses. Reported as not measured, not as failed.
- **Labeling use of the licenses.** POLICY_VERIFIED's recorded use is elicitation. Labeling (classifying existing text
  into primitives) is a narrower use. MIT and Apache-2.0 carry no field-of-use limits. The Nemotron Open Model License
  and the Gemma 4 terms (Apache-2.0) are not limited to elicitation either; labeling bypasses no guardrail (the Gemma
  condition "no safety-filter bypass" holds: the system prompt is the labeling guide, not a jailbreak). No doubt about
  terms arises, so none is reported. POLICY_VERIFIED is unchanged.
- **Brief §4.3 vs this design.** §4.3 asked for labelers outside the elicitation set. Justin replaced that for v3
  (2026-11-01: training-side models label test rows and the reverse). Family separation is enforced instead: no family
  is on both sides (POLICY_VERIFIED rule 4), and an item whose writer family equals the labeler's is never sent
  (code-enforced, `writer_family`).

## 2. Gold rows

- **data-v9 val**, 873 rows, sha256 `964c2b2198572823846364c7f30d4e6c44d8c9bf09fc59a0731f0ce7af7ecd2d` (the P3-3 val).
  Gold = the adjudicated `{stance, objects, qualifiers}` per row; gold classes derived at load through composition 2a
  `59ddf1f6…` (sha-checked), never stored. Built box-locally by `tools/labelcmp_build_items.py` → items
  `b6492dbad23e3279d6d3b303cdf698ddf149dc247fd9a62e2faf1f38eabda579`, gold
  `6d7b0605f651d2326a6e3b8fb0d7a6af6abd01cdee0b056a27c3cfaadc97fb56`. Item text is not committed here.
- Derived positives (873): CSE 66, self_harm 44, criminal_assistance 36, hate 20, persona_claims 52, profanity 24,
  relational_hooks 40, sexual_content 38, simulation_obscured 32, sycophancy 20, violence 44.
- **P (primary, 853 rows):** locally composed rows (no writer model, so no labeler shares their family).
  **W (reported only, 20 rows):** the writer-path self_harm rows, written by Qwen2.5-32B-Instruct
  (inference-advocate `tools/evaluator-training/RUNBOOK.md`). Never sent to the Qwen labeler; scored for the other six
  and never used for selection.
- 20 `violence-kill-instruction` rows carry the non-vocabulary object `criminal_assistance` (a class id). It is
  dropped from gold primitives for scoring; the build asserts this changes no derived class.
- **CSE content:** none. The val CSE positives are the corpus's composed rows (minor marker on non-sexual text; adult
  sexual text separately), the same no-CSE-exhibiting invariant as the corpus. Reports carry counts and ids only.
- **Not used:** v3, v2 held-out, v1-207, any held-out suite.

## 3. Labeling procedure (identical for every candidate)

- System prompt = `airp_v3.label.SYSTEM_PREFIX` + the **full** `LABELING-GUIDE.md` (sha `5b2908ba…5f21`, includes
  settled rule 8), no truncation; user turn = the item text. Temperature 0, max_tokens 300, the model's own chat
  template with its POLICY_VERIFIED thinking-off kwargs; `--max-model-len 8192` (collection used 4096; prompts here are
  ≈ 5k tokens). One pass per labeler per row; invalid JSON / invalid primitive names are not resampled.
- vLLM 0.32.0 on one RTX PRO 6000 Blackwell (96 GB), SECURE EU-RO-1 with network volume `rmn62wuuzx` attached (for
  the weights copy, §6). Models served one at a time, deleted from container disk after use.

## 4. Metrics (on P; W reported the same way)

Computed by `tools/labelcmp_score.py`. An invalid or missing output = empty prediction and counts as wrong.
- valid-output rate;
- per primitive: stance accuracy; for each of the 7 objects and 9 qualifiers, row-level agreement with gold
  (present/absent) plus recall and precision on gold positives; any primitive under 70 % agreement is flagged;
- per class (derived through composition 2a from the labeler's primitives): recall, precision, agreement;
- **safety classes (CSE, self_harm): recall with counts, exact one-sided 95 % Clopper–Pearson upper bound on the miss
  rate, missed and extra ids**;
- row-level: full-primitive exact match, and **derived class-set exact match (primary)**.

## 5. Selection rule (declared now; measured accuracy on gold only)

Per side (train-role labelers for test-side rows; test-role labelers for train-side rows):
1. Eligible: valid-output rate ≥ 95 % on P.
2. Rank by derived class-set exact match on P. Values within 0.5 pp are a tie, broken by the higher of
   min(CSE recall, self_harm recall), then by full-primitive exact match, then by key.
3. **Pair = the top two; the third = the adjudication tie-breaker.** If fewer than two are eligible on a side, no pair
   is recommended for that side and that is reported.
4. Safety recall is reported for each, and any recommended labeler with CSE or self_harm recall under 90 % is
   flagged in the report. The flag does not change the rule.
This rule is not amended after the pod starts.

## 6. Pod, caps and close-out

- One pod. Headroom check first (no running pod; box, VPS and volume free space; balance; cumulative GPU spend
  ≤ $30 stop including this pod's cap). Cap **90 min and $4** (RTX PRO 6000 SECURE $2.49/h → 90 min ≈ $3.74);
  box watchdog + in-pod `runpodctl remove pod` watchdog. Terminate within 15 min of any failure.
- Expected cost ≈ $2.5–3.2. The labeling itself is a few cents per labeler (≈ 1–2 GPU-min each); model download and
  load dominate.
- **Weights copy (Justin t204u):** while the pod is up, the 17 GB P3-3 `p33/keep/` (10 finals + 10 artifacts) is
  copied from the volume to the VPS `…/decide-2026-10-13/shared-adopt/p33/volume-weights/`, streamed through the
  box (no VPS credential on the pod). Source is `sha256sum -c` against `MANIFEST-volume-p33.sha256` (`988a3b56…`) on
  the volume; destination `sha256sum -c` on the VPS. A weights-copy failure does not stop labeling and does not start a
  second pod.
- Labels, summaries and scores archived to the VPS (`/root/primitives-evaluator/v3-labcmp-20261101/`) with a manifest
  and `sha256sum -c` before terminate. Pod list confirmed empty after.

## 7. Pins

| file | sha256 |
|---|---|
| `airp_v3/label_local.py` | `1d5ab6e0550d8252d25c43bf5a6f94edc445397b15adf5d0d82f8d9e3b8ca0c6` |
| `airp_v3/label.py` (SYSTEM_PREFIX) | `5a031e45a6500b0eb382e84f22dd2d249ebf917dcd8e9c2ec9a02f3d302b7d01` |
| `tools/labelcmp_score.py` | `84c3cba922449e467e68cd98dc229542ed75ac798a0cf99761174c3bbebbfa14` |
| `tools/labelcmp_build_items.py` | `7240f2a816a1a230aa39a09292804fd62c9f4a1b396bd92f132ec730e0c1aca4` |
| `labelcmp/labelers.labelcmp.json` | `d2730247d01160d7850960950f427f078b21d428765a882daaec09018bd7e194` |
| `tests/test_labelcmp.py` | `0ac70328805a4e9d28912b6047ccece46ad2667b13738090a9db9872e07638a5` |
| `LABELING-GUIDE.md` | `5b2908ba2cd5cf04df3bb79486d7909326796b79d67e71e9210dfec4e2945f21` |
| `spec/composition-2a.json` | `59ddf1f630ec2dcd81d40dd01f2adb53f1310fe42128d3ccc9b90de61e28ab9e` |
| `policy/POLICY_VERIFIED.json` | `9f49db7f6cf4b45303c0337d74d93790e4abd8559d09178b9159bfb8242531c8` |
