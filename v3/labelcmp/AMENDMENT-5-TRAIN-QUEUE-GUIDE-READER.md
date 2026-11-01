# Amendment 5: train-queue adjudication by a self-hosted guide-reader

Decided by Justin, 2026-11-01 19:35 NPT (t207u). This file and its code are committed **before any run**. It
replaces the train-queue adjudication method of AMENDMENT-2/3 (agent adjudication). AMENDMENT-3/4 rules for
high-precision safety fires apply where relevant. Code: `v3/airp_v3/xside.py` (`pick_guide_reader`,
`decide_train_a5`, `A5_DROP_UNREAD`); tests `v3/tests/test_xside.py` (`test_a5_*`).

## Queue and drops before any read
- Queue: `results/xside/QUEUE-train-a3.jsonl`, 849 rows (indexes 0–848 in file order).
- Queue indexes **230 and 545** (CSE-risk) are dropped, logged by id, never read and never sent to the pod.
- Any queue row with `cse_fire` (0 at queue build) is dropped unread and logged by id.
- All other rows (847) are sent, including the 585 the agent decided earlier: the whole queue is one method.
  The earlier decisions (`dec.tsv`, box, sha in `dec.tsv.sha256`; VPS copy) are used only for the agreement report.

## Guide-reader selection (declared rule)
- Candidates: nemotron-3-super, qwen3-30b-a3b-2507.
- Eligible: gold validity ≥ 0.95 (labcmp, P = 853) **and** family not a train-side writer family (gemma, glm,
  mistral, qwen), so the reader is cross-family on every queue row.
- Nemotron is chosen if eligible; otherwise the eligible candidate with the higher gold class-set exact match.
- Stored gold: nemotron valid 1.000, exact 0.8159, eligible; qwen3 valid 1.000, exact 0.7186, **ineligible**
  (qwen writes train-side rows). **Guide-reader = nemotron-3-super.**

## Reading
- Revised guide `LABELING-GUIDE.md` sha256 `e5b7b56cd466b2f503ad15178ef1b1b8d44a1dde20523898546ed3c4ceca6aa6`, frozen
  copy on the box. Same system prompt and procedure as `airp_v3.label_local` (SYSTEM_PREFIX + full guide,
  temperature 0, POLICY_VERIFIED gate, same-family refusal).
- One row per request (no multi-row prompts); the reader sees the row and the guide only, not the other labels,
  so its vote is independent. Output is `{stance, objects, qualifiers}` only, no free text.

## Decision per row (primitives only; classes composed through composition 2a)
1. Any of the three labels (primary, second, reader) composes CSE or carries `sexual_activity` +
   `subject_is_minor` → dropped unread (`cse_flag_any_labeler_unread`), id logged.
2. Reader output invalid → dropped (`reader_invalid`), id logged.
3. Three valid labels: stance with ≥ 2 votes; each object and qualifier kept if ≥ 2 of 3 carry it. Three-way
   disagreement drops the row: all three stances differ (`three_way:stance`) or all three derived class sets
   differ (`three_way:classes`).
4. Primary or second invalid: the two valid labels decide where they agree and the reader breaks every two-way
   tie (equivalent to taking the reader's value on each differing primitive).
5. AMENDMENT-3/4: a safety fire from a labeler with gold precision ≥ 0.95 on that class stands unless the reader
   records a mention (`describes` + `is_mention_not_use`); a standing fire is overlaid with the minimal composing
   primitives (AMENDMENT-4, readings confirmed by Justin). On the train side no labeler is high-precision on
   self_harm (nemotron 0.8889, seed-oss 0.2051) and CSE rows are dropped by step 1, so this is expected to be
   vacuous; it is counted.

## Run and reporting
- One pod (`greader-1`, RTX PRO 6000 SECURE): headroom check, POLICY_VERIFIED gate, cache clear, tunnel probe,
  $4 / 90 min cap, box and in-pod watchdogs, archive with manifest and `sha256sum -c`, terminate, pod list empty.
- Report (counts and ids only): decisions by outcome and by final class, drops with reasons, agreement of the
  re-run with the 585 earlier decisions (agree / disagree, by class), the five most common disagreement shapes,
  spend, balance, shas, pod list.
