# Contributing new evidence

1. Keep `experiments/smm-baseline-001` and its sealed runs unchanged. Use a separate checkout for exploratory runs; add a new run ID, never overwrite a first output.
2. Keep all 75 canonical inputs, complete source text, references, timestamps, retrieval rankings, and semantic policy fixed for a model comparison. If any of these change, publish a separate experiment version.
3. Declare provider, exact model ID, effort, interface wrapper, timeout, sampling defaults, retry/continuation policy, and planned calls before inference. Do not place reference answers or reviewer notes in model inputs.
4. Preserve failures, first outputs, usage, and request hashes. Distinguish a transport retry from a semantic resample. Do not replace failed answers with a better attempt.
5. Review new answer content against actual source evidence. Do not copy old semantic labels onto changed outputs, grade by the mere presence of a number, or automatically mark every nonreference source unrelated. Separate semantic, format, citation, and availability failures.
6. Keep all25 reference comparisons and the P22/P25 ambiguity notes. Do not change the denominator after seeing new model outputs. Independent human review and blinded new cases are welcome as **separately labeled** evidence.
7. Publish no credentials, login files, authorization headers, private user history, or hidden reasoning text. Keep upstream provenance and licenses.

Offline regression check: `python3 -B tools/verify_publication.py`. No inference is needed for this check. Rerunning an online service does not guarantee byte-identical answers, even with the same model alias.
