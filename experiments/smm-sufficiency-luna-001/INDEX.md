# SMM sufficiency and one follow-up search: GPT-6 Luna high

This study gives an Agent each question's **original full-conversation BM25 Top5**. It decides whether the visible text is sufficient. Only when it says information is missing does it write one new BM25 query; the system ranks the original corpus, excludes the five already seen conversations, gives it up to five new full conversations, and asks once more. No vector search, third retrieval, prompt tuning during the run, or answer-score grading is involved.

The run contains **257 questions** in three separate cohorts (25 / 32 / 200), 257 first-round and 60 second-round model records. All inputs, outputs, rankings, source bindings, and application-level retries are retained. The model is GPT-6 Luna at high reasoning effort through the existing OpenAI Codex subscription. Four hash-verified first-round pilot records were reused from the [pilot](../smm-sufficiency-luna-pilot-001/README.md); the rest were new calls. Two calls ended in 429 after one identical-request retry and are counted as service errors.

Read the [frozen numeric report](README.md) together with the [post-run interpretation audit](REVIEW.md). The main source-witness metric is deliberately narrow: finding every pre-declared document is not the same as proving that a list is exhaustive, a count exact, or an answer correct. The audit documents both real early stops and cases where a single visible document already supported the answer despite missing other pre-declared witnesses. It does not alter frozen scores.

The [method and label definitions](METHOD.md), [machine-readable results](results.json), [per-group summary](summary.csv), and [execution audit program](audit_execution.py) support independent inspection. To replay the scores without model calls:

```bash
python3 -B experiments/smm-sufficiency-luna-001/score.py --verify --check
python3 -B experiments/smm-sufficiency-luna-001/audit_execution.py
```

The generated report's final replay command has an old directory name; the commands above are the corrected ones. Original model outputs and failed requests were not rerun to improve scores. This is a retrospective test on previously used questions with researcher-reviewed dependency labels, not an independent blind benchmark or a production reliability estimate.
