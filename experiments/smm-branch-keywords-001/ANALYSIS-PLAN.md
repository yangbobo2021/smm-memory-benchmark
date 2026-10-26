# Pre-score controls (recorded before all source extractions finished)

The primary protocol compares the proposed branch-keyword routes against the
frozen historical routes. To separate the effect of **query normalization** from
the effect of **branch indexing**, run two additional controls using the exact
same normalized original question as the branch routes:

- BM25 on complete source text with FTS5 `porter unicode61`, using the same
  stopword filtering and OR expression as branch BM25.
- MiniLM-L6-v2 on 224-token/32-overlap complete-source windows, averaged and
  normalized as in the historical vector route, using the same normalized query
  text as branch vectors.

All routes rank **unique complete conversations**, within the same per-question
visible source IDs and clock. Score the fixed 178 clear LoCoMo dependency cases
at Top 1-5 and Top 10. Do not change prompts, source keywords, rank formulas,
or controls based on results. Report the 22 uncertain dependency cases
separately. This addendum changes analysis only; it does not change the frozen
source extraction requests or model outputs.

Mechanical output-contract repair, fixed before any retrieval scoring: if a
model response otherwise validates but a branch has more than 12 keywords,
retain its first 12 in the scored index. If a tiny branch has exactly two
keywords, retain both rather than invent a third. Preserve the complete raw
response, error receipt, and a separate hash-bound adjudication. No new model
call or keyword choice by evaluation result. Any other validation failure stops
the run for manual investigation.

As a secondary complementarity check, take BM25 Top5 and vector Top5 from the
same index variant, deduplicate by source ID, and measure dependency coverage
at the resulting (at most 10) source budget. Run this for historical raw
whole-conversation routes, normalized whole-conversation controls, and branch
routes. Do not treat a 5+5 union as a Top5 result.
