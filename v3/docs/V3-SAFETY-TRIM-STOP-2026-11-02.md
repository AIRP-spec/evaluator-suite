# v3-safety trim to the 150 ceiling: STOPPED before step 1 (ids, counts and shas only; no item text)

Ruling: Justin t214u, 2026-11-02 02:52 NPT. Candidate seal `294922d57292b1ad68f722575df69300f77d997e8e08b3708d7855655b457229`
(259 rows, VPS `/root/primitives-evaluator/v3-safety-20261102/seal-work/candidate/`, `sha256sum -c` OK
2026-11-02 ~02:55 NPT; id set identical to box seal input `de38048b…`, id-list sha `786a0495…`).

**Status: nothing deleted, nothing promoted, no pod, no spend.** Step 1 deletes rows from the set and the
archive, which is irreversible, and the ruling cannot be applied mechanically as written (two points below).
Step 6 (in-set collision rule, tool and test) is done in this commit. Steps 1-5 and 7 wait for a ruling.

## Why it stopped
1. **"The 26 method-content rows" names two different sets of 26.** From the labels (code count, matches the
   run report): final stance `conveys_method` = 26; qualifier `exceeds_common_knowledge` = 26; overlap 18;
   union **34**. Which set is "method content"?
   - A = `conveys_method` (26). Note: 17 of these are sh03, whose declared gold allows `conveys_method`.
   - B = `exceeds_common_knowledge` (26).
   - C = union (34).
2. **Step 1 conflicts with "all 9 real rows kept".** Real rows in the method sets: 4 in A, 3 in B, 4 in C
   (`ailuminate-demo:airr_practice_1_0_90092::seed-oss-36b@pilot-s0`, `…_90092::seed-oss-36b@pilot-s1`,
   `…_155959::seed-oss-36b@pilot-s1`, `…_90094::phi-4@pilot-s0`; B lacks `…_90092…@pilot-s0`).
   Either real method rows are deleted (real kept = 5 or 6), or they are exempt from step 1 (real kept = 9).
3. **Archive scope of the deletion (to confirm).** The rows exist in the v3-safety archive (VPS
   `v3-safety-20261102/out-v3s` gen/items/labels/combined/seal-input, `seal-work/candidate` and `recheck`)
   and the box working copy. The 4 real method rows also exist in the S1 / S3 pilot archives
   (`v3-supp-20261101` etc.). Confirm whether "the archive" includes those.
4. **"Lowest id" order for the cap (doubt, not a blocker by itself).** Read as Python string order of the
   full id, the cap keeps `clinical` before `colloquial` before `terse` and `long` before `medium` before
   `short`, which skews register inside each family (below). Generation order (`build_jobs`: terse,
   clinical, colloquial) skews the other way. The ruling says "lowest id", so string order is the literal
   reading.

## Dry run (box, by code, counts only; same ids as the VPS candidate)
Step 2 (in-set collisions after step 1, rule in docs/LEAK-CHECK.md §3) drops the **same 19 ids** under every
step-1 reading (offer-shape 10, sh01 3, sh02-offer 3, sh03 2, sh04 1); 0 real rows and 0 protected conflicts.
On all 259 rows the same rule gives 21, matching the run report.

| step-1 reading | real method rows | after step 1 | after step 2 | final sh01 / sh03 / sh04 / offer-shape / sh02-offer / real | total | reserve |
|---|---|---|---|---|---|---|
| A conveys_method | deleted | 233 | 214 | 28 / 28 / 28 / 28 / 28 / 5 | 145 | 69 |
| A conveys_method | kept | 237 | 218 | 28 / 28 / 28 / 28 / 28 / 9 | 149 | 69 |
| B exceeds_common_knowledge | deleted | 233 | 214 | 28 / 28 / 28 / 28 / 24 / 6 | 142 | 72 |
| B exceeds_common_knowledge | kept | 236 | 217 | 28 / 28 / 28 / 28 / 24 / 9 | 145 | 72 |
| C union | deleted | 225 | 206 | 28 / 28 / 28 / 28 / 24 / 5 | 141 | 65 |
| C union | kept | 229 | 210 | 28 / 28 / 28 / 28 / 24 / 9 | 145 | 65 |

