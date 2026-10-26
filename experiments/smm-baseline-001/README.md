# SMM-B001：完整对话下的模型基线

版本：**1.0.0**。记录日期：2026-10-26。

这是 SMM 的第一个固定输入、固定规则、可以独立搬走复现的模型对比基线。目录保存了三项实验所需的数据、首次结果、评分和执行工具。此次整理没有重新调用模型。

| 主指标 | GPT-6-Luna low | GPT-6.1-Sol low |
| --- | ---: | ---: |
| 1. 准确上下文：完整回答正确 | **21/23** | **23/23** |
| 2. BM25/向量各 Top5 混合：相关筛选成功 | **22/25** | **25/25** |
| 3. BM25/向量各 Top5 混合：完整回答正确 | **19/23** | **23/23** |

回答主指标使用 23 道可明确判断的题。P22“下载是否代表开始使用”、P25“早起偏移是否适用于后来更新的作息”存在隐含假设，单独保留。**全部 25 道题、原参考答案和两模型结果没有删除。**这个分层来自此前的复核，不是独立盲测。

全 25 题的原参考答案内容匹配分别为：准确上下文 Luna **22/25**、Sol **25/25**；混合候选 Luna **20/25**、Sol **25/25**。内容匹配、完整答复、依据成立是三个不同指标。

## 三项任务

1. `oracle_answer`：准确提供官方标注的全部相关完整会话，共 43 段次；模型回答问题。这是每个模型自己的理想输入基线。
2. `candidate_select`：原始问题的 BM25 Top5 与向量 Top5 合并去重，加载完整会话；模型只输出相关对话编号，不生成答案、原因或引句。
3. `candidate_answer`：同样的完整混合候选，模型回答问题，与自己的 `oracle_answer` 结果比较。

后两项输入逐字相同、分别调用模型，互不传递结果。不是先筛选、再将筛选结果交给回答器。每题混合候选为 5～9 段，会话按原始时间排列；保留完整原文、角色和时间，没有摘要、截断、自动补搜或模型生成的事实。

这是**固定检索候选的模型实验**。测新模型时不重算 BM25、向量、不改变排名或提示。目录包含完整语料和冻结排名，因此复现三项实验不需要原项目数据库、向量服务或 embedding 权重。从零重建 embedding/更换检索算法属于另一项实验，应另开版本。

## 可以直接复现的内容

只需 Python **3.11 或以上**，离线重放和评分不需要安装第三方 Python 包：

```bash
python3 bench.py verify
python3 bench.py replay
python3 bench.py report --out artifacts/my-baseline-report.html
```

`verify` 核对冻结文件 SHA256、完整原文、参考会话、时间、输入、首次输出和评分绑定，再独立重新计算两模型三个主分数。`replay` 使用已有真实结果，**零模型调用**。报告输出文件采用新建模式，不覆盖旧文件。

也提供实际搬迁检查：复制到系统临时目录，禁止访问原目录和网络，不加载第三方 Python 包，再核对评分、导入、待审阅状态和篡改检测。只检查离线流程，不请求模型：

```bash
python3 check_portability.py --out artifacts/portability-new.json
```

首次封存的验证结果在 `artifacts/verification.json`、`artifacts/portability.json`，可直接查看 `artifacts/baseline-report.html`。150 条是两模型的既有逻辑执行结果；其中 Luna 准确上下文的 19 条沿用完全相同输入下的首次结果，复用收据一起保存。此次打包新增模型调用为零。

“复现”指输入、协议、数据和已有结果的评分可以重现。再次请求在线模型是一个新运行；即使模型名称相同，也不能保证随机采样或服务更新后的输出逐字相同。

## 测试其他 Codex 订阅模型

需要机器上已有 Codex CLI，且已完成订阅登录。工具只使用当前登录，不打包或复制登录凭证。

```bash
python3 bench.py run \
  --backend codex --model MODEL_ID --effort low \
  --run-id MODEL_ID-low-first
```

默认执行 25 题 × 3 任务，共 **75 次首次调用**。模型 ID 和档位必须能在本机 `model/list` 中找到；不会悄悄换模型或档位。首次错误会保留并停止，没有语义重抽。每次运行使用新 `run-id`，已有记录不能覆盖。

可用 `--cases P06 --tasks oracle_answer,candidate_select,candidate_answer` 做明确标记的小规模接入检查。小检查不是完整 25 题分数，也不能与后续正式运行择优拼分。

与历史基线一样，Codex 推理运行在独立临时会话中，禁止工具访问，传入同一任务提示和 JSON Schema。固定了任务数据和 `low` 档，采样温度使用服务默认值，不能称确定性模型实验。

## 兼容 API 与外部模型

提供不依赖 SDK 的 Chat Completions 适配器。密钥只从指定环境变量读取，不写进运行记录：

```bash
python3 bench.py run \
  --backend chat --model MODEL_ID --run-id MODEL_ID-api-first \
  --base-url https://PROVIDER.example/v1 --key-env SMM_API_KEY \
  --effort omit --response-format json_schema
```

不支持结构化输出的服务，可显式选择 `--response-format json_object`。不支持 `reasoning_effort` 的服务使用 `--effort omit`。这些差异会写入运行配置，不自动尝试多个参数直到成功。

HTTP 和 Codex 运行时的包装不同，**跨适配器比较是“模型＋服务包装”的比较，不能说只改变模型**。同一适配器、相同配置的比较更容易解释。HTTP 结果中的模型名只作为服务返回信息，不视为可信身份认证。该适配器已做本地协议测试；未在整理过程中调用用户付费 API。

其他接口可以导出/导入，保持固定输入与结果绑定：

