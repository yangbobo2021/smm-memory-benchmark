"""Render the fixed first results without altering queries, labels or rankings."""
import csv
import io
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def artifacts():
    d = json.loads((HERE / 'results.json').read_text())
    runtime = {c['id']: c for c in json.loads((HERE / 'runtime.json').read_text())}
    cohorts = ['original25', 'longmemeval_new32', 'locomo_random200']
    routes = ['bm25_raw', 'bm25_rewritten', 'vector_raw', 'vector_rewritten',
              'union_raw_raw', 'union_rewritten_raw', 'union_raw_rewritten', 'union_rewritten_rewritten']
    lines = ['# SMM-QI001：为 BM25 与向量分别设计查询输入', '',
             '**结果：这批关键词输入改善了 BM25；向量的自然语言改写没有稳定收益；两路都改写后合并有所改善，但仍会漏检和回退。**', '',
             '沿用原25题、后续LongMemEval32题、LoCoMo200题；每题每路一个输入。输入审核和协议冻结后才产生本轮排名。只改变查询，不改变原文、切片、向量模型、BM25公式、时间可见性或候选预算。', '',
             '这是已用题上的输入设计诊断，不是新盲测。输入由本任务 Codex 作者编写并复核，未引入答案专有信息；作者有项目历史知情，未经过外部独立输入质量评审，不能称最优输入或运行时Agent的稳定能力。', '',
             '## 主结果：全部官方参考对话取齐', '',
             '| 测试组 | BM25 原问题→关键词，Top5 | 向量 原问题→语义改写，Top5 | 各取Top4合并，原→改 | 各取Top5合并，原→改 |',
             '|---|---:|---:|---:|---:|']
    def row(co, route, n): return next(x for x in d['summaries'] if x['cohort'] == co and x['route'] == route and x['n'] == n)
    for co in cohorts:
        count = row(co, 'bm25_raw', 5)['cases']
        comparisons = [('bm25_raw', 'bm25_rewritten', 5), ('vector_raw', 'vector_rewritten', 5),
                       ('union_raw_raw', 'union_rewritten_rewritten', 4), ('union_raw_raw', 'union_rewritten_rewritten', 5)]
        cells = [f"{row(co, old, n)['all_reference']}/{count} → {row(co, new, n)['all_reference']}/{count}" for old, new, n in comparisons]
        lines.append('| ' + co + ' | ' + ' | '.join(cells) + ' |')
    lines += ['', '每路Top5是去重后最多10段对话，合并后不再截成5段；参考对话取齐不是最终回答正确率。', '',
              '## 完整 Top1–5 与预注册四种组合', '']
    for co in cohorts:
        lines += [f'### {co}', '', '| 方法 | Top1 | Top2 | Top3 | Top4 | Top5 |', '|---|---:|---:|---:|---:|---:|']
        for route in routes:
            lines.append('| ' + route + ' | ' + ' | '.join(str(row(co, route, n)['all_reference']) for n in range(1, 6)) + ' |')
    lines += ['', '中间两种组合是预先注册的诊断：改BM25+原向量、原BM25+改向量。不能根据成绩挑选其中最好者冒充事前确定的主方案。', '',
              '## Top5逐题增益与回退', '', '| 数据组 | 对照 | 新增取齐 | 原本取齐但本次遗漏 |', '|---|---|---|---|']
    for r in d['paired']:
        if r['n'] == 5:
            lines.append(f"| {r['cohort']} | {r['old']} → {r['new']} | {len(r['gains'])}：{', '.join(r['gains']) or '无'} | {len(r['losses'])}：{', '.join(r['losses']) or '无'} |")
    lines += ['', '## 参考覆盖与候选成本', '',
              '| 数据组 | 合并原/原→改/改，Top5参考段次覆盖 | 平均候选数原→改 | 改写后至少一条参考命中 | 改写后仍未取齐题数 |',
              '|---|---:|---:|---:|---:|']
    for co in cohorts:
        old, new = row(co, 'union_raw_raw', 5), row(co, 'union_rewritten_rewritten', 5)
        lines.append(f"| {co} | {old['reference_hits']} → {new['reference_hits']} / {new['reference_total']} | {old['mean_candidates']:.3f} → {new['mean_candidates']:.3f} | {new['any_reference']}/{new['cases']} | {new['cases']-new['all_reference']} |")
    lines += ['', '## 具体输入与结果', '']
    for cid in ['C037', 'C035', 'L011', 'L028', 'C186']:
        c = runtime[cid]; result = next(c for c in d['cases'] if c['id'] == cid)
        lines += [f'### {cid}', '', c['question'], '', f"BM25：`{c['bm25_input']}`", '', f"向量：{c['vector_input']}", '',
                  '| 参考对话 | 原BM25→改写 | 原向量→改写 |', '|---|---:|---:|']
        for sid, rank in result['reference_ranks'].items():
            lines.append(f"| {sid} | {rank['bm25_raw']} → {rank['bm25_rewritten']} | {rank['vector_raw']} → {rank['vector_rewritten']} |")
        comments = {
            'C037': '保留人物与health scare/scares，三个真实健康事件参考从第4/12/14提高到第1/2/3。原文确实使用单数health scare，改写没有加入具体病名。',
            'C035': '补充vacation/trip/travel等表达，Florida与Oregon两段实际度假/公路旅行记录从第12/6提高到第2/4；输入没有加入两个地点。',
            'L011': '关键词仅bake/baked/baking，去掉something/times等普通词后，四个参考的BM25排名明显改善，但单路仍未全部进入Top5。向量改写还把一条从第4降到第7；两路互补使合并仍取齐。',
            'L028': '真实用户原文是“catch up with Emma ... over lunch today”，Tuesday来自会话日期，不在对应原句中。关键词改写并没有解析日期，并且其他对话的Tuesday等词仍可抢占名次；唯一参考从BM25第5退到第7，向量也从第11退到第14。不能事后加入Emma来修复这题。',
            'C186': '官方参考原文提及在Stamford的收容所领养狗，不直接包含Connecticut/live。改写无法凭空知道未知线索Stamford，引用源从BM25第5退到第21。此题带有地域常识与居住推断，不能把领养地点等同明确居住事实，也不按结果改标注。',
        }
        lines += ['', comments[cid], '']
    lines += ['## 原25题必要证据口径', '', '| 方法 | Top1 | Top2 | Top3 | Top4 | Top5 |', '|---|---:|---:|---:|---:|---:|']
    for route in routes:
        lines.append('| ' + route + ' | ' + ' | '.join(str(row('original25', route, n)['necessary_all']) for n in range(1, 6)) + ' |')
    enc = json.loads((HERE / 'encoding.json').read_text()); comp = json.loads((HERE / 'rankings/complete.json').read_text())
    lines += ['', '## 核验与边界', '',
              f"原257题BM25 Top10与向量Top10均重放原顺序；原分数最大差 {comp['original_vector_max_score_difference']}。40844切片、2947来源保持不变。", '',
              f"本次只编码 {enc['rewritten_query_encodes']} 个改写查询，另编码25个旧查询做原25向量排名重放；0新文档编码、0外部生成模型API调用。编写改写本身由Codex完成，不能将整个实验称为没有使用大模型。", '',
              f"查询编码合计 {sum(r['seconds'] for r in enc['receipts']):.3f} 秒，模型加载 {enc['model_load_seconds']:.3f} 秒。排名算术阶段共 {comp['arithmetic_seconds']:.3f} 秒，包含本轮与旧排名重放，不是线上请求P95，不包括作者编写/审查查询的耗时。", '',
              '作者在运行前检查了语义、范围、时间和是否引入答案；精确人名/宠物名检查480项无遗漏。该检查只验证名称保留，不证明语义或查询最优。时间和否定文字不会自动变成检索引擎的硬过滤。', '',
              '本轮结果支持：查询表达确实影响召回，关键词改写能够改善部分词面匹配；不支持“只要写得更清楚，向量就一定更好”，也不支持“足够好的单个查询就能保证找全”。不得以此次数据继续改写并挑选最好成绩。', '',
              '官方背景引用/标注/替代证据限制沿用父实验，不改gold，不计算回答正确率。仅原25题有必要证据标注。LoCoMo200题来自10份历史，不能当200份独立历史。', '',
              '## 文件与复现', '',
              '- `authored-inputs.tsv`：257对独立输入。',
              '- `runtime.json`、`input-review.json`、`named-anchor-audit.json`：原问题/时钟/候选范围与运行前审核。',
              '- `protocol.json`：冻结文件与SHA256；`evaluation.json`只供评分。',
              '- `queries.npy`和`encoding.json`：全部新查询向量与模型/耗时记录。',
              '- `old-documents.npy`：原25题既有向量的导出；另两组复用父实验文档向量。',
              '- `rankings/`：每题首次完整单路排名；`results.json`和`summary.csv`：逐题评分与汇总。',
              '- `case-audit.json`：改善/回退案例的原句、坐标与来源hash。', '',
              '在仓库根目录，用已装NumPy的Python执行：', '',
              '```sh', 'python -B experiments/smm-query-input-001/lab.py verify', '```', '',
              '重放只读取封存原文/向量/查询/排名，不需要生成模型API，不重新编码。首次查询编码还需要父实验固定MiniLM资产；未把本机模型权重复制进研究仓库。', '',
              '本实验相关上游许可见 [METHOD.md](METHOD.md)，尤其LoCoMo派生材料沿用CC BY-NC 4.0。', '']
    stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, fieldnames=list(d['summaries'][0]))
    writer.writeheader(); writer.writerows(d['summaries'])
    return {'README.md': '\n'.join(lines), 'summary.csv': stream.getvalue()}


if __name__ == '__main__':
    for name, text in artifacts().items():
        with (HERE / name).open('x', newline='') as f: f.write(text)
