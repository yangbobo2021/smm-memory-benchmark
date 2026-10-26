"""Render the fixed-cohort comparison after extraction and scoring complete."""
import collections
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def read(p):return json.loads(Path(p).read_text())
def s(x):return f"{x['all']}/{x['cases']}"

def main():
    summary=read(HERE/'summary.json');audit=read(HERE/'audit.json')
    outcome=read(HERE/'case-outcomes.json');unions=read(HERE/'union-outcomes.json')
    rows={(x['route'],x['n']):x for x in summary['rows']}
    cases=collections.defaultdict(dict)
    for x in outcome:cases[(x['id'],x['n'])][x['route']]=x
    diffs=[]
    for name,new,old in [('branch_bm25_vs_normalized_whole','branch_bm25','whole_bm25_normalized'),
                         ('branch_bm25_vs_historical_raw','branch_bm25','whole_bm25_raw'),
                         ('branch_vector_vs_normalized_whole','branch_vector','whole_vector_normalized')]:
        for n in [5,10]:
            gains=[cid for (cid,k),v in cases.items() if k==n and v[new]['all'] and not v[old]['all']]
            losses=[cid for (cid,k),v in cases.items() if k==n and v[old]['all'] and not v[new]['all']]
            diffs.append({'comparison':name,'top_n':n,'gains':sorted(gains),'losses':sorted(losses)})
    (HERE/'diffs.json').write_text(json.dumps(diffs,ensure_ascii=False,indent=2)+'\n')
    lines=['# 对话分支关键词索引实验（SMM-BR001）','',
           '本实验固定 LoCoMo 的 200 道原问题及 272 段完整对话。GPT-6 Luna high 仅阅读原始对话，',
           '为不同讨论分支提取关键词；检索时仍把整段对话作为候选单位。主要指标只统计预先明确标注的 178 题，',
           '其余 22 题有依赖歧义，未混入主分母。测试过的题和来源不能视为全新盲测。','',
           '## 提取和成本','',
           f"- {audit['source_count']} 段对话产生 {audit['branch_count']} 个分支，平均 {audit['branch_per_source_mean']:.2f} 个/段。",
           f"- 模型调用耗时合计 {audit['inference_seconds_sum']:.1f} 秒，平均 {audit['inference_seconds_mean']:.2f} 秒/段（并行时墙钟时间更短）。",
           f"- 输入/输出 token 合计 {audit['input_tokens_sum']}/{audit['output_tokens_sum']}。",
           f"- 轮次引用覆盖率平均 {audit['turn_reference_coverage_mean']:.1%}；这只能说明轮次被标到，不能证明关键词完整。",
           f"- 机械格式裁定 {len(audit['adjudicated'])} 段，原始响应及裁定均保留。",
           f"- 向量编码含模型加载和整段对照索引耗时 {summary['embedding_seconds_with_model_load']:.1f} 秒；200 题排名计算 {summary['ranking_seconds']:.1f} 秒。",
           '', '## 完整依赖来源取齐','',
           '| 方法 | Top5 全部取齐 | Top5 至少命中一项 | Top5 依赖项覆盖 | Top10 全部取齐 | Top10 至少命中一项 | Top10 依赖项覆盖 | Top5 平均候选数 |',
           '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    names=[('原始整段 BM25','whole_bm25_raw'),('原始整段向量','whole_vector_raw'),
           ('人工设计查询的整段 BM25','whole_bm25_rewritten'),
           ('同一归一化问题＋整段 BM25','whole_bm25_normalized'),
           ('同一归一化问题＋整段向量','whole_vector_normalized'),
           ('同一归一化问题＋分支 BM25','branch_bm25'),
           ('同一归一化问题＋分支向量','branch_vector')]
    for label,key in names:
        a=rows[(key,5)];b=rows[(key,10)]
        lines.append(f"| {label} | {s(a)} | {a['any']}/{a['cases']} | {a['unit_hits']}/{a['unit_total']} | {s(b)} | {b['any']}/{b['cases']} | {b['unit_hits']}/{b['unit_total']} | {a['mean_candidates']:.2f} |")
    lines+=['','同一归一化问题与相同可见来源的对照，更能隔离“分支索引”本身的影响。',
            '原始基线展示现实效果；它同时包含查询处理差异，不能把两者差额全归因于分支。','',
            '## 两路各取 Top5 后去重','',
            '| 索引方案 | 全部取齐 | 至少命中一项 | 平均候选数 |','| --- | ---: | ---: | ---: |']
    ul={'historical_raw':'原始整段','normalized_whole':'归一化整段','branch':'分支关键词'}
    for x in summary['unions']:
        lines.append(f"| {ul[x['variant']]} | {s(x)} | {x['any']}/{x['cases']} | {x['mean_candidates']:.2f} |")
    lines+=['','并集候选数通常大于 5，不能与单路 Top5 直接当作同预算比较。','',
            '## 分支索引的逐题增益与回退','']
    for d in diffs:
        lines.append(f"- {d['comparison']} Top{d['top_n']}：新增 {len(d['gains'])} 题（{', '.join(d['gains']) or '无'}）；回退 {len(d['losses'])} 题（{', '.join(d['losses']) or '无'}）。")
    lines+=['','## 解释边界','',
            '这些数字衡量候选对话是否包含预先标注的必需来源，不衡量 Agent 是否选对证据或答对。',
            'LoCoMo 的 200 道题来自少量共享历史，题目之间不独立；仅凭本组差额不能宣布泛化优势。',
            '若分支索引增加漏检，应检查关键词是否丢了旁支事实、Porter 词形与关键词是否错位，以及每段取最高分是否偏向多分支对话。',
            '所有请求、模型输出、来源绑定、逐题排名和评分脚本均在本目录。','']
    (HERE/'README.md').write_text('\n'.join(lines))
    print(HERE/'README.md')

if __name__=='__main__':main()
