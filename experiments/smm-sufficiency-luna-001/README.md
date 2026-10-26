# SMM-SF-LUNA001：GPT-6-Luna high 的充分性判断与一次补查

原始问题 → 原BM25 Top5完整对话 → Agent判断 → 若缺失则生成一个新查询 → 排除原5段后取新Top5 → 对最多10段完整对话再判断。

**不使用向量、重排或第三轮补查。所有首输出、失败与补查排名均保留。** 模型固定GPT-6-Luna、high；提示未因结果调整。

## 信息齐全时能否停、缺失时能否继续

主表使用运行前审核的回答依赖口径。模型判断比例只用有有效返回的判断作分母，服务/格式错误另列。任务口径的全部分母也在summary.csv中保留。

| 数据组 | 明确依赖齐全题 | 判断充分 / 有效返回 | 明确依赖缺失题 | 判断缺失 / 有效返回 | 初次调用错误 | 歧义单列 |
|---|---:|---:|---:|---:|---:|---:|
| original25 | 23 | 20/22 (90.9%) | 0 | —（无样本） | 1 | 2 |
| longmemeval_new32 | 25 | 21/25 (84.0%) | 6 | 5/6 (83.3%) | 0 | 1 |
| locomo_random200 | 151 | 135/150 (90.0%) | 27 | 18/27 (66.7%) | 1 | 22 |

不要用一个总体准确率掩盖缺失识别：总判充分的策略在齐全题上100%，但在缺失题上0%。原25题没有自然缺失的明确样本，不能据此估计它的缺失识别率。

## 认为缺失后，新查询是否有效

| 数据组 | 真缺失且发起补查 | 补到至少一项缺失 / 补查题 | 补齐全部 / 补查题 | 所有初始缺失题最终补齐 | 补齐且随后判断充分 |
|---|---:|---:|---:|---:|---:|
| original25 | 0 | —（无样本） | —（无样本） | —（无样本） | 0 |
| longmemeval_new32 | 5 | 5/5 (100.0%) | 5/5 (100.0%) | 5/6 (83.3%) | 2 |
| locomo_random200 | 18 | 12/18 (66.7%) | 9/18 (50.0%) | 9/27 (33.3%) | 6 |

“补查题成功率”和“所有缺失题最终恢复率”的分母不同。Agent过早认为充分、没有发起补查的题，仍在后一列的分母里。

## 新信息到齐后是否能停止

| 数据组 | 补查后齐全：判断充分 | 补查后仍缺：判断缺失 | 初始齐全却判断缺失 | 最终过早停止 |
|---|---:|---:|---:|---:|
| original25 | 0/2 (0.0%) | —（无样本） | 2 | 0 |
| longmemeval_new32 | 2/9 (22.2%) | —（无样本） | 4 | 1 |
| locomo_random200 | 6/24 (25.0%) | 5/9 (55.6%) | 15 | 13 |

## 不改标签的官方参考口径（完整257题）

此表仅为对照。缺背景或重复支持不一定等于缺少答案；参考来源取齐不是回答正确率。

| 数据组 | 原Top5参考取齐 | 取齐时判断充分 / 有效返回 | 未取齐时判断缺失 / 有效返回 | 补查后的参考取齐 |
|---|---:|---:|---:|---:|
| original25 | 25/25 | 22/24 (91.7%) | —（无样本） | 25/25 |
| longmemeval_new32 | 20/32 | 17/20 (85.0%) | 7/12 (58.3%) | 27/32 |
| locomo_random200 | 156/200 | 135/155 (87.1%) | 28/44 (63.6%) | 166/200 |

## 用量、失败与可复现记录

- 逻辑尝试：317；首轮257、第二轮60。
- 调用/契约错误：2；返回中原文字面引用校验失败：5。
- 新调用不设固定间隔；429首次尝试另存，等待30秒重试同一输入一次。试跑复用的4题曾有45秒间隔，保留其原始耗时与来源。服务错误及重试尝试单独统计。
- 底层Codex内部网络重试不可观测，不把逻辑调用数称为全部HTTP请求数。隐藏思考正文不采集，保存的是模型可见输入、指定JSON输出、用量和错误。

