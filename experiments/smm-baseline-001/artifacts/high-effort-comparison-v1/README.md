# SMM-B001：五模型 Low / High 固定对照

冻结25题×3任务，每模型75个high首次逻辑调用，共375。重用相同完整原文、候选、问题、时钟、schema和评分；无新检索、编码、压缩或模型裁判。只改每个模型对应接口的low→high；旧结果不覆盖。

## 冻结主分（Low → High）

P22/P25时间适用歧义单列，回答主分母23；筛选主分母25，以必要信息齐全且无确认无关误选为准。格式/生成失败不能通过主分；status=partial本身不决定对错。

| 模型 | 准确上下文回答 /23 | 混合Top5筛选 /25 | 混合Top5回答 /23 |
| --- | ---: | ---: | ---: |
| gpt-6-luna | 21 → 23 | 22 → 25 | 19 → 23 |
| gpt-6.1-sol | 23 → 23 | 25 → 25 | 23 → 23 |
| glm-5.3-flash | 23 → 23 | 25 → 25 | 21 → 21 |
| glm-5.3 | 20 → 23 | 24 → 25 | 21 → 21 |
| deepseek-flash | 23 → 23 | 25 → 25 | 22 → 23 |

## High 执行完整性

| 模型 | 首次逻辑调用 | 返回输出 | 无输出失败 |
| --- | ---: | ---: | ---: |
| gpt-6-luna | 75 | 75 | 0 |
| gpt-6.1-sol | 75 | 75 | 0 |
| glm-5.3-flash | 75 | 74 | 1 |
| glm-5.3 | 75 | 74 | 1 |
| deepseek-flash | 75 | 75 | 0 |

每对任务仅一个首次应用层调用；失败保留，不补跑取更优分数。HTTP读取超时按预先冻结协议只继续后续未尝试任务。

## 正文正确与格式/生成失败分开

| 模型 | 准确上下文正文 /23（Low→High） | 混合候选正文 /23（Low→High） |
| --- | ---: | ---: |
| gpt-6-luna | 21 → 23 | 19 → 23 |
| gpt-6.1-sol | 23 → 23 | 23 → 23 |
| glm-5.3-flash | 23 → 23 | 21 → 21 |
| glm-5.3 | 22 → 23 | 23 → 22 |
| deepseek-flash | 23 → 23 | 23 → 23 |

正文表仅诊断，不修补首输出或替代冻结主分。分母仍含23道明确题，无输出不会记正文正确；不将无输出称为事实答错。逐字引文、所有附加主张支持、必要核心依据支持另见diagnostics.json和reviews。输出引用的ID正确不代表引文支持答案。

## 返回耗时中位数（秒，Low → High）

| 模型 | 准确上下文回答 | 筛选 | 混合候选回答 |
| --- | ---: | ---: | ---: |
| gpt-6-luna | 4.62 → 6.36 | 4.30 → 5.13 | 5.21 → 6.95 |
| gpt-6.1-sol | 6.10 → 11.66 | 5.52 → 6.93 | 7.09 → 12.89 |
| glm-5.3-flash | 6.82 → 18.77 | 4.20 → 13.94 | 8.54 → 23.02 |
| glm-5.3 | 7.00 → 19.06 | 4.43 → 12.55 | 7.57 → 23.27 |
| deepseek-flash | 4.68 → 5.57 | 3.86 → 4.20 | 5.90 → 7.11 |

成功返回的首输出均计入耗时，即使格式或正文错误；无输出失败单列timing.json，不把超时当0秒或混成事实答错。此为服务函数观测，非APP端到端、非独立P95估计。

## 逐题主分变化

- gpt-6-luna：oracle_answer 改善[P06,P08]，退步[]；candidate_select 改善[P06,P09,P25]，退步[]；candidate_answer 改善[P06,P07,P08,P09]，退步[]
- gpt-6.1-sol：oracle_answer 改善[]，退步[]；candidate_select 改善[]，退步[]；candidate_answer 改善[]，退步[]
- glm-5.3-flash：oracle_answer 改善[]，退步[]；candidate_select 改善[]，退步[]；candidate_answer 改善[P21]，退步[P20]
- glm-5.3：oracle_answer 改善[P01,P03,P06]，退步[]；candidate_select 改善[P25]，退步[]；candidate_answer 改善[P15,P20]，退步[P06,P18]
- deepseek-flash：oracle_answer 改善[]，退步[]；candidate_select 改善[]，退步[]；candidate_answer 改善[P02]，退步[]

## 这轮变化具体来自哪里

