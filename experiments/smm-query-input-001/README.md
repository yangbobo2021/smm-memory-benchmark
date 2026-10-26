# SMM-QI001：为 BM25 与向量分别设计查询输入

**结果：这批关键词输入改善了 BM25；向量的自然语言改写没有稳定收益；两路都改写后合并有所改善，但仍会漏检和回退。**

沿用原25题、后续LongMemEval32题、LoCoMo200题；每题每路一个输入。输入审核和协议冻结后才产生本轮排名。只改变查询，不改变原文、切片、向量模型、BM25公式、时间可见性或候选预算。

这是已用题上的输入设计诊断，不是新盲测。输入由本任务 Codex 作者编写并复核，未引入答案专有信息；作者有项目历史知情，未经过外部独立输入质量评审，不能称最优输入或运行时Agent的稳定能力。

## 主结果：全部官方参考对话取齐

| 测试组 | BM25 原问题→关键词，Top5 | 向量 原问题→语义改写，Top5 | 各取Top4合并，原→改 | 各取Top5合并，原→改 |
|---|---:|---:|---:|---:|
| original25 | 25/25 → 25/25 | 23/25 → 23/25 | 25/25 → 25/25 | 25/25 → 25/25 |
| longmemeval_new32 | 20/32 → 24/32 | 21/32 → 20/32 | 22/32 → 24/32 | 25/32 → 27/32 |
| locomo_random200 | 156/200 → 162/200 | 115/200 → 108/200 | 162/200 → 169/200 | 169/200 → 176/200 |

每路Top5是去重后最多10段对话，合并后不再截成5段；参考对话取齐不是最终回答正确率。

## 完整 Top1–5 与预注册四种组合

### original25

| 方法 | Top1 | Top2 | Top3 | Top4 | Top5 |
|---|---:|---:|---:|---:|---:|
| bm25_raw | 12 | 19 | 22 | 25 | 25 |
| bm25_rewritten | 11 | 21 | 24 | 25 | 25 |
| vector_raw | 11 | 18 | 20 | 23 | 23 |
| vector_rewritten | 11 | 18 | 21 | 22 | 23 |
| union_raw_raw | 16 | 21 | 23 | 25 | 25 |
| union_rewritten_raw | 14 | 21 | 25 | 25 | 25 |
| union_raw_rewritten | 15 | 21 | 23 | 25 | 25 |
| union_rewritten_rewritten | 13 | 21 | 25 | 25 | 25 |
### longmemeval_new32

| 方法 | Top1 | Top2 | Top3 | Top4 | Top5 |
|---|---:|---:|---:|---:|---:|
| bm25_raw | 4 | 16 | 18 | 18 | 20 |
| bm25_rewritten | 4 | 17 | 20 | 20 | 24 |
| vector_raw | 4 | 13 | 18 | 18 | 21 |
| vector_rewritten | 4 | 14 | 17 | 18 | 20 |
| union_raw_raw | 5 | 18 | 18 | 22 | 25 |
| union_rewritten_raw | 6 | 19 | 20 | 22 | 26 |
| union_raw_rewritten | 6 | 17 | 20 | 22 | 24 |
| union_rewritten_rewritten | 7 | 19 | 22 | 24 | 27 |
### locomo_random200

| 方法 | Top1 | Top2 | Top3 | Top4 | Top5 |
|---|---:|---:|---:|---:|---:|
| bm25_raw | 91 | 129 | 138 | 148 | 156 |
| bm25_rewritten | 97 | 129 | 140 | 153 | 162 |
| vector_raw | 50 | 78 | 90 | 107 | 115 |
| vector_rewritten | 51 | 72 | 93 | 102 | 108 |
| union_raw_raw | 104 | 140 | 152 | 162 | 169 |
| union_rewritten_raw | 109 | 145 | 156 | 170 | 176 |
| union_raw_rewritten | 105 | 139 | 152 | 163 | 169 |
| union_rewritten_rewritten | 109 | 141 | 156 | 169 | 176 |

中间两种组合是预先注册的诊断：改BM25+原向量、原BM25+改向量。不能根据成绩挑选其中最好者冒充事前确定的主方案。

## Top5逐题增益与回退

