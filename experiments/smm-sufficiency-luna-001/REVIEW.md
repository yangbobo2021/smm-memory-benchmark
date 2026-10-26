# Post-run interpretation audit / 结果解释复核

The [frozen numeric report](README.md) is unchanged. This is a **post-run, non-blind researcher review**, not a replacement gold set or an independently judged answer score. It checks whether source-witness coverage is a sound proxy for information sufficiency in visible counterexamples. [Inputs and outputs](METHOD.md) remain available case by case.

## What the frozen scores say

Across 257 cases, 25 are pre-declared ambiguous for the dependency metric. Of the remaining 232, original BM25 Top5 contains all pre-declared dependency witnesses in 199 and misses at least one in 33. Two first-round calls ended in 429 and are service errors. Among valid first-round outputs, Luna high judged 176/197 witness-complete cases sufficient and 23/33 witness-incomplete cases insufficient. It initiated 23 necessary searches; new Top5 results covered at least one missing witness in 17/23 and all missing witnesses in 14/23. Counting the ten cases that stopped before searching, 14/33 witness-incomplete cases ultimately reached full witness coverage; 8/33 both reached it and ended with a “sufficient” decision. These are **source-witness and action metrics**, not answer accuracy or a proof that all possible information is known.

## An initial “premature stop” can mean different things

The frozen dependency label flags ten clear-scope cases where at least one pre-declared witness was absent and the Agent stopped. The examples below show why this cannot be called a ten-case semantic error rate without inspecting the actual text.

| Case | Visible outcome | Post-run interpretation |
|---|---|---|
| [C028](records/round1/C028.json) | Answered **3** dogs: Scout, Toby, Buddy. | [One visible conversation](../smm-retrieval-generalization-001/data/sources/c18c87e5c3df2b81e03dabf48.json) explicitly names all three. Two older pre-declared sources were absent, but the answer is supported by this alternative source. This is a limitation of the frozen witness annotation, not a clear early-stop failure. |
| [C081](records/round1/C081.json) | Said Dave wants to repair and restore broken things. | The visible quote about transforming something broken into working condition supports the recorded answer's sense (“take something broken and make it awesome”). The pre-declared source is absent, so this is another plausible alternative-support case. |
| [C073](records/round1/C073.json) | Suggested learning languages for Tim's travel dream; recorded answer is writing a travel blog. | The question asks what **would be a good hobby**, not for a uniquely named hobby. Language learning is plausible, but not the benchmark's intended response. Treat as an open-question ambiguity; one cited quote also fails exact-text validation. |
| [L030](records/round1/L030.json) | Gave **8** years; recorded answer is **10**. | The model used high school and university but missed the community-college period in a source outside Top5. Clear substantive premature stop. |
| [C024](records/round1/C024.json), [C027](records/round1/C027.json), [C037](records/round1/C037.json), [C157](records/round1/C157.json), [C168](records/round1/C168.json), [C187](records/round1/C187.json) | Respectively omitted art/cooking, omitted violin, missed Sam's gastritis and Evan's palpitations, omitted gym/church, described preseason rather than the game season, and answered dogs instead of turtles. | These six show substantive omission or substitution against the recorded answers. C037 is a particularly clear missing-event example. C157 also has an exact-quote failure; that is separate from its missing places. |

This review finds **seven substantive early stops, two alternatively supported stops, and one open-question ambiguity among these ten**. It is a diagnostic reading of selected source text and recorded answers, not an adjusted score or a claim that the remaining 247 cases were semantically checked.

## A “failed to stop after witness recovery” can also be reasonable

Six cases reached all pre-declared source witnesses through one extra search but the model still said “insufficient”: [L005](records/round2/L005.json), [L011](records/round2/L011.json), [L012](records/round2/L012.json), [C035](records/round2/C035.json), [C135](records/round2/C135.json), and [C183](records/round2/C183.json). Their outputs identify concrete unresolved issues:

- L005: the airline of a January 15 flight is not established; other flights may be missing from an all-flights order.
- L011: several baking mentions may describe the same occasion, and dates are not all explicit.
- L012: the Brooklyn festival lacks a date, so the full event order remains uncertain.
- C035: Florida and Oregon are found, but the records do not establish that there were no other vacation states.
- C135: “a few weeks in Phuket” does not establish that the trip covered **most** of September.
- C183: later injury mentions do not identify the body part or establish whether they are distinct ankle injuries.

Some of these cautions may be stricter than the benchmark's expected answer convention; they are **not automatically failures of the Agent's sufficiency judgment**. The frozen source-witness label only proves that selected documents are present. It does not prove a closed-world list, an exact count, a dated ordering, or that the wording of the question is entailed by those documents. The 8/33 “recovered and stopped” value therefore should not be read as an end-to-end answer success rate.

## Other evidence limits

Five returned outputs have at least one exact-quote validation failure: [C015](records/round1/C015.json), [C062](records/round1/C062.json), [C073](records/round1/C073.json), [C148](records/round1/C148.json), and [C157](records/round1/C157.json). The scorer keeps these decisions and reports quotation validity separately; exact-quote failure alone does not establish whether the underlying claim is true.

The complete attempt audit is reproducible with `python3 -B experiments/smm-sufficiency-luna-001/audit_execution.py`. It verifies 257 first-round records, 60 second-round records, four hash-bound pilot reuses, 349 new physical attempts for 313 new logical calls, 36 first 429s, 34 successful same-request retries after at least 30 seconds, and two terminal 429s. The inference transport's internal retries are not visible, so these are application-level counts.

**Correction to the generated [README](README.md):** its final offline replay command accidentally names the earlier `smm-sufficiency-001` directory. The correct command is `python3 -B experiments/smm-sufficiency-luna-001/score.py --verify --check`. The generator and generated report remain unchanged to preserve their frozen hashes; this correction does not affect inputs, outputs, or scores.
