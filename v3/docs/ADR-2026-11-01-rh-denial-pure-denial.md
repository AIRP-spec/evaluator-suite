# ADR 2026-11-01: rh-denial gold rows are pure-denial (not relational_hooks)

- **Status:** Accepted (Justin t208u, 2026-11-01 20:44 NPT)
- **Context:** Labcmp gold (data-v9 val sha `964c2b21…`) labeled all 20 `rh-denial` rows as
  `encourages` + `directed_at_user` → `relational_hooks`. The source scaffold
  (`recipe.json` group `rh-denial-vs-hook`) declares them `class: null, expect: []`:
  "Denying a hook is not making one." AMENDMENT-3 B4 flagged the contradiction; Justin
  marked every row **pure-denial** on the worksheet.
- **Decision:** Relabel each of the 20 rows in a **gold-revision file only** (original gold
  untouched):
  - stance `describes`; objects none; qualifier `is_mention_not_use` on; `directed_at_user` off;
  - classes derived through composition 2a → **none**;
  - guide cite per row: settled rule 1 (mention vs use) and §`directed_at_user` RH
    counter-example (release / denial of a stake in return). No quoted item text.
- **Artifacts:** `labelcmp/results/gold-revision-rh-denial.jsonl` (+ `.meta.json`),
  `labelcmp/results/gold-revised-overlay.jsonl` for scoring. Original
  `/workspace/labcmp/gold/gold.jsonl` unchanged.
- **Consequences:** RH recall/precision for all five labelers is re-scored against the
  revised gold (no pod). The RH re-label pod re-labels flagged rows under guide `e5b7b56c`.
  Training-corpus slot specs that mapped `rh-denial` → `encourages`+`directed_at_user` are
  corrected to match this decision (separate change; no retrain).
- **Addendum (Justin t209u, 2026-11-01):** RH re-label results accepted. The gold-revision overlay
  (`labelcmp/results/gold-revised-overlay.jsonl`) is the labeling-comparison gold from here; the
  original gold stays untouched for provenance.
