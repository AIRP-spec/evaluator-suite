# Error profile: v3-safety (standing notes)

Every later score on v3-safety states the notes below in its error profile, in addition to the synthetic provenance
required by `DRAFT-V3-SAFETY-DECLARATION.md` and `ADR-2026-11-02-v3-safety-trim-eck-deletion.md`. They do not change any
signed rule. v3-safety is never used for selection or gating of the head-extension retrain.

## Independence from the head-extension training data (Justin t217u, sizing addendum amendment 9; 2026-11-02)

- **Offer-shape overlap is unavoidable.** The data-v10 offer-shape `self_harm` rows (`offer-clinical`,
  `offer-colloquial`, held-out `offer-terse`) and the self-harm arms of the `hate-elim-vs-self-harm` pairs use the shape in
  the published `self_harm` definition (a method announced or offered, none delivered). v3-safety's `v3s-offer-shape`,
  `v3s-sh02-offer` and `v3s-sh01` families come from the same definition. After this phase the training recipe contains those
  shapes. Overlap at the shape level remains; the text-level leak check (sizing addendum §5 V-g, against the v3-safety
  seal `2dc0e7d8…` and reserve `ee7a4658…`) removes near-duplicate text only.
- **Generators and spec sources differ.** v3-safety rows were written by Seed-OSS-36B from `v3-safety-slot-spec.json`.
  The data-v10 rows are written by `Qwen3-30B-A3B-Instruct-2507 @0d7cf239` from the head-extension slot spec
  (inference-advocate `decide/shared-adopt/phase3/headext/headext-slot-spec.json`), with a different system prompt.
- **Qwen3 is the weaker point.** qwen3 is labeler 3 and adjudicator for the v3-safety gold
  (DRAFT-V3-SAFETY-DECLARATION.md, labeler table); it now
  also writes training text. A data-v10 model's v3-safety score is not fully independent of qwen3's reading of these
  shapes. Seed-OSS-36B also acts as a delete-only checker on the data-v10 rows (it never sets their gold).
