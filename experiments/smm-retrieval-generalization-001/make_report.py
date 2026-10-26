"""Render descriptive tables from sealed retrieval scores; no inference."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    r = json.loads((HERE / 'results.json').read_text())
    cs = r['cases']; ss = r['summaries']; lines = [
        '# 新问题上的 BM25 / 向量 Top N 验证', '',
        '**SMM-RG001，232 道新题，固定当前检索实现，无新增回答或筛选模型调用。**', '',
        '两组分别统计：LongMemEval 从未进入旧实验元数据且时间有效的剩余 32 题全部纳入；LoCoMo 按固定种子随机选取 200 题。'
        '协议、抽样与排除清单在首次检索前固定，运行后没有换题或调参数。完整方法见 [METHOD.md](METHOD.md)，冻结定义见 [protocol.json](protocol.json)。', '',
        '**本页所有比例指全部官方参考对话取齐，不是答案正确率，也不是旧实验 36 项手工必要信息覆盖率。**'
        '旧 25 题同口径 BM25 Top4 为 25/25，向量 Top4 为 23/25，合并为 25/25。', '']
    def aggregate(cohort, route, n):
        return next(s for s in ss if s['cohort'] == cohort and s['slice'] == 'all' and s['route'] == route and s['n'] == n)
    for cohort, title in [('longmemeval_new32', '同源新题：LongMemEval 32 题'), ('locomo_random200', '跨数据集新题：LoCoMo 随机 200 题')]:
        cc = [c for c in cs if c['cohort'] == cohort]
        lines += ['## ' + title, '', '| N | BM25 | 向量 | 两路各 Top N 合并 | 单路数量允许的最高取齐比例 |', '|---|---:|---:|---:|---:|']
        for n in range(1, 6):
            vals = []
            for route in ['bm25', 'vector', 'union']:
                s = aggregate(cohort, route, n); vals.append(f"{s['all_reference']}/{s['cases']}（{s['all_reference']/s['cases']:.1%}）")
            capacity = sum(len(c['official_reference_sources']) <= n for c in cc)
            vals.append(f'{capacity}/{len(cc)}（{capacity/len(cc):.1%}）')
            lines.append(f'| {n} | ' + ' | '.join(vals) + ' |')
        lines += ['', '双路各取 N 可能返回超过 N 段，对照如下；字符为完整原文 Unicode 字符，不是 token 或实测回答耗时。', '',
                  '| 方案 | 取齐题数 | 平均对话数 | 平均原文字符 |', '|---|---:|---:|---:|']
        for route in ['bm25', 'vector', 'union']:
            for n in [3, 4, 5]:
                s = aggregate(cohort, route, n)
                lines.append(f"| {route} Top{n} | {s['all_reference']}/{s['cases']} | {s['mean_candidates']:.2f} | {s['mean_characters']:,.0f} |")
        lines += ['', '### 参考数量不超过 4 的题', '']
        possible = [c for c in cc if len(c['official_reference_sources']) <= 4]
        vals = []
        for route in ['bm25', 'vector', 'union']:
            count = sum(c['cells'][route][3]['all_reference'] for c in possible)
            vals.append(f'{route}：{count}/{len(possible)}（{count/len(possible):.1%}）')
        lines.append('在排除单路容量本身不足的题后，Top4 的实际取齐比例为：' + '；'.join(vals) + '。')
        pair = next(x for x in r['paired'] if x['cohort'] == cohort and x['n'] == 4)
        lines += ['', '### Top4 的逐题配对', '',
                  '| 两路均取齐 | 仅 BM25 取齐 | 仅向量取齐 | 两路各自均未取齐 |', '|---:|---:|---:|---:|',
                  '| ' + ' | '.join(str(len(pair[k])) for k in ['both', 'bm25_only', 'vector_only', 'neither']) + ' |', '',
                  '这是同 N 对比，双路合并的实际输入量另见上表；不据此宣称相同输入成本的优势。', '',
                  '### 参考来源数量分组（Top4）', '', '| 每题参考数 | 题数 | BM25 | 向量 | 合并 |', '|---|---:|---:|---:|---:|']
        for count in sorted({len(c['official_reference_sources']) for c in cc}):
            group = [c for c in cc if len(c['official_reference_sources']) == count]
            vals = [str(sum(c['cells'][route][3]['all_reference'] for c in group)) + '/' + str(len(group)) for route in ['bm25', 'vector', 'union']]
            lines.append(f'| {count} | {len(group)} | ' + ' | '.join(vals) + ' |')
        lines.append('')
    lines += ['## 记录与复算', '',
              '- [逐题结果](case-results.md)：每道题三种路线取齐所需的最小 N。',
              '- [完整机器结果](results.json)：每个 N 的入选与遗漏来源、目标排名、配对。',
              '- [分组汇总](summary.csv)：类别、历史、参考数量、任意命中、引用次数覆盖及输入量。',
              '- [评分冻结记录](scoring-contract.json)：评分代码与输入协议在首次新检索前的绑定。',
              '- `rankings/`：原实现首次返回的两路 Top10 分数与来源；`data/sources/`：完整原文与角色/轮次坐标。',
              '- `vectors/`：原文块与查询向量、来源位置、模型资产哈希、软件版本、缓存/计算记录。', '',
              '从仓库根目录运行：', '', '```bash',
              'python3 -B experiments/smm-retrieval-generalization-001/score.py --check --verify', '```', '',
              '独立重建两路排序需要 NumPy，不需要模型、密钥或网络。方法说明包含从零编码的范围与限制。', '',
              '## 结论边界', '',
              '这是本实现的新问题检索验证，不是新的官方排行榜。两组数据、任务类型、语料量和参考数量分布不同，不合并分母，也不把成绩变化单独归因于数据量。'
              'LoCoMo200 共享10份历史；只检索文本；没有新标注必要事实，没有回答试验。官方来源可能冗余，也可能没有穷尽所有可用旁证，'
              '所以取齐来源是可核验指标，未取齐则需要检查原文，不能自动等同于无法回答。所有局限与许可见 [METHOD.md](METHOD.md)。', '']
    with (HERE / 'README.md').open('x') as f: f.write('\n'.join(lines))


if __name__ == '__main__': main()
