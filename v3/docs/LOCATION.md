# Where the v3 work lives

**Decided (Justin, 2026-10-19, t165u):** the public repository **AIRP-spec/evaluator-suite**. Suite versions
are top-level directories, starting with `v3/`. This content was moved from draft PR
AIRP-spec/inference-advocate#34 (branch `v3/intern-prep`, commit `1767890`), which stays a draft and points here.

Why a separate repo:

1. **Contamination.** The v2 suite and the v1-207 items are public on `main` of AIRP-spec/inference-advocate
   (since 2026-09-11). Anyone who clones that repo has the protected text on disk, in editor search, and in
   the context of any coding assistant that indexes the checkout. This repo contains none of it.
2. **The no-copy check is absolute here.** `v3/tools/check_no_protected.py` can scan the whole tree.
3. **History and review.** Suite PRs don't mix with the certification, evaluator and deploy PRs.

v3 authors: don't clone inference-advocate into the same workspace you author items in.
The leak-check protected files are never committed here; they are resolved privately by the operator
(docs/LEAK-CHECK.md).
