# SMM-BR001: conversation-branch keyword retrieval

Frozen before model inference on 2026-10-26.

## Question

Does indexing distinct discussion branches within a full conversation, instead of
only the whole conversation, improve source-level retrieval? This is candidate
retrieval, not answer generation or proof of downstream answer correctness.

## Initial complete cohort

All 200 LoCoMo questions and all 272 source conversations in their union from
`smm-sufficiency-luna-001/runtime.json`. The other two cohorts need 2,675 more
source extractions and are outside this initial complete cohort. No question,
answer, reference, or dependency annotation is supplied to extraction.

## Frozen extraction

Model `gpt-6-luna`, OpenAI subscription transport, reasoning `high`, zero tools.
Input: one complete source conversation with numbered message turns and source ID.
Output: every substantive discussion branch, each with a concise label, 3-12
normalized English keyword/short-phrase strings, and supporting turn numbers.
Proper names remain distinct; inflected common words use dictionary form.
Generic umbrella labels alone are insufficient. A branch may use non-contiguous
turns; one turn may support more than one branch. Greetings need no branch.
The model does not see the evaluation queries or gold labels. Inputs and outputs
are saved with source hashes and call metrics. Initial pilot checks only the
mechanical contract and whether actual multi-topic conversations are separated;
it cannot select prompts by retrieval scores.

## Frozen retrieval/evaluation plan

Index each branch as one independent document. For a question, use only original
question text; normalize words with the same fixed English stemmer for lexical
matching. Compute FTS5 BM25 over branch-keyword text, aggregate by maximum
branch score to each source, then rank source IDs. Compute MiniLM-L6-v2 vectors
for branch keyword texts and normalized question text, aggregate maximum cosine
similarity to each source. For both, suppress future sources per question clock
and deduplicate sources before Top N. Compare with frozen whole-conversation raw
BM25 and MiniLM baselines on exactly the same visible sources.

Report source-level Top 1-5 and Top 10: any required source-witness unit found,
all required units found, micro unit coverage, and per-question gains/losses.
Use the 178 unambiguous LoCoMo dependency labels for the main analysis and keep
22 ambiguous cases separate. No tuning or changing extraction after looking at
retrieval scores; a revised method would require a separate experiment ID.

## Limits

LoCoMo questions and sources were previously inspected in SMM research, so this
is a fixed-data comparison, not blind generalization. Branch extraction cost
and indexing latency must be reported. No claim about live data or answer
accuracy follows from source coverage alone.
