# SMM Memory Benchmark

**Frozen inputs, original model outputs, evidence reviews, and reproducible scoring for knowledge-retrieval research.**

This repository publishes **SMM-B001**, a 25-question, full-conversation reader experiment based on a fixed subset of [LongMemEval-cleaned](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned). It asks three separate questions:

1. Can a model answer when given the correct full conversations?
2. Can it select the necessary conversations from a fixed BM25 Top5 + vector Top5 union?
3. Can it answer from those same full candidates?

The selection and candidate-answer calls are independent. The selected output is **not** passed to the answer call. Retrieval rankings are frozen controls; this is not a new official LongMemEval leaderboard or a complete implementation of SMM.

**中文：本仓库公开测试原文、模型可见输入、最终输出、错误、耗时、用量、证据映射与评分，方便逐题检查“检索找到了，模型是否能选对、答对”。** 完整输入没有摘要或截断；隐藏思考正文不保存。详细说明见[输入输出查看指南](docs/IO_GUIDE.md)。

## Start here

- [BM25 as an Agent retrieval tool: completed lexical variants, authored query inputs, Top5/Top10 coverage, and decision-gate evidence review](analyses/bm25-route-review-001/README.md)
- [Five-route candidate-budget comparison: BM25/vector Top5, Top10, and their 5+5 union against answer dependencies](analyses/five-candidate-routes-001/README.md)
- [Agent sufficiency judgment and one follow-up BM25 search: GPT-6 Luna high, 257 cases](experiments/smm-sufficiency-luna-001/INDEX.md)
- [Raw BM25 Top1–Top5: at least one reference vs all references on 257 cases](analyses/bm25-any-reference-top1-top5/README.md)
- [Separate BM25 keywords and semantic queries: fixed 257-case input comparison](experiments/smm-query-input-001/README.md)
- [Each-route Top4 / Top5 union: complete-reference coverage on the same 257 cases](analyses/dual-route-top4-top5/README.md)
- [Role-separated BM25: 70% user + 30% assistant, with unchanged full-conversation control](experiments/smm-bm25-role-weight-001/README.md)
- [New-question retrieval validation: 32 fresh LongMemEval cases + 200 randomly sampled LoCoMo questions](experiments/smm-retrieval-generalization-001/README.md)
- [Text-evidence sensitivity of the new LoCoMo sample](analyses/smm-rg001-text-evidence/README.md)
- [Top1–Top5 complete-evidence coverage: BM25, vector, and their union](analyses/top-n-evidence-v1/README.md)
- [Browse all 25 cases and their inputs/outputs](docs/CASE_INDEX.md)
- [What was recorded, and what was not](docs/IO_GUIDE.md)
- [Complete Low / High comparison](experiments/smm-baseline-001/artifacts/high-effort-comparison-v1/README.md)
- [Case-by-case Low / High results](experiments/smm-baseline-001/artifacts/high-effort-comparison-v1/case-results.md)
- [Full machine-readable scores and reviews](experiments/smm-baseline-001/artifacts/high-effort-comparison-v1/comparison.json)
- [Original experiment definitions and runner documentation](experiments/smm-baseline-001/README.md)

## Published results

Each cell is **Low → High**. Answer scores use **23 clear questions**; P22 and P25 have temporal applicability ambiguities and remain separately reported. All 25 questions, original references, outputs, and reviews are included.

| Model | Correct-context answers /23 | Candidate selection /25 | Candidate answers /23 | Candidate-answer median, seconds |
|---|---:|---:|---:|---:|
| GPT-6-Luna | 21 → 23 | 22 → 25 | 19 → 23 | 5.21 → 6.95 |
| GPT-6.1-Sol | 23 → 23 | 25 → 25 | 23 → 23 | 7.09 → 12.89 |
| GLM-5.3-Flash | 23 → 23 | 25 → 25 | 21 → 21 | 8.54 → 23.02 |
| GLM-5.3 | 20 → 23 | 24 → 25 | 21 → 21 | 7.57 → 23.27 |
| DeepSeek Flash | 23 → 23 | 25 → 25 | 22 → 23 | 5.90 → 7.11 |

Scores preserve format and generation failures. Exact quotation, evidence support, and answer content are separate diagnostics. A full primary score does not imply every citation is valid. Latencies include returned outputs even when their format/content is wrong; no-output timeouts are reported separately.

There are **75 canonical task inputs**, **10 model/effort runs**, and **750 logical result records**: **746 generated outputs and 4 timeout records** across Low and High. These are logical records, not a claim of 750 newly billed calls: historical exact reuse is explicitly recorded. The High experiment added 375 first-attempt tasks, with 373 outputs and 2 timeouts. No failed task was resampled to replace its score.

## Reproduce offline

Python **3.11+**, standard library only. No API keys, model downloads, database, or embedding service are needed to verify the archived results.

```bash
git clone https://github.com/yangbobo2021/smm-memory-benchmark.git
cd smm-memory-benchmark
python3 -B tools/verify_publication.py

# Inspect one complete visible task input and its actual output.
python3 -B tools/inspect_case.py P06 --model gpt-6-luna --effort high --task candidate_answer
```

The verifier checks the publication snapshot, all frozen benchmark bindings, sealed runs, and all 750 input/output trace links. It does **not** call any model. Existing semantic labels can be replayed; their semantic truth is not established by a checksum.

To independently score a run or generate an HTML report:

```bash
cd experiments/smm-baseline-001
python3 -B bench.py score --run gpt-6-luna-high-first
python3 -B bench.py report \
  --runs gpt-6-luna,gpt-6-luna-high-first,deepseek-flash-low-first,deepseek-flash-high-first \
  --out artifacts/my-new-report.html
```

Files are written in exclusive-create mode. Choose a new filename or run ID instead of overwriting archived results. To test another model, see the [runner documentation](experiments/smm-baseline-001/README.md) and [contribution rules](CONTRIBUTING.md). Online inference requires your own authorized provider access and may consume paid or subscription quota.

## What this evidence supports

Correct source retrieval is insufficient to guarantee correct selection or answering. Models can miss a fact inside a correctly retrieved conversation, mistake suggestions for completed actions, mishandle temporal updates, or return invalid citations. On this slice, Luna improved with High; other models did not uniformly gain new correct answer content. See the paired per-case results rather than inferring a winner from totals alone.

The 25 English positive cases were already known during exploration. This is a **retrospective, single-sample study**, with research-assistant semantic reviews rather than independent human blind labels. There are no natural no-answer cases. Provider wrappers differ, and Low/High runs were not randomized contemporaneous repetitions. This cannot establish universal model superiority, production reliability, a global false-positive rate, or the causal effect of effort alone.

Frozen rankings and full source text are included; embedding weights and a from-scratch retrieval-index build are not. No private user chat history, API credentials, login state, authorization headers, or hidden reasoning text are distributed. Historical machine paths in some audit metadata are retained for provenance; offline verification does not require the original machine.

## Data and licensing

Upstream data: [LongMemEval-cleaned](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned), revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`. The dataset card declares MIT; the original copyright notice is retained. Exact versions and file hashes are in [dataset provenance](experiments/smm-baseline-001/provenance/dataset.json).

Original repository code/documentation is provided under [MIT](LICENSE). Third-party data keeps its original attribution; archived provider outputs are research records and are not represented as third-party MIT source code. See [NOTICE](NOTICE.md). To cite this artifact, use [CITATION.cff](CITATION.cff).
