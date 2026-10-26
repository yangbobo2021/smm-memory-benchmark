# SMM-B001：DeepSeek Flash 对比

日期：2026-10-26。模型deepseek-flash，thinking=enabled、reasoning_effort=low。复用25题×3任务，75份固定逻辑请求及原始完整会话；不重检索、不重编码、不提供gold或证据要点。

本次正式首次请求75次，其中生成失败0次。另2次最小兼容性探测（json_schema拒绝、json_object成功），不计成绩。没有语义重抽、结果修补或重试已有题。

## 固定评分结果

答题主分沿用冻结程序，格式失败和生成失败不能通过。P22/P25原有时间适用歧义单列，回答主分母23；筛选25题，以必要信息选齐且无确认无关误选为准。

| 模型 | 准确上下文完整回答 | 混合Top5筛选 | 混合Top5完整回答 |
| --- | ---: | ---: | ---: |
| gpt-6-luna | 21/23 | 22/25 | 19/23 |
| gpt-6.1-sol | 23/23 | 25/25 | 23/23 |
| glm-5.3-flash | 23/23 | 25/25 | 21/23 |
| glm-5.3 | 20/23 | 24/25 | 21/23 |
| deepseek-flash | 23/23 | 25/25 | 22/23 |

## 正文与协议失败分开

| 模型 | 准确上下文正文正确/23 | 混合候选正文正确/23 |
| --- | ---: | ---: |
| gpt-6-luna | 21/23 | 19/23 |
| gpt-6.1-sol | 23/23 | 23/23 |
| glm-5.3-flash | 23/23 | 21/23 |
| glm-5.3 | 22/23 | 23/23 |
| deepseek-flash | 23/23 | 23/23 |

正文诊断读取实际语义复核，区分内容答错、格式失败和无输出，不替换冻结主分。例如DeepSeek的P02混合回答给出了正确20打和有效来源，但增加type字段，冻结additionalProperties=false将其判为格式失败；没有删字段再冒充原始通过。GLM重复编号和超时的原记录与原分数也不改变。
DeepSeek另有P24准确上下文：26天正确，但把真实提供的received_at时间戳当成原文正文quote，逐字引用检查失败。日期不是捏造，metadata与正文引用的契约仍需区分；没有修补该首输出。

## DeepSeek逐题复核

本次已生成明确题未发现语义复核失败；仍需分别查看格式、引用逐字性及歧义题，不能由小样本推得通用可靠。

## 返回耗时

单位秒，下表仅成功返回输出的请求中位数（包含可能格式或语义错误的输出）；失败请求单列。非APP端到端时间，非并发/缓存/调度完全受控的纯模型速度比较。

| 模型 | 准确上下文回答 | 筛选 | 混合候选回答 |
| --- | ---: | ---: | ---: |
| gpt-6-luna | 4.62 | 4.30 | 5.21 |
| gpt-6.1-sol | 6.10 | 5.52 | 7.09 |
| glm-5.3-flash | 6.82 | 4.20 | 8.54 |
| glm-5.3 | 7.00 | 4.43 | 7.57 |
| deepseek-flash | 4.68 | 3.86 | 5.90 |

各模型错误题、格式错误、正文错误及返回延迟分布分别见failures.json、semantic-content-diagnostic.json和timing.json。DeepSeek的完整首次输出、服务回显模型名、request ID、system_fingerprint和token用量均保存；隐藏reasoning_content不保存。接口回显不是独立模型身份认证。

## 必须保留的接口差异

DeepSeek当前接口拒绝response_format=json_schema（HTTP400：This response_format type is unavailable now）。采用官方支持的json_object，将冻结请求中的同一份JSON Schema统一追加到system的格式约定中；原任务system前缀、user payload和每道题的schema内容保持一致，没有增加解题提示。额外3个离线契约测试验证了payload不变、schema仅用于格式、调用不重试、不留思考文本。

这保持了逻辑任务和评分，但实际wire prompt与原生schema路径不同。75个实际wire-body hash在推理前冻结，协议/适配器/runner随包保存，可审计与重跑。不能称与GPT Codex或GLM原生schema只有模型权重不同，尤其格式通过率会受服务约束能力影响。

本轮使用low思考，与此前生产探索中的DeepSeek非思考配置不同；旧非思考成绩没有复用。temperature和max_tokens采用服务默认，low标签不保证不同供应商投入相同计算量。

官方依据：[JSON输出](https://api-docs.deepseek.com/guides/json_mode/)、[思考参数](https://api-docs.deepseek.com/guides/thinking_mode/)。当前原生schema拒绝以preflight.json实际响应为证。

## 复现

在SMM-B001根目录使用Python>=3.11，无第三方Python包依赖：

```bash
python3 bench.py verify
python3 artifacts/deepseek-comparison-v1/verify_comparison.py
python3 bench.py score --run deepseek-flash-low-first
python3 bench.py report --runs gpt-6-luna,gpt-6.1-sol,glm-5.3-flash-low-first,glm-5.3-low-first,deepseek-flash-low-first --out artifacts/new-five-model-report.html
```

离线命令不调用模型。新模型重测需新run-id及明确凭证；本次首结果已经封存，runner拒绝覆盖已有run。原75输入、全部原文、参考与评分、适配器、实际wire哈希及原始final JSON均在同一实验目录中。
本次run_deepseek.py是固定本次身份的可审计执行快照，直接重跑会拒绝已有目录；未来新运行应新建protocol/run-id，保持同一内容和接口配置，不在旧目录覆盖结果。

仍是25道已知公开英文正例，每输入一次，语义标签来自研究助手逐题审阅，不是独立人类盲评；没有自然无答案、跨语言、企业文档或重复采样证明。没有修改SMM生产默认或旧结果。
