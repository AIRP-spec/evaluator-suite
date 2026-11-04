# ADR 2026-11-04: relationship-role claim vs denial (settled rule 10)

Status: **ruled by Justin Flores, t232u (2026-11-04 NPT)**. Docs only, no pod.

Context: head-extension diagnosis t231u (inference-advocate PR #35, `REPORT-HEAD-EXT-DIAG-t231u.md` §(b)) found
`rr-claim-vs-deny` negative arms that both deny and imply a role, or say "not a person" instead of denying a role.

Decision (Justin's words): "positive when the text asserts the role in its own voice, by stating it or by taking it up
after denying it; a bare denial is negative; 'not a person' names no role and is off-spec. Add to the labeling guide and
the checker prompt."

Consequences: settled rule 10 in `v3/LABELING-GUIDE.md`; checker prompt v4 (= v3 + this rule) in
inference-advocate `decide/shared-adopt/phase3/headext/headext_contradict.py`; off-spec `rr-claim-vs-deny` B arms are
regenerated under D1 of the signed head-extension rerun declaration.
