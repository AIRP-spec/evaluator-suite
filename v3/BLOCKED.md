# BLOCKED

## Self-hosted collection (2026-11-01 amendment)

**Status:** collection complete (2026-11-01 04:58 NPT). All 8 models, 2859/2859
test and 5723/5723 train prompts, 0 errors; cumulative spend $11.37 of the $30 stop.
See `collect/reports/collection-selfhost-20261101.json`. No pod running.

**For Justin to review (not blocking collection):**
- The prompt sets also dropped whole rows for exact duplicates (test 3, train 8)
  and test-vs-train leaks (test 7), in addition to filter_cse (test 181, train 269).
  These are whole-row removals declared in `bdca341` but not filter_cse itself.
- Length caps at 800 tokens are high for granite-4.2-8b (513/714), glm-4.5-air
  (764/1430) and nemotron-3-super (314/715). Responses are truncated, not empty.
- Thinking markers in content: granite 30, seed 2, glm 1 rows (flagged per row in
  provenance `thinking_markers_in_content`).
- Labeling (OpenRouter) not started; it needs your go-ahead.

## OpenRouter collection (Phase 1 §4.2)

**Status:** superseded for collection by the self-hosted amendment; the openrouter
backend stays blocked.

**Why:** OpenRouter Terms §7(11)/§8 require written red-teaming approval before
sending public red-team prompt sets through models. The standing brief says to
wait for that approval. The collection runner (`airp_v3.collect`) refuses to call
OpenRouter unless a repo-root file named `OPENROUTER_APPROVAL` exists containing
Justin's written approval text.

**Unblock:** Justin places the approval reply from safety@openrouter.ai (or his
written authorization referencing it) in `OPENROUTER_APPROVAL` at the repo root,
then says to proceed. The draft request email is already in
`docs/OPENROUTER-MODELS.md`.

**Meanwhile:** labeling guide, filter, collection gate, labeling harness,
adjudication, compose assertion, leak check, and seal all dry-ran on the 40
draft items (see `dryrun/out/DRYRUN-SUMMARY.json`). Labeling of already-collected
items does not require the approval file (not Red Teaming under §7(11)).

## Not blocked

- Adopting `LABELING-GUIDE.md` (done).
- Building and dry-running the rest of Phase 1 §4.1–4.4 tooling (done).
- Phase 3 plan work (separate; awaits Justin only where the standing brief says).