| 题号 | 首轮判断 | 新查询 | 新增段数 | 二次判断 | 依赖：初始→补查后 |
|---|---|---|---:|---|---|
| [P01](requests/round1/P01.json) | [sufficient](records/round1/P01.json) |  | 0 | — | True → True |
| [P02](requests/round1/P02.json) | [sufficient](records/round1/P02.json) |  | 0 | — | True → True |
| [P03](requests/round1/P03.json) | [sufficient](records/round1/P03.json) |  | 0 | — | True → True |
| [P04](requests/round1/P04.json) | [sufficient](records/round1/P04.json) |  | 0 | — | True → True |
| [P05](requests/round1/P05.json) | [sufficient](records/round1/P05.json) |  | 0 | — | True → True |
| [P06](requests/round1/P06.json) | [sufficient](records/round1/P06.json) |  | 0 | — | True → True |
| [P07](requests/round1/P07.json) | [insufficient](records/round1/P07.json) | dinner party attended last month dinner parties feast potluck BBQ Sarah Alex Mike | 5 | insufficient | True → True |
| [P08](requests/round1/P08.json) | [insufficient](records/round1/P08.json) | cocktail recipes made used lime orange lemon grapefruit citrus Cucumber Gimlet Sangria | 5 | insufficient | True → True |
| [P09](requests/round1/P09.json) | [sufficient](records/round1/P09.json) |  | 0 | — | True → True |
| [P10](requests/round1/P10.json) | [sufficient](records/round1/P10.json) |  | 0 | — | True → True |
| [P11](requests/round1/P11.json) | [sufficient](records/round1/P11.json) |  | 0 | — | True → True |
| [P12](requests/round1/P12.json) | [sufficient](records/round1/P12.json) |  | 0 | — | True → True |
| [P13](requests/round1/P13.json) | [sufficient](records/round1/P13.json) |  | 0 | — | True → True |
| [P14](requests/round1/P14.json) | [sufficient](records/round1/P14.json) |  | 0 | — | True → True |
| [P15](requests/round1/P15.json) | [sufficient](records/round1/P15.json) |  | 0 | — | True → True |
| [P16](requests/round1/P16.json) | [sufficient](records/round1/P16.json) |  | 0 | — | True → True |
| [P17](requests/round1/P17.json) | [sufficient](records/round1/P17.json) |  | 0 | — | True → True |
| [P18](requests/round1/P18.json) | [sufficient](records/round1/P18.json) |  | 0 | — | True → True |
| [P19](requests/round1/P19.json) | [sufficient](records/round1/P19.json) |  | 0 | — | True → True |
| [P20](requests/round1/P20.json) | [sufficient](records/round1/P20.json) |  | 0 | — | True → True |
| [P21](requests/round1/P21.json) | [error](records/round1/P21.json) |  | 0 | — | True → True |
| [P22](requests/round1/P22.json) | [sufficient](records/round1/P22.json) |  | 0 | — | 歧义单列 |
| [P23](requests/round1/P23.json) | [sufficient](records/round1/P23.json) |  | 0 | — | True → True |
| [P24](requests/round1/P24.json) | [sufficient](records/round1/P24.json) |  | 0 | — | True → True |
| [P25](requests/round1/P25.json) | [sufficient](records/round1/P25.json) |  | 0 | — | 歧义单列 |
| [L001](requests/round1/L001.json) | [sufficient](records/round1/L001.json) |  | 0 | — | True → True |
| [L002](requests/round1/L002.json) | [sufficient](records/round1/L002.json) |  | 0 | — | True → True |
| [L003](requests/round1/L003.json) | [sufficient](records/round1/L003.json) |  | 0 | — | True → True |
| [L004](requests/round1/L004.json) | [sufficient](records/round1/L004.json) |  | 0 | — | True → True |
| [L005](requests/round1/L005.json) | [insufficient](records/round1/L005.json) | airline flight flew traveled trip United American Delta Boston Atlanta New York Los Angeles | 5 | insufficient | False → True |
| [L006](requests/round1/L006.json) | [sufficient](records/round1/L006.json) |  | 0 | — | True → True |
| [L007](requests/round1/L007.json) | [sufficient](records/round1/L007.json) |  | 0 | — | True → True |
| [L008](requests/round1/L008.json) | [insufficient](records/round1/L008.json) | cucumbers cucumber plants initially planted started planted seedlings garden | 5 | insufficient | True → True |
| [L009](requests/round1/L009.json) | [insufficient](records/round1/L009.json) | Rachel wedding married next year age birthday date of birth | 5 | insufficient | 歧义单列 |
| [L010](requests/round1/L010.json) | [sufficient](records/round1/L010.json) |  | 0 | — | True → True |
| [L011](requests/round1/L011.json) | [insufficient](records/round1/L011.json) | baked baking cookies cake bread oven recipe | 5 | insufficient | False → True |
| [L012](requests/round1/L012.json) | [insufficient](records/round1/L012.json) | Queen Adam Lambert Prudential Center Newark live concert date Brooklyn music festival Billie Eilish Philly show jazz night outdoor concert | 5 | insufficient | False → True |
| [L013](requests/round1/L013.json) | [sufficient](records/round1/L013.json) |  | 0 | — | True → True |
| [L014](requests/round1/L014.json) | [insufficient](records/round1/L014.json) | museum friend visit Science Museum chemistry professor behind-the-scenes tour | 5 | insufficient | True → True |
| [L015](requests/round1/L015.json) | [sufficient](records/round1/L015.json) |  | 0 | — | True → True |
| [L016](requests/round1/L016.json) | [insufficient](records/round1/L016.json) | bike fixed repaired serviced maintenance weekend mountain road bike pedals | 3 | insufficient | True → True |
| [L017](requests/round1/L017.json) | [sufficient](records/round1/L017.json) |  | 0 | — | True → True |
| [L018](requests/round1/L018.json) | [insufficient](records/round1/L018.json) | business milestone company business achievement launch startup revenue | 5 | sufficient | False → True |
| [L019](requests/round1/L019.json) | [sufficient](records/round1/L019.json) |  | 0 | — | True → True |
| [L020](requests/round1/L020.json) | [sufficient](records/round1/L020.json) |  | 0 | — | True → True |
| [L021](requests/round1/L021.json) | [sufficient](records/round1/L021.json) |  | 0 | — | True → True |
| [L022](requests/round1/L022.json) | [insufficient](records/round1/L022.json) | local art competition sculpture investment bought purchase found objects recycled materials | 5 | sufficient | False → True |
| [L023](requests/round1/L023.json) | [sufficient](records/round1/L023.json) |  | 0 | — | True → True |
| [L024](requests/round1/L024.json) | [sufficient](records/round1/L024.json) |  | 0 | — | True → True |
| [L025](requests/round1/L025.json) | [sufficient](records/round1/L025.json) |  | 0 | — | True → True |
| [L026](requests/round1/L026.json) | [sufficient](records/round1/L026.json) |  | 0 | — | True → True |
| [L027](requests/round1/L027.json) | [sufficient](records/round1/L027.json) |  | 0 | — | True → True |
| [L028](requests/round1/L028.json) | [sufficient](records/round1/L028.json) |  | 0 | — | True → True |
| [L029](requests/round1/L029.json) | [sufficient](records/round1/L029.json) |  | 0 | — | True → True |
| [L030](requests/round1/L030.json) | [sufficient](records/round1/L030.json) |  | 0 | — | False → False |
| [L031](requests/round1/L031.json) | [insufficient](records/round1/L031.json) | February visited museum gallery art museum Natural History Museum Art Cube opening night 2/15 2/8 | 5 | insufficient | True → True |
| [L032](requests/round1/L032.json) | [sufficient](records/round1/L032.json) |  | 0 | — | True → True |
| [C001](requests/round1/C001.json) | [insufficient](records/round1/C001.json) | Deborah married wedding beach surfing | 5 | insufficient | True → True |
| [C002](requests/round1/C002.json) | [sufficient](records/round1/C002.json) |  | 0 | — | True → True |
| [C003](requests/round1/C003.json) | [sufficient](records/round1/C003.json) |  | 0 | — | True → True |
| [C004](requests/round1/C004.json) | [sufficient](records/round1/C004.json) |  | 0 | — | True → True |
| [C005](requests/round1/C005.json) | [sufficient](records/round1/C005.json) |  | 0 | — | True → True |
| [C006](requests/round1/C006.json) | [sufficient](records/round1/C006.json) |  | 0 | — | True → True |
| [C007](requests/round1/C007.json) | [sufficient](records/round1/C007.json) |  | 0 | — | True → True |
| [C008](requests/round1/C008.json) | [sufficient](records/round1/C008.json) |  | 0 | — | True → True |
| [C009](requests/round1/C009.json) | [sufficient](records/round1/C009.json) |  | 0 | — | True → True |
| [C010](requests/round1/C010.json) | [sufficient](records/round1/C010.json) |  | 0 | — | True → True |
| [C011](requests/round1/C011.json) | [sufficient](records/round1/C011.json) |  | 0 | — | True → True |
| [C012](requests/round1/C012.json) | [sufficient](records/round1/C012.json) |  | 0 | — | True → True |
| [C013](requests/round1/C013.json) | [sufficient](records/round1/C013.json) |  | 0 | — | True → True |
| [C014](requests/round1/C014.json) | [sufficient](records/round1/C014.json) |  | 0 | — | 歧义单列 |
| [C015](requests/round1/C015.json) | [sufficient](records/round1/C015.json) |  | 0 | — | True → True |
| [C016](requests/round1/C016.json) | [sufficient](records/round1/C016.json) |  | 0 | — | True → True |
| [C017](requests/round1/C017.json) | [sufficient](records/round1/C017.json) |  | 0 | — | 歧义单列 |
| [C018](requests/round1/C018.json) | [sufficient](records/round1/C018.json) |  | 0 | — | True → True |
| [C019](requests/round1/C019.json) | [sufficient](records/round1/C019.json) |  | 0 | — | True → True |
| [C020](requests/round1/C020.json) | [sufficient](records/round1/C020.json) |  | 0 | — | True → True |
| [C021](requests/round1/C021.json) | [insufficient](records/round1/C021.json) | Joanna hiking hikes trails went hiking | 5 | insufficient | False → False |
| [C022](requests/round1/C022.json) | [sufficient](records/round1/C022.json) |  | 0 | — | True → True |
| [C023](requests/round1/C023.json) | [insufficient](records/round1/C023.json) | Jolene mom Nintendo Wii game system favorite game Wii console | 5 | insufficient | True → True |
| [C024](requests/round1/C024.json) | [sufficient](records/round1/C024.json) |  | 0 | — | False → False |
| [C025](requests/round1/C025.json) | [sufficient](records/round1/C025.json) |  | 0 | — | True → True |
| [C026](requests/round1/C026.json) | [sufficient](records/round1/C026.json) |  | 0 | — | 歧义单列 |
| [C027](requests/round1/C027.json) | [sufficient](records/round1/C027.json) |  | 0 | — | False → False |
| [C028](requests/round1/C028.json) | [sufficient](records/round1/C028.json) |  | 0 | — | False → False |
| [C029](requests/round1/C029.json) | [sufficient](records/round1/C029.json) |  | 0 | — | True → True |
| [C030](requests/round1/C030.json) | [sufficient](records/round1/C030.json) |  | 0 | — | True → True |
| [C031](requests/round1/C031.json) | [sufficient](records/round1/C031.json) |  | 0 | — | True → True |
| [C032](requests/round1/C032.json) | [sufficient](records/round1/C032.json) |  | 0 | — | True → True |
| [C033](requests/round1/C033.json) | [sufficient](records/round1/C033.json) |  | 0 | — | True → True |
| [C034](requests/round1/C034.json) | [sufficient](records/round1/C034.json) |  | 0 | — | True → True |
| [C035](requests/round1/C035.json) | [insufficient](records/round1/C035.json) | Maria vacation trip visited states travel destination | 5 | insufficient | False → True |
| [C036](requests/round1/C036.json) | [insufficient](records/round1/C036.json) | Deborah mother mom passed away died date | 5 | insufficient | True → True |
| [C037](requests/round1/C037.json) | [sufficient](records/round1/C037.json) |  | 0 | — | False → False |
| [C038](requests/round1/C038.json) | [sufficient](records/round1/C038.json) |  | 0 | — | True → True |
| [C039](requests/round1/C039.json) | [sufficient](records/round1/C039.json) |  | 0 | — | True → True |
| [C040](requests/round1/C040.json) | [insufficient](records/round1/C040.json) | Nate met new people convention tournament gamers | 5 | insufficient | True → True |
| [C041](requests/round1/C041.json) | [sufficient](records/round1/C041.json) |  | 0 | — | True → True |
| [C042](requests/round1/C042.json) | [sufficient](records/round1/C042.json) |  | 0 | — | True → True |
| [C043](requests/round1/C043.json) | [sufficient](records/round1/C043.json) |  | 0 | — | True → True |
| [C044](requests/round1/C044.json) | [sufficient](records/round1/C044.json) |  | 0 | — | 歧义单列 |
| [C045](requests/round1/C045.json) | [sufficient](records/round1/C045.json) |  | 0 | — | True → True |
| [C046](requests/round1/C046.json) | [sufficient](records/round1/C046.json) |  | 0 | — | True → True |
| [C047](requests/round1/C047.json) | [sufficient](records/round1/C047.json) |  | 0 | — | True → True |
| [C048](requests/round1/C048.json) | [sufficient](records/round1/C048.json) |  | 0 | — | True → True |
| [C049](requests/round1/C049.json) | [sufficient](records/round1/C049.json) |  | 0 | — | True → True |
| [C050](requests/round1/C050.json) | [insufficient](records/round1/C050.json) | Calvin friends park arranged gathering picnic walk | 5 | insufficient | True → True |
| [C051](requests/round1/C051.json) | [insufficient](records/round1/C051.json) | John Maria veterans support project volunteer shelter helped out participated | 5 | sufficient | False → False |
| [C052](requests/round1/C052.json) | [sufficient](records/round1/C052.json) |  | 0 | — | True → True |
| [C053](requests/round1/C053.json) | [insufficient](records/round1/C053.json) | Dave Calvin car modification mod workshop San Francisco duration how long days attended | 5 | insufficient | True → True |
| [C054](requests/round1/C054.json) | [sufficient](records/round1/C054.json) |  | 0 | — | True → True |
| [C055](requests/round1/C055.json) | [sufficient](records/round1/C055.json) |  | 0 | — | True → True |
| [C056](requests/round1/C056.json) | [insufficient](records/round1/C056.json) | Evan favorite food ginger snaps favorite meal food preference | 5 | insufficient | True → True |
| [C057](requests/round1/C057.json) | [sufficient](records/round1/C057.json) |  | 0 | — | True → True |
| [C058](requests/round1/C058.json) | [sufficient](records/round1/C058.json) |  | 0 | — | True → True |
| [C059](requests/round1/C059.json) | [insufficient](records/round1/C059.json) | Melanie camping planned next trip when family camping | 5 | sufficient | False → True |
| [C060](requests/round1/C060.json) | [sufficient](records/round1/C060.json) |  | 0 | — | True → True |
| [C061](requests/round1/C061.json) | [sufficient](records/round1/C061.json) |  | 0 | — | True → True |
| [C062](requests/round1/C062.json) | [sufficient](records/round1/C062.json) |  | 0 | — | True → True |
| [C063](requests/round1/C063.json) | [sufficient](records/round1/C063.json) |  | 0 | — | True → True |
| [C064](requests/round1/C064.json) | [error](records/round1/C064.json) |  | 0 | — | True → True |
| [C065](requests/round1/C065.json) | [sufficient](records/round1/C065.json) |  | 0 | — | True → True |
| [C066](requests/round1/C066.json) | [sufficient](records/round1/C066.json) |  | 0 | — | True → True |
| [C067](requests/round1/C067.json) | [insufficient](records/round1/C067.json) | Melanie roadtrip hike after the road trip yesterday went hiking | 5 | insufficient | True → True |
| [C068](requests/round1/C068.json) | [sufficient](records/round1/C068.json) |  | 0 | — | True → True |
| [C069](requests/round1/C069.json) | [sufficient](records/round1/C069.json) |  | 0 | — | True → True |
| [C070](requests/round1/C070.json) | [sufficient](records/round1/C070.json) |  | 0 | — | True → True |
| [C071](requests/round1/C071.json) | [sufficient](records/round1/C071.json) |  | 0 | — | True → True |
| [C072](requests/round1/C072.json) | [sufficient](records/round1/C072.json) |  | 0 | — | True → True |
| [C073](requests/round1/C073.json) | [sufficient](records/round1/C073.json) |  | 0 | — | False → False |
| [C074](requests/round1/C074.json) | [sufficient](records/round1/C074.json) |  | 0 | — | True → True |
| [C075](requests/round1/C075.json) | [sufficient](records/round1/C075.json) |  | 0 | — | True → True |
| [C076](requests/round1/C076.json) | [sufficient](records/round1/C076.json) |  | 0 | — | True → True |
| [C077](requests/round1/C077.json) | [sufficient](records/round1/C077.json) |  | 0 | — | True → True |
| [C078](requests/round1/C078.json) | [insufficient](records/round1/C078.json) | Joanna hiking found trail trails hometown more amazing | 5 | insufficient | True → True |
| [C079](requests/round1/C079.json) | [sufficient](records/round1/C079.json) |  | 0 | — | True → True |
| [C080](requests/round1/C080.json) | [sufficient](records/round1/C080.json) |  | 0 | — | True → True |
| [C081](requests/round1/C081.json) | [sufficient](records/round1/C081.json) |  | 0 | — | False → False |
| [C082](requests/round1/C082.json) | [sufficient](records/round1/C082.json) |  | 0 | — | True → True |
| [C083](requests/round1/C083.json) | [insufficient](records/round1/C083.json) | Dave car shop employees staff mechanics employ people | 5 | insufficient | 歧义单列 |
| [C084](requests/round1/C084.json) | [sufficient](records/round1/C084.json) |  | 0 | — | True → True |
| [C085](requests/round1/C085.json) | [sufficient](records/round1/C085.json) |  | 0 | — | True → True |
| [C086](requests/round1/C086.json) | [sufficient](records/round1/C086.json) |  | 0 | — | True → True |
| [C087](requests/round1/C087.json) | [sufficient](records/round1/C087.json) |  | 0 | — | True → True |
| [C088](requests/round1/C088.json) | [insufficient](records/round1/C088.json) | Jolene Deborah meeting September 8 reschedule rescheduled scheduling appointment | 5 | insufficient | 歧义单列 |
| [C089](requests/round1/C089.json) | [sufficient](records/round1/C089.json) |  | 0 | — | True → True |
| [C090](requests/round1/C090.json) | [sufficient](records/round1/C090.json) |  | 0 | — | True → True |
| [C091](requests/round1/C091.json) | [sufficient](records/round1/C091.json) |  | 0 | — | True → True |
| [C092](requests/round1/C092.json) | [insufficient](records/round1/C092.json) | Jolene partner boyfriend dating anniversary relationship start year | 5 | sufficient | False → True |
| [C093](requests/round1/C093.json) | [sufficient](records/round1/C093.json) |  | 0 | — | True → True |
| [C094](requests/round1/C094.json) | [insufficient](records/round1/C094.json) | Tim where location trip travel vacation November Europe castles | 5 | insufficient | False → False |
| [C095](requests/round1/C095.json) | [insufficient](records/round1/C095.json) | Evan health issues health scare hospital check-up doctors 2023 | 5 | insufficient | 歧义单列 |
| [C096](requests/round1/C096.json) | [sufficient](records/round1/C096.json) |  | 0 | — | True → True |
| [C097](requests/round1/C097.json) | [insufficient](records/round1/C097.json) | Melanie family activities kids beach camping museum park | 5 | insufficient | False → False |
| [C098](requests/round1/C098.json) | [sufficient](records/round1/C098.json) |  | 0 | — | True → True |
| [C099](requests/round1/C099.json) | [sufficient](records/round1/C099.json) |  | 0 | — | True → True |
| [C100](requests/round1/C100.json) | [sufficient](records/round1/C100.json) |  | 0 | — | True → True |
| [C101](requests/round1/C101.json) | [sufficient](records/round1/C101.json) |  | 0 | — | True → True |
| [C102](requests/round1/C102.json) | [sufficient](records/round1/C102.json) |  | 0 | — | True → True |
| [C103](requests/round1/C103.json) | [insufficient](records/round1/C103.json) | Jon dance competition performances judging event occurred hosted attended | 5 | insufficient | 歧义单列 |
| [C104](requests/round1/C104.json) | [sufficient](records/round1/C104.json) |  | 0 | — | True → True |
| [C105](requests/round1/C105.json) | [insufficient](records/round1/C105.json) | John James meet meetup get-together gaming night | 5 | sufficient | False → False |
| [C106](requests/round1/C106.json) | [sufficient](records/round1/C106.json) |  | 0 | — | True → True |
| [C107](requests/round1/C107.json) | [insufficient](records/round1/C107.json) | John endorsement renowned outdoor gear company hiking stuff outdoor gear photoshoot forest | 5 | insufficient | 歧义单列 |
| [C108](requests/round1/C108.json) | [sufficient](records/round1/C108.json) |  | 0 | — | True → True |
| [C109](requests/round1/C109.json) | [sufficient](records/round1/C109.json) |  | 0 | — | True → True |
| [C110](requests/round1/C110.json) | [sufficient](records/round1/C110.json) |  | 0 | — | True → True |
| [C111](requests/round1/C111.json) | [insufficient](records/round1/C111.json) | Nate Joanna stuffed animal dog Tilly gave gift present | 5 | sufficient | False → True |
| [C112](requests/round1/C112.json) | [sufficient](records/round1/C112.json) |  | 0 | — | True → True |
| [C113](requests/round1/C113.json) | [sufficient](records/round1/C113.json) |  | 0 | — | True → True |
| [C114](requests/round1/C114.json) | [sufficient](records/round1/C114.json) |  | 0 | — | True → True |
| [C115](requests/round1/C115.json) | [sufficient](records/round1/C115.json) |  | 0 | — | True → True |
| [C116](requests/round1/C116.json) | [insufficient](records/round1/C116.json) | James Samantha John baseball game next Sunday attended went | 5 | insufficient | 歧义单列 |
| [C117](requests/round1/C117.json) | [sufficient](records/round1/C117.json) |  | 0 | — | True → True |
| [C118](requests/round1/C118.json) | [insufficient](records/round1/C118.json) | Nate won tournament video game international high scores | 5 | insufficient | False → False |
| [C119](requests/round1/C119.json) | [insufficient](records/round1/C119.json) | Sam October 2023 travelling travel trip road state | 5 | insufficient | 歧义单列 |
| [C120](requests/round1/C120.json) | [insufficient](records/round1/C120.json) | Audrey dogs often dress up green hat clothes outfit costume | 5 | sufficient | False → True |
| [C121](requests/round1/C121.json) | [sufficient](records/round1/C121.json) |  | 0 | — | True → True |
| [C122](requests/round1/C122.json) | [sufficient](records/round1/C122.json) |  | 0 | — | True → True |
| [C123](requests/round1/C123.json) | [insufficient](records/round1/C123.json) | Evan painting bird flying bird artwork joy freedom | 5 | insufficient | True → True |
| [C124](requests/round1/C124.json) | [sufficient](records/round1/C124.json) |  | 0 | — | 歧义单列 |
| [C125](requests/round1/C125.json) | [insufficient](records/round1/C125.json) | James game Witcher 3 released first game Unity strategy Civilization Total War | 5 | insufficient | True → True |
| [C126](requests/round1/C126.json) | [sufficient](records/round1/C126.json) |  | 0 | — | True → True |
| [C127](requests/round1/C127.json) | [sufficient](records/round1/C127.json) |  | 0 | — | True → True |
| [C128](requests/round1/C128.json) | [sufficient](records/round1/C128.json) |  | 0 | — | True → True |
| [C129](requests/round1/C129.json) | [sufficient](records/round1/C129.json) |  | 0 | — | True → True |
| [C130](requests/round1/C130.json) | [insufficient](records/round1/C130.json) | John martial arts kickboxing karate judo classes practiced trained | 5 | sufficient | False → False |
| [C131](requests/round1/C131.json) | [sufficient](records/round1/C131.json) |  | 0 | — | True → True |
| [C132](requests/round1/C132.json) | [sufficient](records/round1/C132.json) |  | 0 | — | True → True |
| [C133](requests/round1/C133.json) | [sufficient](records/round1/C133.json) |  | 0 | — | True → True |
| [C134](requests/round1/C134.json) | [sufficient](records/round1/C134.json) |  | 0 | — | True → True |
| [C135](requests/round1/C135.json) | [insufficient](records/round1/C135.json) | Jolene partner meditation retreat September 2023 where spent retreat | 5 | insufficient | False → True |
| [C136](requests/round1/C136.json) | [sufficient](records/round1/C136.json) |  | 0 | — | True → True |
| [C137](requests/round1/C137.json) | [insufficient](records/round1/C137.json) | Melanie kids children youngest daughter family | 5 | insufficient | 歧义单列 |
| [C138](requests/round1/C138.json) | [insufficient](records/round1/C138.json) | John basketball games wins winning close game comeback intense season trophy | 5 | insufficient | 歧义单列 |
| [C139](requests/round1/C139.json) | [sufficient](records/round1/C139.json) |  | 0 | — | True → True |
| [C140](requests/round1/C140.json) | [sufficient](records/round1/C140.json) |  | 0 | — | True → True |
| [C141](requests/round1/C141.json) | [sufficient](records/round1/C141.json) |  | 0 | — | True → True |
| [C142](requests/round1/C142.json) | [insufficient](records/round1/C142.json) | Dave photography took up started October hobby | 5 | sufficient | False → True |
| [C143](requests/round1/C143.json) | [insufficient](records/round1/C143.json) | Calvin Tokyo first visit trip traveled earlier festival | 5 | insufficient | True → True |
| [C144](requests/round1/C144.json) | [sufficient](records/round1/C144.json) |  | 0 | — | True → True |
| [C145](requests/round1/C145.json) | [sufficient](records/round1/C145.json) |  | 0 | — | True → True |
| [C146](requests/round1/C146.json) | [sufficient](records/round1/C146.json) |  | 0 | — | True → True |
| [C147](requests/round1/C147.json) | [sufficient](records/round1/C147.json) |  | 0 | — | True → True |
| [C148](requests/round1/C148.json) | [sufficient](records/round1/C148.json) |  | 0 | — | True → True |
| [C149](requests/round1/C149.json) | [sufficient](records/round1/C149.json) |  | 0 | — | 歧义单列 |
| [C150](requests/round1/C150.json) | [sufficient](records/round1/C150.json) |  | 0 | — | True → True |
| [C151](requests/round1/C151.json) | [sufficient](records/round1/C151.json) |  | 0 | — | True → True |
| [C152](requests/round1/C152.json) | [sufficient](records/round1/C152.json) |  | 0 | — | True → True |
| [C153](requests/round1/C153.json) | [sufficient](records/round1/C153.json) |  | 0 | — | True → True |
| [C154](requests/round1/C154.json) | [insufficient](records/round1/C154.json) | Calvin cars first interested into cars childhood age passion | 5 | insufficient | 歧义单列 |
| [C155](requests/round1/C155.json) | [sufficient](records/round1/C155.json) |  | 0 | — | True → True |
| [C156](requests/round1/C156.json) | [sufficient](records/round1/C156.json) |  | 0 | — | True → True |
| [C157](requests/round1/C157.json) | [sufficient](records/round1/C157.json) |  | 0 | — | False → False |
| [C158](requests/round1/C158.json) | [sufficient](records/round1/C158.json) |  | 0 | — | True → True |
| [C159](requests/round1/C159.json) | [sufficient](records/round1/C159.json) |  | 0 | — | True → True |
| [C160](requests/round1/C160.json) | [sufficient](records/round1/C160.json) |  | 0 | — | True → True |
| [C161](requests/round1/C161.json) | [insufficient](records/round1/C161.json) | Maria aunt family struggling money financial help gave money | 5 | insufficient | True → True |
| [C162](requests/round1/C162.json) | [sufficient](records/round1/C162.json) |  | 0 | — | True → True |
| [C163](requests/round1/C163.json) | [insufficient](records/round1/C163.json) | Nate purple hair dyed hair color purple | 5 | insufficient | True → True |
| [C164](requests/round1/C164.json) | [sufficient](records/round1/C164.json) |  | 0 | — | True → True |
| [C165](requests/round1/C165.json) | [sufficient](records/round1/C165.json) |  | 0 | — | True → True |
| [C166](requests/round1/C166.json) | [sufficient](records/round1/C166.json) |  | 0 | — | True → True |
| [C167](requests/round1/C167.json) | [sufficient](records/round1/C167.json) |  | 0 | — | True → True |
| [C168](requests/round1/C168.json) | [sufficient](records/round1/C168.json) |  | 0 | — | False → False |
| [C169](requests/round1/C169.json) | [insufficient](records/round1/C169.json) | Evan Sam October shared painting landscape watercolor artwork | 5 | sufficient | False → True |
| [C170](requests/round1/C170.json) | [insufficient](records/round1/C170.json) | Nate turtles how many number pets | 5 | sufficient | False → False |
| [C171](requests/round1/C171.json) | [sufficient](records/round1/C171.json) |  | 0 | — | True → True |
| [C172](requests/round1/C172.json) | [insufficient](records/round1/C172.json) | James Canada trip planned days duration itinerary | 5 | insufficient | False → False |
| [C173](requests/round1/C173.json) | [sufficient](records/round1/C173.json) |  | 0 | — | True → True |
| [C174](requests/round1/C174.json) | [sufficient](records/round1/C174.json) |  | 0 | — | True → True |
| [C175](requests/round1/C175.json) | [sufficient](records/round1/C175.json) |  | 0 | — | True → True |
| [C176](requests/round1/C176.json) | [sufficient](records/round1/C176.json) |  | 0 | — | True → True |
| [C177](requests/round1/C177.json) | [insufficient](records/round1/C177.json) | Joanna Nate book recommendation fantasy series Little Women recommended books | 5 | insufficient | 歧义单列 |
| [C178](requests/round1/C178.json) | [sufficient](records/round1/C178.json) |  | 0 | — | True → True |
| [C179](requests/round1/C179.json) | [sufficient](records/round1/C179.json) |  | 0 | — | 歧义单列 |
| [C180](requests/round1/C180.json) | [sufficient](records/round1/C180.json) |  | 0 | — | True → True |
| [C181](requests/round1/C181.json) | [insufficient](records/round1/C181.json) | Sam weight health ailment diagnosis condition | 5 | insufficient | 歧义单列 |
| [C182](requests/round1/C182.json) | [sufficient](records/round1/C182.json) |  | 0 | — | True → True |
| [C183](requests/round1/C183.json) | [insufficient](records/round1/C183.json) | John ankle injured injury rehab physical therapy recovery | 5 | insufficient | False → True |
| [C184](requests/round1/C184.json) | [sufficient](records/round1/C184.json) |  | 0 | — | True → True |
| [C185](requests/round1/C185.json) | [insufficient](records/round1/C185.json) | Caroline Melanie transgender poetry reading posters slogan words | 5 | insufficient | 歧义单列 |
| [C186](requests/round1/C186.json) | [insufficient](records/round1/C186.json) | James Connecticut lives residence home apartment Stamford McGee's bar | 5 | insufficient | 歧义单列 |
| [C187](requests/round1/C187.json) | [sufficient](records/round1/C187.json) |  | 0 | — | False → False |
| [C188](requests/round1/C188.json) | [insufficient](records/round1/C188.json) | John moving abroad move overseas relocate another country international relocation willing open | 5 | insufficient | 歧义单列 |
| [C189](requests/round1/C189.json) | [sufficient](records/round1/C189.json) |  | 0 | — | True → True |
| [C190](requests/round1/C190.json) | [sufficient](records/round1/C190.json) |  | 0 | — | True → True |
| [C191](requests/round1/C191.json) | [sufficient](records/round1/C191.json) |  | 0 | — | True → True |
| [C192](requests/round1/C192.json) | [sufficient](records/round1/C192.json) |  | 0 | — | True → True |
| [C193](requests/round1/C193.json) | [sufficient](records/round1/C193.json) |  | 0 | — | True → True |
| [C194](requests/round1/C194.json) | [sufficient](records/round1/C194.json) |  | 0 | — | True → True |
| [C195](requests/round1/C195.json) | [sufficient](records/round1/C195.json) |  | 0 | — | True → True |
| [C196](requests/round1/C196.json) | [sufficient](records/round1/C196.json) |  | 0 | — | True → True |
| [C197](requests/round1/C197.json) | [sufficient](records/round1/C197.json) |  | 0 | — | True → True |
| [C198](requests/round1/C198.json) | [sufficient](records/round1/C198.json) |  | 0 | — | True → True |
| [C199](requests/round1/C199.json) | [sufficient](records/round1/C199.json) |  | 0 | — | True → True |
| [C200](requests/round1/C200.json) | [insufficient](records/round1/C200.json) | John charity teaming up local organization disadvantaged kids sports school charity work | 5 | insufficient | True → True |

## 限制

这批问题此前已用过。依赖审核由研究作者完成，不是外部独立金标；25道不适合明确文本充分性二分的题预先单列，所有257题和未改官方口径仍保留。

有限候选中没有线索的隐藏事件，Agent不能凭空知道存在。标注依赖都出现，并不等于输入本身提供了“没有其他事件”的证明。计数/列表题的继续搜索可能包含合理谨慎；需结合原输出和具体缺口复核，不能把条件比例推广为一般性知识完备判断。

本实验不报告最终回答正确率。输出中的短回答用于检查判断依据，尚不等于逐题答案验收。字面引用合法也不证明语义支持正确。

输入/输出/查询/排名分别见requests、records、followups；标签只在evaluation.json和dependency_annotations.py。正文与模型不见的来源ID映射在runtime.json；模型仅见D1–D10。协议与原脚本hash见protocol.json。

离线重放：`python -B experiments/smm-sufficiency-001/score.py --verify --check`。无需模型API或文档向量；依赖父实验已公开的原文。上游原文与派生数据许可沿用父实验，LoCoMo为CC BY-NC 4.0。
