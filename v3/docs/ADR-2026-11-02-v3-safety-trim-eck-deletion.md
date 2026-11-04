# ADR 2026-11-02: v3-safety trim to the 150 ceiling, eck deletion as a declared exception (Justin t214u + t215u)

**Decision.** v3-safety is sealed at **145** rows (`2dc0e7d8…c5c514`, VPS only), with a separate unused sealed reserve of **72** (`ee7a4658…076068`).
Order: (a) delete generated rows with qualifier `exceeds_common_knowledge` (23); (b) in-set near-duplicate dedupe (LEAK-CHECK §3, keep lower id; 19);
(c) round-robin cap 28 per generated family across register × length cells, lowest id within cell. All 9 real rows kept and flagged, including the
4 with method content: **the eck deletion rule applies to generated rows only.**

**Declared exception to archive-before-terminate / keep-the-archive.** The 23 generated eck rows were deleted unviewed from the v3-safety archive
(VPS and box), with ids, trigger and row sha logged (`docs/v3-safety-trim/eck-deletion-log.json`), in the same form as CSE deletions. S1 and S3
pilot archives untouched. `conveys_method` without eck stays.

**Publication.** The sealed file stays on the VPS. Only its sha is in the repo. Publishing v3-safety is a separate decision at certification time.
**Rule added (t214u):** the in-set collision check is part of the v3 rules (`airp_v3.inset`, 4527eb8c).
**Error profile** of any later score must state the synthetic provenance (136 synthetic / 9 real_elicited; seal sha above).
Detail: `V3-SAFETY-TRIM-2026-11-02.md`.
