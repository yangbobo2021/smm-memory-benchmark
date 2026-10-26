"""Render complete fixed-criterion results and links to every execution trace."""
import csv
import io
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def rate(a,b):return f'{a}/{b} ({a/b:.1%})'if b else'—（无样本）'


def artifacts():
    d=json.loads((HERE/'results.json').read_text());assert not d['pending']
    lines=['# SMM-SF-LUNA001：GPT-6-Luna high 的充分性判断与一次补查','',
           '原始问题 → 原BM25 Top5完整对话 → Agent判断 → 若缺失则生成一个新查询 → 排除原5段后取新Top5 → 对最多10段完整对话再判断。','',
           '**不使用向量、重排或第三轮补查。所有首输出、失败与补查排名均保留。** 模型固定GPT-6-Luna、high；提示未因结果调整。','',
           '## 信息齐全时能否停、缺失时能否继续','',
           '主表使用运行前审核的回答依赖口径。模型判断比例只用有有效返回的判断作分母，服务/格式错误另列。任务口径的全部分母也在summary.csv中保留。','',
           '| 数据组 | 明确依赖齐全题 | 判断充分 / 有效返回 | 明确依赖缺失题 | 判断缺失 / 有效返回 | 初次调用错误 | 歧义单列 |',
           '|---|---:|---:|---:|---:|---:|---:|']
    semantic=[x for x in d['summaries']if x['view']=='dependency']
    for s in semantic:
        lines.append(f"| {s['cohort']} | {s['complete_initial']} | {rate(s['complete_judged_sufficient'],s['complete_initial']-s['complete_call_errors'])} | {s['incomplete_initial']} | {rate(s['incomplete_judged_insufficient'],s['incomplete_initial']-s['incomplete_call_errors'])} | {s['complete_call_errors']+s['incomplete_call_errors']} | {s['ambiguous_separate']} |")
    lines+=['','不要用一个总体准确率掩盖缺失识别：总判充分的策略在齐全题上100%，但在缺失题上0%。原25题没有自然缺失的明确样本，不能据此估计它的缺失识别率。','',
            '## 认为缺失后，新查询是否有效','',
            '| 数据组 | 真缺失且发起补查 | 补到至少一项缺失 / 补查题 | 补齐全部 / 补查题 | 所有初始缺失题最终补齐 | 补齐且随后判断充分 |',
            '|---|---:|---:|---:|---:|---:|']
    for s in semantic:
        lines.append(f"| {s['cohort']} | {s['necessary_searches']} | {rate(s['needed_search_adds_any_missing_unit'],s['necessary_searches'])} | {rate(s['needed_search_completes_all'],s['necessary_searches'])} | {rate(s['all_initial_incomplete_recovered'],s['incomplete_initial'])} | {s['recovered_and_stopped']} |")
    lines+=['','“补查题成功率”和“所有缺失题最终恢复率”的分母不同。Agent过早认为充分、没有发起补查的题，仍在后一列的分母里。','',
            '## 新信息到齐后是否能停止','',
            '| 数据组 | 补查后齐全：判断充分 | 补查后仍缺：判断缺失 | 初始齐全却判断缺失 | 最终过早停止 |',
            '|---|---:|---:|---:|---:|']
    for s in semantic:
        lines.append(f"| {s['cohort']} | {rate(s['after_search_complete_judged_sufficient'],s['after_search_complete'])} | {rate(s['after_search_incomplete_judged_insufficient'],s['after_search_incomplete'])} | {s['complete_judged_insufficient']} | {s['incorrect_final_stops']} |")
    lines+=['','## 不改标签的官方参考口径（完整257题）','',
            '此表仅为对照。缺背景或重复支持不一定等于缺少答案；参考来源取齐不是回答正确率。','',
            '| 数据组 | 原Top5参考取齐 | 取齐时判断充分 / 有效返回 | 未取齐时判断缺失 / 有效返回 | 补查后的参考取齐 |',
            '|---|---:|---:|---:|---:|']
    for s in [x for x in d['summaries']if x['view']=='official']:
        lines.append(f"| {s['cohort']} | {s['complete_initial']}/{s['cases']} | {rate(s['complete_judged_sufficient'],s['complete_initial']-s['complete_call_errors'])} | {rate(s['incomplete_judged_insufficient'],s['incomplete_initial']-s['incomplete_call_errors'])} | {s['final_dependency_coverage']}/{s['cases']} |")
    lines+=['','## 用量、失败与可复现记录','',
            f"- 逻辑尝试：{d['calls']['logical_attempts']}；首轮{d['calls']['round1']}、第二轮{d['calls']['round2']}。",
            f"- 调用/契约错误：{d['calls']['errors']}；返回中原文字面引用校验失败：{d['calls']['literal_quote_failures']}。",
            '- 新调用不设固定间隔；429首次尝试另存，等待30秒重试同一输入一次。试跑复用的4题曾有45秒间隔，保留其原始耗时与来源。服务错误及重试尝试单独统计。',
            '- 底层Codex内部网络重试不可观测，不把逻辑调用数称为全部HTTP请求数。隐藏思考正文不采集，保存的是模型可见输入、指定JSON输出、用量和错误。','',
            '| 题号 | 首轮判断 | 新查询 | 新增段数 | 二次判断 | 依赖：初始→补查后 |','|---|---|---|---:|---|---|']
    for c in d['cases']:
        a=c['views']['dependency'];state='歧义单列'if not c['semantic_evaluable']else f"{a['initial']['complete']} → {a['after']['complete']}"
        query=(c['next_query']or'').replace('|','\\|').replace('\n',' ')
        lines.append(f"| [{c['id']}](requests/round1/{c['id']}.json) | [{c['first_decision']}](records/round1/{c['id']}.json) | {query} | {len(c['added_sources'])} | {c['second_decision']or'—'} | {state} |")
    lines+=['','## 限制','',
            '这批问题此前已用过。依赖审核由研究作者完成，不是外部独立金标；25道不适合明确文本充分性二分的题预先单列，所有257题和未改官方口径仍保留。','',
            '有限候选中没有线索的隐藏事件，Agent不能凭空知道存在。标注依赖都出现，并不等于输入本身提供了“没有其他事件”的证明。计数/列表题的继续搜索可能包含合理谨慎；需结合原输出和具体缺口复核，不能把条件比例推广为一般性知识完备判断。','',
            '本实验不报告最终回答正确率。输出中的短回答用于检查判断依据，尚不等于逐题答案验收。字面引用合法也不证明语义支持正确。','',
            '输入/输出/查询/排名分别见requests、records、followups；标签只在evaluation.json和dependency_annotations.py。正文与模型不见的来源ID映射在runtime.json；模型仅见D1–D10。协议与原脚本hash见protocol.json。','',
            '离线重放：`python -B experiments/smm-sufficiency-001/score.py --verify --check`。无需模型API或文档向量；依赖父实验已公开的原文。上游原文与派生数据许可沿用父实验，LoCoMo为CC BY-NC 4.0。','']
    stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=list(d['summaries'][0]));w.writeheader();w.writerows(d['summaries'])
    return {'README.md':'\n'.join(lines),'summary.csv':stream.getvalue()}


if __name__=='__main__':
    for name,text in artifacts().items():
        with(HERE/name).open('x',newline='')as f:f.write(text)