- **Luna收益最明确。** 准确上下文修复P06四天健身和P08三种柑橘的完整作答；混合候选又补齐P07三场晚宴、P09三个December日期。筛选补齐P06周三瑜伽、P09必要来源和P25较新7AM。三主分均满，但oracle P22/P24仍把真实时间metadata当正文quote，逐字引证不全通过；P22歧义题不计23分母，P24计入引用诊断。混合回答中位5.21→6.95秒。
- **Sol没有新增通过题。** Low与High三主分均23/23、25/25、23/23；逐字引用/明确题严格支持均通过。混合回答中位7.09→12.89秒。本轮没有观察到升档带来的新增任务收益，不能推其他更难任务也无收益。
- **DeepSeek新增主分来自格式通过。** Low P02混合回答正文20打正确，但多type字段；High没有此格式失败，两档明确题正文均全部正确。Low oracle P24 metadata引用问题这次消失，High却在mixed P23把两个真实metadata时间串当正文quote，未全面解决引用约定。混合回答中位5.90→7.11秒。P25 oracle本次给6:45、mixed保留适用不确定，均看到7AM和15分钟两事实，不能用该歧义题挑选更高分模型。
- **GLM Flash有一题语义改善，主分被超时抵消。** Mixed P21现在按毕业时间正确排Emma→Rachel→Alex，Low曾误作毕业名次；P07仍不完整：Low漏Mike，High改为错误排除Sarah，原文用户明确speaking of dinner parties连接Sarah。新P20 mixed读取超时，无输出，不是事实答案错误。故mixed仍21/23（High生成明确题正文21/22正确，另1超时）。中位8.54→23.02秒，超时单列。High还存在逐字改引号、metadata作正文quote、P12只引用无剧名的引导语，以及P24多引无关正文等支持缺陷。
- **GLM主模型增分主要是格式/可用性，不是已证实的理解提升。** Oracle P01/P03 Low正文原已正确但来源ID重复，High主分通过却引文仍有复制错误；P06 Low超时、本次返回四天。筛选P25补齐新7AM，24→25。Mixed旧P15/P20重复ID消失，新P06反复输出100个来源ID、P18读取超时，得分仍21/23。High所有返回的明确题正文均正确（oracle23/23、mixed22/22；另mixed1超时），但P07/P23缺关键引证；missing字段还出现控制/自我修复片段。中位7.57→23.27秒。

所有High选择均覆盖必要要点36/36，观察无关误选0；Luna选39、Sol42、DeepSeek42、两GLM各43个基准来源段次。与Low的数量相同不代表找到了相同信息：Luna Low选39但只覆盖33必要要点，High39覆盖36。43个参考来源含可省冗余，不能把没选齐全部43判必要漏检；无关所选/所选段次也不是全库FPR。

本轮支持的选择是：**不统一把所有模型提升High。** Luna升High观察到明确收益；Sol/DeepSeek没有新增正文正确题，GLM的耗时增加显著且仍有语义/格式/引用或可用性缺陷。此为固定已知样本的一次配对观察，不是泛化保证、因果证明或默认模型变更。

## 过程记录

共375首次逻辑调用、373生成输出、2读取超时，无应用层重试、重抽或追加探测。248实际生成答案（两种回答任务共250，减2超时）逐一审阅，125筛选输出按冻结必要信息规则复核；没有模型裁判。旧Low正式运行亦各有1个GLM超时，但题目/任务不同，不以补跑替代失败。

第一次独立核验脚本曾错误要求Codex每条metrics包含transport_profile，原封装实际仅在run元数据存此字段。只修正离线检查以检查run.profile与冻结源码、实际provider/model绑定，原请求、推理输出和评分未改、未产生新模型调用；随后21388完整性检查通过。此为核验程序错误，不计入模型失败。


## 比较边界与复现

每题每档一次，本轮与旧low不是同一时间随机交错重复；运行调度与缓存不同，供应商模型别名亦可能更新。逐题变化是观察结果，不能把全部差异归因思考档位，不能由25道已知英文正例推通用排名。没有自然无答案或企业文档泛化验证。

保留各自low接口：GPT走原Codex订阅封装，GLM走原Coding Chat/native json_schema，DeepSeek走原json_object加相同schema格式附录（其原生json_schema不可用）。只改各自effort，不把不同供应商high当成相同计算预算。GPT原transport原样保留，其底层网络行为由Codex运行时管理；本测试无应用层重试/语义重抽，不把逻辑函数调用数冒充可观测全部底层HTTP请求数。

75个HTTP DeepSeek high实际wire hashes、原输入hash、代码hash在推理前冻结；375任务的首次记录、启动标记、错误/用量、实际生成答案语义复核与旧low原结果全部可追溯。凭证和隐藏思考正文不保存。研究助手逐题复核，非外部独立人类盲评；没有使用额外模型裁判。

在实验根目录使用Python>=3.11；以下离线命令不调用模型：

```bash
python3 -B artifacts/high-effort-comparison-v1/verify_high.py
python3 -B bench.py score --run gpt-6-luna-high-first
python3 -B bench.py report --runs gpt-6-luna,gpt-6-luna-high-first,gpt-6.1-sol,gpt-6.1-sol-high-first,glm-5.3-flash-low-first,glm-5.3-flash-high-first,glm-5.3-low-first,glm-5.3-high-first,deepseek-flash-low-first,deepseek-flash-high-first --out artifacts/new-low-high-report.html
```

新模型或新档位需新protocol/run-id，不覆盖旧首结果。未修改SMM生产默认。
