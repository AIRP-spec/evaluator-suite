# BLOCKED

## Self-hosted collection (2026-11-01 amendment)

**Status:** not blocked. Runs on RunPod per `docs/PLAN-AMENDMENT-2026-11-01.md`.
Stop and record here if cumulative Phase 3 + collection GPU spend reaches $30,
or if any licence recheck fails.

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