Every reading is ≤ 150, and the minor-qualifier row `v3s:v3s-offer-shape:clinical:long:4::seed-oss-36b@v3s`
survives every reading (flagged). Register mix of the generated rows kept (string-order cap vs generation-order cap):
A: colloquial 66 / clinical 48 / terse 26 vs terse 82 / clinical 33 / colloquial 25;
B: colloquial 64 / clinical 55 / terse 17 vs terse 76 / clinical 40 / colloquial 20;
C: colloquial 64 / clinical 48 / terse 24 vs terse 76 / clinical 33 / colloquial 27.

### Step-2 drop ids (dropped → kept lower id it collides with)
- `v3s:v3s-offer-shape:clinical:short:2::seed-oss-36b@v3s` → `v3s:v3s-offer-shape:clinical:short:0::seed-oss-36b@v3s`
- `v3s:v3s-offer-shape:clinical:short:3::seed-oss-36b@v3s` → `v3s:v3s-offer-shape:clinical:short:0::seed-oss-36b@v3s`
- `v3s:v3s-offer-shape:clinical:short:4::seed-oss-36b@v3s` → `v3s:v3s-offer-shape:clinical:short:1::seed-oss-36b@v3s`
- `v3s:v3s-offer-shape:clinical:short:5::seed-oss-36b@v3s` → `v3s:v3s-offer-shape:clinical:short:1::seed-oss-36b@v3s`
- `v3s:v3s-offer-shape:colloquial:short:2::seed-oss-36b@v3s` → `v3s:v3s-offer-shape:colloquial:short:0::seed-oss-36b@v3s`
- `v3s:v3s-offer-shape:colloquial:short:5::seed-oss-36b@v3s` → `v3s:v3s-offer-shape:colloquial:short:4::seed-oss-36b@v3s`
- `v3s:v3s-offer-shape:terse:short:2::seed-oss-36b@v3s` → `v3s:v3s-offer-shape:terse:short:0::seed-oss-36b@v3s`
- `v3s:v3s-offer-shape:terse:short:3::seed-oss-36b@v3s` → `v3s:v3s-offer-shape:terse:short:1::seed-oss-36b@v3s`
- `v3s:v3s-offer-shape:terse:short:4::seed-oss-36b@v3s` → `v3s:v3s-offer-shape:terse:short:0::seed-oss-36b@v3s`
- `v3s:v3s-offer-shape:terse:short:5::seed-oss-36b@v3s` → `v3s:v3s-offer-shape:terse:short:0::seed-oss-36b@v3s`
- `v3s:v3s-sh01:colloquial:short:2::seed-oss-36b@v3s` → `v3s:v3s-sh01:colloquial:short:0::seed-oss-36b@v3s`
- `v3s:v3s-sh01:colloquial:short:4::seed-oss-36b@v3s` → `v3s:v3s-sh01:colloquial:short:1::seed-oss-36b@v3s`
- `v3s:v3s-sh01:terse:medium:4::seed-oss-36b@v3s` → `v3s:v3s-sh01:terse:medium:0::seed-oss-36b@v3s`
- `v3s:v3s-sh02-offer:colloquial:short:5::seed-oss-36b@v3s` → `v3s:v3s-sh02-offer:colloquial:short:0::seed-oss-36b@v3s`
- `v3s:v3s-sh02-offer:terse:short:4::seed-oss-36b@v3s` → `v3s:v3s-sh02-offer:terse:short:0::seed-oss-36b@v3s`
- `v3s:v3s-sh02-offer:terse:short:5::seed-oss-36b@v3s` → `v3s:v3s-sh02-offer:terse:short:0::seed-oss-36b@v3s`
- `v3s:v3s-sh03:colloquial:short:2::seed-oss-36b@v3s` → `v3s:v3s-sh03:colloquial:short:0::seed-oss-36b@v3s`
- `v3s:v3s-sh03:colloquial:short:5::seed-oss-36b@v3s` → `v3s:v3s-sh03:colloquial:short:3::seed-oss-36b@v3s`
- `v3s:v3s-sh04:colloquial:short:3::seed-oss-36b@v3s` → `v3s:v3s-sh04:colloquial:short:1::seed-oss-36b@v3s`

## What is needed to finish
One line each: (1) A, B or C; (2) real method rows deleted or exempt; (3) archive scope (v3-safety only, or
also the S1/S3 pilot archives); (4) cap order: string order of the id (literal), or another order.
Then steps 1-5 and 7 run as ruled, with no further stop unless a total exceeds 150 or a protected row would drop.

Dry-run script: box `/workspace/v3safety/trim_dryrun.py` (not committed; reads item files, prints counts only).
