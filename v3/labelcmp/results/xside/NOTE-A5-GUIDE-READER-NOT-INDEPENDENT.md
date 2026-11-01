# Note (Justin t208u): guide-reader is not an independent third vote

Recorded 2026-11-01. The AMENDMENT-5 train-queue guide-reader is **nemotron-3-super**, the
same model as the primary train-side labeler (different guide revision only). Its vote is
therefore **not independent** of the primary. On the A5 run the final class set matched the
reader on 776/777 decided rows.

**Check on the reader:** the test-side trio (mistral-small-3.2, gemma-4-31b,
qwen3-30b-a3b-2507 under AMENDMENT-2/3/4) is the independent check on labeling quality; do
not treat the A5 guide-reader majority as a three-way independent adjudication.
