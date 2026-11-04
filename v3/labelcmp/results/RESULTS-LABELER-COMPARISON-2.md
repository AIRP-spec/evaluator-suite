# Labeler comparison, second pod (labcmp-2), under Amendment 1

Amendment 1 (`../AMENDMENT-1-THREE-LABELERS.md`) was committed in `3278558c` before this pod. Scored with
`tools/labelcmp_score.py` on all seven measured label files → `SCORES-labcmp-2.json`. The per-labeler per-class
recall/precision table is `PER-CLASS-labcmp-2.tsv`. Both hold counts and ids only. Gold: P = 853 composed rows.

## Run

- Pod `r9pes7ri7q07lk`, RTX PRO 6000 Blackwell Server Edition, SECURE, $2.49/h, no volume. It ran from 15:29 to
  15:55 NPT (25.7 min) and cost $1.065 (balance $44.819 → $43.897). The pod list was empty after termination.
  Both watchdogs ran.
- Between models, the HF cache (`/root/hf`, hub + xet) was cleared and the free disk checked: 229 G free before each
  model (needs: granite 18+20 G, seed-oss 72+20 G, nemotron 80+20 G), and 228–229 G after each clear. There were
  no disk problems.
- The tunnel health probe (`/health` + `/v1/models` through the tunnel) passed for all three models. Transport
  errors: 0, and tunnel restarts: 0, for every model.
- granite was re-run from scratch; the labcmp-1 granite file is void and not used. glm-4.5-air was not run.
- Label files are archived on the VPS at `v3-labcmp-20261101/out-labcmp-2/` (`sha256sum -c` 11/11 OK):
  granite `c9df49bd…f3c1`, seed-oss `19cdee54…d614`, nemotron `7e4e4872…1f1d`.

## Test-role labelers (they would label train-side text), P n = 853

| labeler | valid | class-set exact | stance | primitives exact | CSE tp/pos (fp) | SH tp/pos (fp) | ≥ 95% valid |
|---|---|---|---|---|---|---|---|
| nemotron-3-super | 853 (100%) | 0.8159 (696) | 0.8617 | 0.3095 | 62/66 (1) | 16/24 (2) | yes |
| seed-oss-36b | 849 (99.53%) | 0.7819 (667) | 0.8030 | 0.2392 | 45/66 (0) | 8/24 (31) | yes |
| granite-4.2-8b | 709 (83.12%) | 0.6940 (592) | 0.6553 | 0.1852 | 36/66 (6) | 11/24 (0) | **no** |
| phi-4 (labcmp-1) | 769 (90.15%) | 0.6706 (572) | 0.7456 | 0.4760 | 12/66 (0) | 10/24 (4) | **no** |

granite's invalid outputs (all 873 rows): 74 used an invalid primitive name, 65 had no JSON, and 8 had trailing data
after the JSON. seed-oss had 4 outputs with an invalid primitive name.

## Selection under Amendment 1

- **Labeling test-side text: trio = mistral-small-3.2, gemma-4-31b, qwen3-30b-a3b-2507** (ranked in that order, so
  qwen3 is third/adjudicator).
- **Labeling train-side text: only two test-role labelers clear the 95% validity bar (nemotron-3-super,
  seed-oss-36b). Per Amendment 1 §2, fewer than three = report and stop.** There is no train-side trio, and no
  cross-side labeling was started.
