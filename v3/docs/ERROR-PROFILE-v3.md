# Error profile: v3 (standing notes)

Every later score on v3 states the notes below in its error profile. They do not change any signed rule. v3 is never
used for selection or gating of the head-extension retrain (inference-advocate
`decide/shared-adopt/phase3/DRAFT-HEAD-EXTENSION-DECLARATION.md` §5).

## Independence from the head-extension training data (Justin t217u, sizing addendum amendment 9; 2026-11-02)

- **Qwen3 as v3 adjudicator is the weaker point.** `qwen3-30b-a3b-2507` (`Qwen/Qwen3-30B-A3B-Instruct-2507 @0d7cf239`)
  is the v3 adjudicator (airp_v3.xside, labeler 3). The same checkpoint writes the head-extension
  (data-v10) training and validation rows. A model trained on qwen3-written text and then scored against qwen3-adjudicated
  gold is not fully independent of qwen3's reading of the same shapes. State this in any v3 score of a data-v10 model.
- **Generators and spec sources differ.** The data-v10 rows come from the head-extension slot spec
  (`decide/shared-adopt/phase3/headext/headext-slot-spec.json`, inference-advocate) and the qwen3 generator; v3 items come
  from the v3 collection specs and test-side writers. No v3 item text is used to build data-v10; the text-level leak check
  (sizing addendum §5 V-g) runs before training.
- **Offer-shape overlap.** The offer shape (a method announced or offered, none delivered) is part of the published
  `self_harm` definition (ADR 2026-11-01 sh-02 correction), so overlap at the level of shape is unavoidable. State it;
  it is not a leak of text.
