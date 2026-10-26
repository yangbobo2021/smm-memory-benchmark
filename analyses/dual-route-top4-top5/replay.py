"""Recount fixed original BM25/vector results; standard library, no model calls."""
import argparse
import collections
import hashlib
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent


def render(inputs):
    cases = []
    for c in inputs:
        refs = set(c['refs'])
        assert refs and len(refs) == len(c['refs'])
        rankings = c['rankings']
        for values in rankings.values():
            assert len(values) == len(set(values))
        cells = {}
        for n in (4, 5):
            b = set(rankings['bm25'][:n])
            v = set(rankings['vector'][:n])
            cells[str(n)] = {}
            for route, chosen in [('bm25', b), ('vector', v), ('union', b | v)]:
                cells[str(n)][route] = dict(
                    candidates=sorted(chosen), candidate_count=len(chosen),
                    hit=sorted(refs & chosen), missing=sorted(refs - chosen),
                    all_reference=refs <= chosen, any_reference=bool(refs & chosen))
            assert b <= b | v and v <= b | v
        assert set(cells['4']['union']['candidates']) <= set(cells['5']['union']['candidates'])
        cases.append(dict(id=c['id'], cohort=c['cohort'], question=c['question'],
                          refs=sorted(refs), cells=cells,
                          reference_ranks={s: {k: (a.index(s) + 1 if s in a else None)
                                               for k, a in rankings.items()} for s in sorted(refs)}))
    summaries = []
    for cohort in dict.fromkeys(c['cohort'] for c in cases):
        group = [c for c in cases if c['cohort'] == cohort]
        for n in (4, 5):
            for route in ('bm25', 'vector', 'union'):
                cells = [c['cells'][str(n)][route] for c in group]
                summaries.append(dict(cohort=cohort, n=n, route=route, cases=len(group),
                    all_reference=sum(x['all_reference'] for x in cells),
                    any_reference=sum(x['any_reference'] for x in cells),
                    reference_hits=sum(len(x['hit']) for x in cells),
                    reference_total=sum(len(c['refs']) for c in group),
                    mean_candidates=statistics.mean(x['candidate_count'] for x in cells),
                    missing_cases=[c['id'] for c in group if not c['cells'][str(n)][route]['all_reference']]))
    result = dict(metric='All official reference conversations, not final answering accuracy.',
                  reused_cases=257, new_queries=0, new_embeddings=0, new_model_calls=0,
                  summaries=summaries, cases=cases)
    lines = ['# BM25 与向量各取 Top4 / Top5 的合并覆盖复核', '',
             '复用已有 257 题的首次排名；没有新抽题、改算法或模型调用。两路分别取 N 后按对话 ID 去重，保留整个并集，不再截为 N 条。', '',
             '**指标：全部官方参考对话是否在候选中。不是最终回答正确率，也不表示已穷尽所有语义相关对话。**', '',
             '| 数据组 | 每路 N | BM25 取齐 | 向量取齐 | 两路合并取齐 | 合并参考段次覆盖 | 平均候选数 |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for cohort in dict.fromkeys(c['cohort'] for c in cases):
        for n in (4, 5):
            rows = {r['route']: r for r in summaries if r['cohort'] == cohort and r['n'] == n}
            u = rows['union']
            values = [f"{rows[k]['all_reference']}/{u['cases']} ({rows[k]['all_reference']/u['cases']:.1%})"
                      for k in ('bm25', 'vector', 'union')]
            lines.append(f"| {cohort} | {n} | " + ' | '.join(values)
                         + f" | {u['reference_hits']}/{u['reference_total']} | {u['mean_candidates']:.2f} |")
    lines += ['', '## 合并后仍未取齐的题', '', '| 数据组 | 每路 N | 题号 |', '|---|---:|---|']
    for r in summaries:
        if r['route'] == 'union':
            lines.append(f"| {r['cohort']} | {r['n']} | {', '.join(r['missing_cases']) or '无'} |")
    lines += ['', '## 逐题可复核信息', '',
              '`results.json` 保留每题两路候选、并集、已覆盖与遗漏的参考对话，以及参考对话在原 Top10 中的名次。名次 null 仅表示未进已保存 Top10。', '',
              '`inputs.json` 是本次统计所需的精简固定输入；`bindings.json` 记录原始问题、参考标注与排名文件的 SHA256。', '',
              '独立复算：`python3 replay.py --check`；只需要此目录，不读取原项目、不联网、不执行模型。', '',
              '限制：最初25题和后续32/200题均已使用过，本次是统计复核，不是新盲测。LoCoMo 200题来自10份历史，不能当200份独立历史。', '',
              '官方参考有背景对话和既有标注问题（如 L004/L015、C088/C172），也可能有替代证据（如 C198）。因此未取齐不等于一定无法作答；本次不修改参考标签，也不据此报告回答正确率。', '',
              '上游数据与派生索引沿用原实验许可和归属，尤其 LoCoMo 数据为 CC BY-NC 4.0；不受仓库代码 MIT 许可替代。', '']
    return result, '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    inputs = json.loads((HERE / 'inputs.json').read_text())
    assert len(inputs) == 257 and len({c['id'] for c in inputs}) == 257
    assert collections.Counter(c['cohort'] for c in inputs) == dict(
        original25=25, longmemeval_new32=32, locomo_random200=200)
    binding = json.loads((HERE / 'bindings.json').read_text())
    assert hashlib.sha256((HERE / 'inputs.json').read_bytes()).hexdigest() == binding['inputs_sha256']
    result, report = render(inputs)
    raw = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.check:
        assert (HERE / 'results.json').read_text() == raw
        assert (HERE / 'README.md').read_text() == report
    else:
        for name, content in [('results.json', raw), ('README.md', report)]:
            with (HERE / name).open('x') as f:
                f.write(content)
    print(json.dumps(dict(passed=True, cases=len(inputs), summaries=result['summaries']), ensure_ascii=False))


if __name__ == '__main__':
    main()
