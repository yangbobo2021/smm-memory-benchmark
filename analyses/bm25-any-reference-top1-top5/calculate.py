"""Replay raw-question BM25 Top1-5 reference coverage from frozen inputs."""
import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENTS = {
    'baselines': ROOT / 'experiments/smm-query-input-001/baselines.json',
    'runtime': ROOT / 'experiments/smm-sufficiency-001/runtime.json',
    'evaluation': ROOT / 'experiments/smm-sufficiency-001/evaluation.json',
}
ORDER = ('original25', 'longmemeval_new32', 'locomo_random200')


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def build():
    baselines = read(PARENTS['baselines'])
    runtime = read(PARENTS['runtime'])
    evaluation = {e['id']: e for e in read(PARENTS['evaluation'])}
    assert len(runtime) == len(baselines) == len(evaluation) == 257
    cases = []
    for c in runtime:
        cid = c['id']
        ranked = [r['source_id'] for r in baselines[cid]['bm25'][:5]]
        assert len(ranked) == len(set(ranked)) == 5
        assert ranked == c['initial_source_ids']
        e = evaluation[cid]
        cases.append(dict(id=cid, cohort=c['cohort'], bm25_top5=ranked,
                          official_refs=e['official_refs'],
                          semantic_evaluable=e['semantic_evaluable'],
                          necessary_units=e['requirements']))
    save(HERE / 'inputs.json', cases)
    save(HERE / 'bindings.json', {k: sha(p) for k, p in PARENTS.items()})


def calculate(cases):
    assert len(cases) == 257
    groups = defaultdict(list)
    per_case = []
    for c in cases:
        assert c['cohort'] in ORDER and len(c['bm25_top5']) == 5
        refs = set(c['official_refs'])
        assert refs
        item = dict(id=c['id'], cohort=c['cohort'], official_reference_count=len(refs),
                    semantic_evaluable=c['semantic_evaluable'], top=[])
        for n in range(1, 6):
            top = set(c['bm25_top5'][:n])
            covered = sorted(top & refs)
            row = dict(n=n, official_any=bool(covered), official_all=refs <= top,
                       official_covered=covered)
            if c['semantic_evaluable']:
                unit_hits = [any(set(witness) <= top for witness in unit)
                             for unit in c['necessary_units']]
                row.update(necessary_any=any(unit_hits), necessary_all=all(unit_hits),
                           necessary_units_hit=sum(unit_hits),
                           necessary_units_total=len(unit_hits))
            item['top'].append(row)
        per_case.append(item)
        groups[c['cohort']].append(item)

    def summarize(items):
        out = dict(questions=len(items), semantic_evaluable=sum(x['semantic_evaluable'] for x in items), top={})
        for n in range(1, 6):
            rows = [x['top'][n-1] for x in items]
            valid = [r for r in rows if 'necessary_any' in r]
            out['top'][str(n)] = dict(
                official_any=sum(r['official_any'] for r in rows),
                official_all=sum(r['official_all'] for r in rows),
                official_partial=sum(r['official_any'] and not r['official_all'] for r in rows),
                official_zero=sum(not r['official_any'] for r in rows),
                necessary_any=sum(r['necessary_any'] for r in valid),
                necessary_all=sum(r['necessary_all'] for r in valid),
            )
            assert (out['top'][str(n)]['official_all'] + out['top'][str(n)]['official_partial']
                    + out['top'][str(n)]['official_zero'] == len(items))
        return out

    return dict(metric='raw-question full-conversation BM25; source-level official reference intersection',
                groups={name: summarize(groups[name]) for name in ORDER},
                overall=summarize(per_case), per_case=per_case)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--build', action='store_true')
    p.add_argument('--check', action='store_true')
    args = p.parse_args()
    if args.build:
        build()
    inputs = read(HERE / 'inputs.json')
    result = calculate(inputs)
    if args.check:
        assert result == read(HERE / 'results.json')
        print('257-case local replay OK')
    else:
        save(HERE / 'results.json', result)
        for name, group in list(result['groups'].items()) + [('overall', result['overall'])]:
            print(name, group['questions'], [(n, group['top'][str(n)]['official_any'],
                                               group['top'][str(n)]['official_all']) for n in range(1, 6)])


if __name__ == '__main__':
    main()
