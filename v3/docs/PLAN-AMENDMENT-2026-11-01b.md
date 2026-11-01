# Plan amendment 2026-11-01b: test-side output cap 1,500 and reasoning-marker stripping

Approved by Justin on 2026-11-01 (review of the Nov 1 collection report):
"Collection: raise the output cap to 1,500 tokens. Re-collect the test side only.
Keep the 800-cap rows flagged as truncated. Strip reasoning markers, keep those
rows, flag them." Declared here before any pod runs under it.

## What changes (one variable: the output cap on the test side)

| | Before | After |
|---|---|---|
| Test-side `max_tokens` | 800 | **1,500** |
| Training-side `max_tokens` | 800 | 800 (unchanged) |

`airp_v3.collect` enforces `MAX_TOKENS_CAP = {"train": 800, "test": 1500}` and
refuses a request above the cap for its side.

Re-collected: the four test-side models only (phi-4, granite-4.2-8b,
seed-oss-36b, nemotron-3-super), all 2,859 test prompts, same round-robin
assignment. Output goes to a new directory (`out1500/`), never over the 800-cap
files.

## What does not change

Same prompt files and filter reports (test sha256
`976843d4072d80ca5771a51f12ba014e4bf69b09542470e42ec4d6e897489e4b`), same models,
revisions, quantizations and serve flags, thinking off via the chat template,
no system prompt, no template or jailbreak, temperature 0.7, POLICY_VERIFIED gate
and licence recheck before each pod, one pod at a time (and none while another
workstream's pod runs), 90 min / $4 per pod with in-pod and box watchdogs,
archive with sha256sum -c before terminate, ledger and STATUS-RESUME.md on the
VPS after every pod, $30 cumulative stop (Phase 3 + collection).

## The 800-cap outputs

Kept byte-for-byte and archived (VPS `out-v3c-p*`). They are not deleted.
`tools/flag_collected.py` writes derived copies (`out800-derived/`) that add the
same flags below, with the source sha256 recorded; the source is checked
unchanged before and after.

## Flags on every row (new rows at write time; derived copies of old rows)

- `provenance.truncated`: `finish_reason == "length"` (hit its cap: 800 or 1,500).
- `provenance.max_tokens_cap`: the cap the row was collected under.
- `provenance.reasoning_markers_stripped`: a reasoning marker was found and removed.
- `provenance.original_content`: the verbatim response before stripping (null when
  nothing was stripped). Rows are never discarded for markers.
- `provenance.empty_after_strip`: stripping left no answer text (kept and flagged).

## Stripping rule (`airp_v3.collect.strip_reasoning`)

Markers: `<think>`, `</think>`, `<seed:think>`, `</seed:think>`, `<|channel>thought`.
A complete `<open>…</close>` block is removed. An unmatched closing marker means the
chat template opened the block, so the text before the last closing marker is
reasoning and is removed. An unmatched opening marker (cut off while reasoning)
removes from it to the end. Any other marker literal is removed on its own. In the
800-cap data every marker seen was an unmatched closing marker (granite 30 rows,
seed 2, glm 1).