| 数据组 | 对照 | 新增取齐 | 原本取齐但本次遗漏 |
|---|---|---|---|
| original25 | bm25_raw → bm25_rewritten | 0：无 | 0：无 |
| original25 | vector_raw → vector_rewritten | 1：P10 | 1：P06 |
| original25 | union_raw_raw → union_rewritten_rewritten | 0：无 | 0：无 |
| longmemeval_new32 | bm25_raw → bm25_rewritten | 5：L005, L009, L012, L015, L022 | 1：L028 |
| longmemeval_new32 | vector_raw → vector_rewritten | 1：L014 | 2：L011, L017 |
| longmemeval_new32 | union_raw_raw → union_rewritten_rewritten | 4：L009, L014, L018, L022 | 2：L006, L028 |
| locomo_random200 | bm25_raw → bm25_rewritten | 14：C021, C027, C035, C037, C092, C094, C118, C119, C137, C161, C168, C169, C183, C198 | 8：C008, C015, C075, C135, C158, C180, C186, C194 |
| locomo_random200 | vector_raw → vector_rewritten | 2：C008, C183 | 9：C023, C058, C077, C079, C081, C107, C139, C162, C164 |
| locomo_random200 | union_raw_raw → union_rewritten_rewritten | 11：C021, C027, C037, C092, C094, C118, C119, C120, C137, C161, C168 | 4：C075, C081, C149, C186 |

## 参考覆盖与候选成本

| 数据组 | 合并原/原→改/改，Top5参考段次覆盖 | 平均候选数原→改 | 改写后至少一条参考命中 | 改写后仍未取齐题数 |
|---|---:|---:|---:|---:|
| original25 | 43 → 43 / 43 | 7.520 → 7.040 | 25/25 | 0 |
| longmemeval_new32 | 65 → 67 / 72 | 7.625 → 7.188 | 31/32 | 5 |
| locomo_random200 | 219 → 228 / 265 | 8.175 → 8.075 | 191/200 | 24 |

## 具体输入与结果

### C037

What health scares did Sam and Evan experience?

BM25：`Sam Evan health scare scares`

向量：The health scares experienced by Sam and by Evan.

| 参考对话 | 原BM25→改写 | 原向量→改写 |
|---|---:|---:|
| c8b39ab3ed8428d688548cf45 | 14 → 3 | 22 → 22 |
| cd387b85982a45e4f67498a15 | 12 → 2 | 18 → 18 |
| ce49b7c6f8092a7995fd418ac | 4 → 1 | 2 → 3 |

保留人物与health scare/scares，三个真实健康事件参考从第4/12/14提高到第1/2/3。原文确实使用单数health scare，改写没有加入具体病名。

### C035

What states has Maria vacationed at?

BM25：`Maria vacation vacationed trip travel traveled`

向量：The states Maria visited on vacations or leisure trips.

| 参考对话 | 原BM25→改写 | 原向量→改写 |
|---|---:|---:|
| c20b2e1081a5503e3f47000c5 | 12 → 2 | 3 → 3 |
| cef8a76a54ca457dba453a63e | 6 → 4 | 2 → 1 |

补充vacation/trip/travel等表达，Florida与Oregon两段实际度假/公路旅行记录从第12/6提高到第2/4；输入没有加入两个地点。

### L011

How many times did I bake something in the past two weeks?

BM25：`bake baked baking`

向量：Occurrences of things I actually baked during the past two weeks, to count separate baking occasions.

| 参考对话 | 原BM25→改写 | 原向量→改写 |
|---|---:|---:|
| cb417665b8bd4b27a3a569f66 | 18 → 4 | 3 → 3 |
| cbfdb349c786606dbc3f659cb | 19 → 8 | 5 → 4 |
| ce5a48c01b09bfdba49972c9e | 6 → 2 | 4 → 7 |
| cff265636c0c7608295c5c5d6 | 11 → 5 | 2 → 1 |

关键词仅bake/baked/baking，去掉something/times等普通词后，四个参考的BM25排名明显改善，但单路仍未全部进入Top5。向量改写还把一条从第4降到第7；两路互补使合并仍取齐。

### L028

Who did I meet with during the lunch last Tuesday?

BM25：`lunch Tuesday met person`

向量：Who I met for lunch last Tuesday.