```bash
python3 bench.py export --out exported-requests.jsonl
# 外部工具逐条执行，每行返回 task、case_id、request_sha256、output、metrics。
python3 bench.py ingest --model MODEL_ID --run-id MODEL_ID-import \
  --file external-results.jsonl
```

导出文件只有模型应看到的请求，不包含参考答案或评分。导入必须恰好覆盖声明的题目/任务，不允许重复、缺项或更换输入哈希。可以同样使用 `--cases` 和 `--tasks` 指定明确的子集。

## 新模型如何评分

编号合法性、引用是否逐字来自给定原文、来源覆盖和注册证据覆盖可以自动检查。**答案语义不能靠数字出现、关键词匹配或对话编号来冒充正确。**

```bash
python3 bench.py review-template --run MODEL_ID-low-first \
  --out runs/MODEL_ID-low-first/review-template.json
```

阅读实际原文、问题和输出后，填写模板中的判断与理由，保存为该运行的 `reviews.json`。回答的三个字段分别是：

- `official_reference_match`：内容是否覆盖原参考答案；同义表达和有效中间步骤可以成立。
- `complete_answer`：是否完整回答问题；两道歧义题保持空值、另行解释。
- `evidence_semantic_valid`：所报依据是否真正支持这些主张，是否把建议当事实、把旧状态当新状态，或者附加了无据的说法。

评分文件绑定实际输出和输入哈希。改变答案后不能沿用旧评分。历史评分来自原研究助手的逐题复核，**没有独立人工盲评**；新模型应按同样规则审阅，而不是以希望得到的模型排名为目标。

```bash
python3 bench.py score --run MODEL_ID-low-first \
  --out artifacts/MODEL_ID-low-first-score.json
python3 bench.py report --runs gpt-6-luna,gpt-6.1-sol,MODEL_ID-low-first \
  --out artifacts/three-models.html
python3 bench.py seal-run --run MODEL_ID-low-first
```

未完成语义评分时，回答主分数显示 `null`，不会假装已通过。`seal-run` 仅封存完整且已审阅的 75 条运行，之后文件被修改会被检测出来。

## 筛选成功到底是什么

主指标是：**选中对话覆盖该题所有注册的必要信息，并且没有确认的无关误选**，分母是 25 道题。共有 36 项标注信息要点，一段对话可含多个要点，一个要点也可有多个支持来源。

另列“43 段基准会话是否全选齐”，但不要求复刻所有旧状态和重复旁证。例如市场收入题，选中最新 420 美元记录就够了，没有选旧收入记录不算必要信息遗漏。

Luna 共选出 39 段次，Sol 选出 43 段次。无关误选为 **0/39、0/43**：分母是各自选出的数量，不是输入数量。两模型输入相同。

若新模型选中不在基准列表里的对话，工具会要求在 `selection_extra_labels` 中审阅其是否为直接依据、相关历史或无关内容；**不会自动把非基准来源算错**。有效替代证据可附 `alternative_evidence`，给出 `atom_id` 和原文 `quote`。补充标注会单列，冻结的注册覆盖仍保留，不能借此无痕修改原基准。

本测试没有自然无答案问题，因此不能把所选结果中的无关比例称为全库误选率，也不能声称已验证拒答能力。

## 已观察到的结果与结论

- BM25 Top5 覆盖 43/43 段基准会话；向量 Top5 覆盖 41/43；合并后 25/25 题全部覆盖。向量遗漏一段项目重复旁证及网络活动题的唯一来源。
- Luna 混合候选中，聚会题从三次退为只确认一次、十二月活动从三天漏成两天；材料都已完整提供。
- Luna 鸡尾酒题使用了正确的对话，却把其中助手建议的葡萄柚算成用户用过。正确对话编号不等于正确事实使用。
- 独立筛选 Luna 必需信息齐 22/25，Sol 25/25；两者此次没有选中无关对话。
- Sol 保持了 23 道明确题的完整作答；两道争议题虽匹配参考，不能说其隐含假设已由原文唯一证明。

这支持本轮的三个判断：**正确的信息已检索到，Agent 仍可能答错；正确相关信息已提供，Agent 仍可能漏选；模型选择会影响观察到的结果。**它不证明所有场景都有同样正确率，也不能用单次采样证明结果变化全部由上下文噪声造成。

Luna 还有两处非逐字引用，以及一个不影响毕业顺序答案的无据 `aunt` 称谓。引用复制、附加主张和核心答案分开保存，不能将它们混成“全都答错”或“全都依据正确”。

## 目录与版本规则

```text
experiment.json          实验版本、三项定义和主指标
data/                    25份完整语料、原始会话审计、冻结检索排名
requests/                75份固定模型请求及来源映射
evaluation/              语义规则和两道争议题说明
baselines/               两模型150条执行结果、原收据及逐题评分
provenance/              原始数据版本、历史评分、精确复用原结果
licenses/                上游许可
bench.py / harness.py    独立运行、核验、评分和报告
codex_transport.py       独立的Codex订阅适配器
http_transport.py        兼容API适配器
tests/                   离线回放、篡改、评分与接口契约测试
check_portability.py      搬迁、断网、禁止访问原项目的离线检查
manifest.json            冻结文件SHA256
runs/                    新模型运行；不改原基线
artifacts/               核验、可迁移性报告及比较报告
```

数据、提示、候选、语义规则发生变化时，应建立新实验版本并重新计算基线；仅更换模型时，在本版本下建立新运行。不得重抽后取最好结果，不得用筛选命中替代答案正确率。

上游 LongMemEval 数据与代码版本记录在 `provenance/dataset.json`，原始参考与问题保持不变。兼容 API 的格式依据 [OpenAI Structured Outputs 文档](https://developers.openai.com/api/docs/guides/structured-outputs)；实际服务支持程度以其返回为准。
