# ADR 2026-11-03: labeling guide settled rule 9 (offer vs refusal)

- **Decision.** Justin Flores, owner message t221u, 2026-11-03 11:12 NPT (head-extension sizing addendum A25).
- **Rule.** An announced or offered method is `encourages` plus the harm object, never `is_mention_not_use`. A refusal or
  a discussion declines or describes; an offer proposes to provide.
- **Where.** `LABELING-GUIDE.md`: settled rule 9; one line each under `encourages` and `is_mention_not_use`; Version
  section. The head-extension checker prompt gets the same rule (wt-p3 `headext_contradict.py`, prompt `v3`).
- **Pin change.** `LABELING-GUIDE.md` `e5b7b56cd466b2f503ad15178ef1b1b8d44a1dde20523898546ed3c4ceca6aa6` →
  `79e29da97cc1e37aad6768955d9e9d62416e465c006f0e4e4f25d5097c23c573`.
- **Scope.** Labels already written under `e5b7b56c` are unchanged and stay pinned to it (each label file records its
  `guide_sha256`). The head-extension offer rows are re-checked under the new guide (A25). Any other relabel under the
  new guide needs its own instruction.
- **Consistency.** Rule 9 restates rule 8 (ADR 2026-11-01 sh-02) for the labeler side; it adds no class and no object.
