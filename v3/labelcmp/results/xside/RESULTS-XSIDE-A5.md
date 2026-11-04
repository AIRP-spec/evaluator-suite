# AMENDMENT-5 results: train queue decided by majority of nemotron, seed-oss and the guide-reader

Pod greader-1 (peg7o1avqddken, RTX PRO 6000 SECURE, $2.49/h, vLLM 0.32.0), 19.1 min, cost $0.79. Reader nemotron-3-super,
guide e5b7b56c, one row per request, primitives only. Counts and ids only; no item text. Script `labelcmp/scripts/a5_combine.py`.

- Queue 849; sent 847; reader valid 847/847; transport errors 0.
- Outcome: {"decided:majority_of_3": 771, "dropped": 72, "decided:two_valid_reader_breaks_ties": 6}.
- Decided 777, dropped 72: {"three_way:classes": 68, "cse_risk_unread_not_sent": 2, "three_way:stance": 2}. Ids in `A5-DROPS-train.tsv`.
- High-precision fire overlays: 0 (vacuous on train side, as declared).
- Final classes (decided rows): {"criminal_assistance": 16, "hate": 12, "persona_claims": 52, "profanity": 15, "relational_hooks": 49, "self_harm": 2, "sexual_content": 8, "simulation_obscured": 51, "sycophancy": 1, "violence": 11}; no class 594.
- Final class set equals labeler's class set: {"primary": 714, "reader": 776, "second": 63}.
- Top-5 trio shapes (primary | second | reader classes): [[" | sycophancy | ", 337], [" | persona_claims | ", 98], [" | simulation_obscured | ", 39], [" | hate | ", 26], ["relational_hooks | sycophancy | relational_hooks", 17]].

## Agreement with the earlier 585 agent decisions

- {"compared": 536, "disagree": 150, "agree": 386, "new_dropped:three_way:classes": 46, "old_skipped": 2, "new_dropped:three_way:stance": 1}; primitives {"primitives_differ": 202, "exact_primitives_agree": 334}.
- By class: {"criminal_assistance": {"both": 9, "new_only": 5, "old_only": 1}, "hate": {"new_only": 8}, "persona_claims": {"new_only": 18, "both": 19, "old_only": 8}, "profanity": {"new_only": 6, "old_only": 2, "both": 3}, "relational_hooks": {"new_only": 38, "both": 2}, "self_harm": {"new_only": 2}, "sexual_content": {"new_only": 2, "both": 6}, "simulation_obscured": {"old_only": 40, "both": 32, "new_only": 7}, "sycophancy": {"old_only": 19}, "violence": {"new_only": 8, "both": 2, "old_only": 1}}.
- Top-5 disagreement shapes: [["old[simulation_obscured] -> new[none]", 32], ["old[none] -> new[relational_hooks]", 24], ["old[sycophancy] -> new[none]", 15], ["old[simulation_obscured] -> new[persona_claims,simulation_obscured]", 9], ["old[none] -> new[hate]", 8]].

Note: the reader is the same model as the primary (different guide revision), so the two votes are correlated; the final
class set matches the reader on 776 of 777 decided rows.
