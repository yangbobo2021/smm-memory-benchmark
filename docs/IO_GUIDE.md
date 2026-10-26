# 查看模型输入、输出与评分 / Input-output guide

## 从一道题开始

打开[题目索引](CASE_INDEX.md)，例如 [P06：每周几天健身课程](cases/P06.md)。每个题目页都链接到三个任务的完整输入、公开源对话、十个模型/档位的实际输出及对应评分文件。

也可以本地查看：

```bash
python3 -B tools/inspect_case.py P06 --model gpt-6-luna --effort high --task candidate_answer
python3 -B tools/inspect_case.py P18 --model glm-5.3 --effort high --task candidate_answer --section output
```

第二个例子会展示真实超时记录，`output` 为 null，不会生成一个替代答案。

## 输入实际记录了什么

`experiments/smm-baseline-001/requests/<task>/<Pxx>.json` 中：

- `request.system`：冻结的任务指令。
- `request.payload`：问题、历史参考时间、时区、匿名来源编号、完整原始会话，包含原始 USER/ASSISTANT 角色。
- `request.schema`：输出 JSON 契约。
- `request_sha256`：这一组 system/payload/schema 的哈希。
- `ledger`：实验审计用的原始来源映射。**ledger 不作为额外内容传给模型**。

`oracle_answer` 提供官方相关完整会话；`candidate_select` 与 `candidate_answer` 提供同一份 BM25 Top5 / vector Top5 去重并集。后两项 payload 相同，但两次模型调用完全独立。筛选不是回答的前置过滤器。

各服务封装也保留了实现：

- GPT：`codex_transport.py`。公开任务 system 外，还追加了禁工具的 base/developer 约定，并通过 Codex 订阅运行时提交 payload 和 outputSchema。Codex 的私有系统提示没有保存，不能把可见任务文件称为整个隐藏运行时提示的逐字快照。
- GLM：`http_transport.py`。相同任务加固定 system 包装，通过 Chat Completions 原生 JSON Schema 提交；记录端点、effort 和 provider defaults。
- DeepSeek：`artifacts/deepseek-comparison-v1/deepseek_transport.py` 和 High 对应适配器。服务拒绝原生 JSON Schema，因此使用 JSON object，并把同一 schema 作为格式附录。Low/High 的实际请求体哈希在对应 protocol 中冻结；请求体可由适配器重建。授权头不保存。

因此，同一模型 Low/High 保持原接口只改 effort；跨供应商仍有封装差异，不能当纯模型权重单因素实验。

## 输出实际记录了什么

原 GPT Low 输出在 `baselines/<model>/records/<task>/<Pxx>.json`；其他运行在 `runs/<run-id>/records/<task>/<Pxx>.json`。

- `output`：实际最终 JSON，包括答案、选中来源、claims、引文和 missing；筛选任务只输出来源编号。
- `error`：首次错误，失败时保留空输出；不得用一次补跑覆盖它。
- `metrics`：实际保存的耗时、模型/provider 标识和服务用量。不同服务字段和计费口径可能不同。
- `request_sha256`：绑定准确输入。
- `raw_receipt` / `raw_response`（存在时）：指向当时保存的原始执行收据或已去除隐藏思考/授权信息的服务最终响应。
- `.started.json`（新运行）：记录调用开始标记，便于核对首次尝试。

公开的是**750条独立模型任务的可见输入与最终输出**，不是自主 Agent 工具调用轨迹。这些任务禁用了工具，记录中的 `tool_calls` 为0。没有保存隐藏思考正文，不能查看模型内部如何推理；也不能从服务回显名称独立认证模型权重身份。

历史收据的保留程度不完全相同：部分有原始 final JSON 文本和服务 request ID，其他只有解析后的实际 JSON 与执行元数据。数据来源和精确复用标记保留，不能把后生成的索引当成新推理结果。

## 评分与原始输出分开

`reviews.json` 是后续研究助手对实际输出和原文的语义审阅，不是模型输入，不是新的模型裁判结果。评分绑定输入/输出哈希，不能换答案后沿用评分。

- `complete_answer`：核心问题是否完整答对。
- `official_reference_match`：是否与原参考答案内容一致。
- `evidence_semantic_valid`：引用及附加主张是否有正确语义支持。
- 机械校验另检查 JSON 格式、重复来源编号、引用是否逐字存在。

筛选依据36项必要信息，43段官方参考会话含冗余历史，不要求全部选齐。新选中非参考来源必须另行审阅。主分、正文、格式、引证和超时要分开看；例如 GLM-5.3 High P06 答案“四天”正确，但来源编号重复，主分仍判失败。

P22、P25 的时间适用性有歧义，原参考、全部输出、判断理由都保留；回答主分使用其余23题。这里的“审阅”由研究助手完成，不是外部独立人类盲评。

## English summary

Use the [case index](CASE_INDEX.md) to follow any question to its canonical visible input, all ten model/effort outputs, and separate evidence reviews. `docs/traces.jsonl` is a normalized **path-and-hash index** of 750 logical records; it does not replace or alter original receipts. The benchmark folder is copied byte-for-byte from the sealed experiment snapshot.

Only `request` is submitted as the logical task; `ledger`, references, and reviews are evaluation metadata. Provider wrappers are archived in source; Codex private runtime instructions and hidden reasoning text are not available. Some providers retain a sanitized final response, while older receipts retain parsed JSON only. No tool-enabled autonomous Agent loop was tested in these three tasks.