| 参考对话 | 原BM25→改写 | 原向量→改写 |
|---|---:|---:|
| cfb58939b84bf560e87d4500a | 5 → 7 | 11 → 14 |

真实用户原文是“catch up with Emma ... over lunch today”，Tuesday来自会话日期，不在对应原句中。关键词改写并没有解析日期，并且其他对话的Tuesday等词仍可抢占名次；唯一参考从BM25第5退到第7，向量也从第11退到第14。不能事后加入Emma来修复这题。

### C186

Does James live in Connecticut?

BM25：`James live lives Connecticut`

向量：Whether James lives in Connecticut.

| 参考对话 | 原BM25→改写 | 原向量→改写 |
|---|---:|---:|
| cbb821dcf1cbe29465f76da7d | 5 → 21 | 19 → 20 |

官方参考原文提及在Stamford的收容所领养狗，不直接包含Connecticut/live。改写无法凭空知道未知线索Stamford，引用源从BM25第5退到第21。此题带有地域常识与居住推断，不能把领养地点等同明确居住事实，也不按结果改标注。

## 原25题必要证据口径

| 方法 | Top1 | Top2 | Top3 | Top4 | Top5 |
|---|---:|---:|---:|---:|---:|
| bm25_raw | 16 | 20 | 23 | 25 | 25 |
| bm25_rewritten | 14 | 22 | 25 | 25 | 25 |
| vector_raw | 14 | 19 | 21 | 24 | 24 |
| vector_rewritten | 14 | 19 | 22 | 23 | 23 |
| union_raw_raw | 19 | 22 | 24 | 25 | 25 |
| union_rewritten_raw | 17 | 22 | 25 | 25 | 25 |
| union_raw_rewritten | 18 | 22 | 24 | 25 | 25 |
| union_rewritten_rewritten | 16 | 22 | 25 | 25 | 25 |

## 核验与边界

原257题BM25 Top10与向量Top10均重放原顺序；原分数最大差 0.0。40844切片、2947来源保持不变。

本次只编码 257 个改写查询，另编码25个旧查询做原25向量排名重放；0新文档编码、0外部生成模型API调用。编写改写本身由Codex完成，不能将整个实验称为没有使用大模型。

查询编码合计 0.715 秒，模型加载 0.671 秒。排名算术阶段共 0.496 秒，包含本轮与旧排名重放，不是线上请求P95，不包括作者编写/审查查询的耗时。

作者在运行前检查了语义、范围、时间和是否引入答案；精确人名/宠物名检查480项无遗漏。该检查只验证名称保留，不证明语义或查询最优。时间和否定文字不会自动变成检索引擎的硬过滤。

本轮结果支持：查询表达确实影响召回，关键词改写能够改善部分词面匹配；不支持“只要写得更清楚，向量就一定更好”，也不支持“足够好的单个查询就能保证找全”。不得以此次数据继续改写并挑选最好成绩。

官方背景引用/标注/替代证据限制沿用父实验，不改gold，不计算回答正确率。仅原25题有必要证据标注。LoCoMo200题来自10份历史，不能当200份独立历史。

## 文件与复现

- `authored-inputs.tsv`：257对独立输入。
- `runtime.json`、`input-review.json`、`named-anchor-audit.json`：原问题/时钟/候选范围与运行前审核。
- `protocol.json`：冻结文件与SHA256；`evaluation.json`只供评分。
- `queries.npy`和`encoding.json`：全部新查询向量与模型/耗时记录。
- `old-documents.npy`：原25题既有向量的导出；另两组复用父实验文档向量。
- `rankings/`：每题首次完整单路排名；`results.json`和`summary.csv`：逐题评分与汇总。
- `case-audit.json`：改善/回退案例的原句、坐标与来源hash。

在仓库根目录，用已装NumPy的Python执行：

```sh
python -B experiments/smm-query-input-001/lab.py verify
```

重放只读取封存原文/向量/查询/排名，不需要生成模型API，不重新编码。首次查询编码还需要父实验固定MiniLM资产；未把本机模型权重复制进研究仓库。

本实验相关上游许可见 [METHOD.md](METHOD.md)，尤其LoCoMo派生材料沿用CC BY-NC 4.0。
