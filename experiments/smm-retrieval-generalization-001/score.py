"""Score frozen official-source retrieval labels; no generative judging.

--verify also rebuilds BM25 directly from archived originals and independently
recalculates max-chunk vector scores from archived vectors, without ONNX/API.
"""
import argparse
import collections
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sqlite3
import statistics

HERE = Path(__file__).resolve().parent


def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(x): return json.dumps(x, ensure_ascii=False, indent=2) + '\n'


def results(verify=False):
    protocol = read(HERE / 'protocol.json')
    for rel, h in protocol['frozen_files'].items(): assert sha(HERE / rel) == h, rel
    build = read(HERE / 'vectors/build.json')
    for rel, h in build['files'].items(): assert sha(HERE / 'vectors' / rel) == h, rel
    complete = read(HERE / 'rankings/complete.json')
    for rel, h in complete['files'].items(): assert sha(HERE / 'rankings' / rel) == h, rel
    cases = read(HERE / 'data/cases.json')
    sources = {p.stem: read(p) for p in (HERE / 'data/sources').glob('*.json')}
    checks = collections.Counter()
    for sid, r in sources.items():
        assert hashlib.sha256(r['text'].encode()).hexdigest() == r['source_sha256']; checks['source_hash'] += 1
    if verify:
        import numpy as np
        passages = read(HERE / 'vectors/passages.json')
        vectors = np.load(HERE / 'vectors/documents.npy', mmap_mode='r')
        qvectors = np.load(HERE / 'vectors/queries.npy', mmap_mode='r')
        assert read(HERE / 'vectors/query-keys.json') == [c['id'] for c in cases]
        keys = read(HERE / 'vectors/document-keys.json'); positions = {h: i for i, h in enumerate(keys)}
        bysource = collections.defaultdict(list)
        for p in passages:
            text = sources[p['source_id']]['text'][p['start']:p['end']]
            assert hashlib.sha256(text.encode()).hexdigest() == p['text_sha256']
            bysource[p['source_id']].append(positions[p['text_sha256']]); checks['passage_coordinate_hash'] += 1
    output = []; dbs = {}
    try:
        for i, c in enumerate(cases):
            assert set(c['official_reference_sources']) <= set(c['source_ids'])
            assert all(sources[s]['received_at'] <= c['known_at'] for s in c['source_ids'])
            for w in c['marked_turns_evaluation_only']:
                r = sources[w['source_id']]
                assert r['text'][w['start']:w['end']] == w['quote']
                assert any(p['role'] == w['role'] and p['start'] == w['start'] and p['end'] == w['end'] for p in r['structure']['parts'])
                checks['official_turn_quote'] += 1
            r = read(HERE / 'rankings' / (c['id'] + '.json'))
            assert r['query'] == c['question'] and r['clock'] == c['known_at'] and r['source_ids'] == c['source_ids']
            native = r['native']; refs = set(c['official_reference_sources'])
            for route in ['bm25', 'vector']:
                ids = [x['source_id'] for x in native[route]]
                assert len(ids) == len(set(ids)) and set(ids) <= set(c['source_ids'])
            if verify:
                group = c['cohort'], c['family']
                if group not in dbs:
                    db = sqlite3.connect(':memory:'); db.execute("create virtual table f using fts5(text,tokenize='unicode61')")
                    with db:
                        for j, sid in enumerate(c['source_ids'], 1): db.execute('insert into f(rowid,text)values(?,?)', (j, sources[sid]['text']))
                    dbs[group] = db
                tokens = list(dict.fromkeys(re.findall(r'[^\W_]+', c['question'].casefold(), re.UNICODE)))[:128]
                expr = ' OR '.join('"' + t + '"' for t in tokens)
                bm = [dict(source_id=c['source_ids'][j - 1], score=-float(v)) for j, v in dbs[group].execute('select rowid,bm25(f)from f where f match ?', (expr,))]
                bm.sort(key=lambda x: (-x['score'], x['source_id']))
                assert bm[:10] == native['bm25'], ('independent_bm25', c['id'])
                best = {}
                for sid in c['source_ids']:
                    z = np.asarray(vectors[bysource[sid]], dtype=np.float64) @ qvectors[i].astype(np.float64)
                    best[sid] = float(max(z))
                ordered = sorted(best, key=lambda sid: (-best[sid], sid))[:10]
                assert ordered == [v['source_id'] for v in native['vector']], ('independent_vector', c['id'])
                assert all(abs(best[v['source_id']] - v['score']) < 1e-12 for v in native['vector'])
                checks['independent_route_rank'] += 2
            cells = {}
            for route in ['bm25', 'vector', 'union']:
                cells[route] = []
                for n in range(1, 6):
                    routes = ['bm25', 'vector'] if route == 'union' else [route]
                    chosen = sorted({v['source_id'] for k in routes for v in native[k][:n]})
                    hit = len(refs & set(chosen))
                    cells[route].append(dict(n=n, selected=chosen, count=len(chosen), any_hit=hit > 0,
                        all_reference=hit == len(refs), covered_references=hit, total_references=len(refs),
                        missing_references=sorted(refs - set(chosen)), characters=sum(len(sources[s]['text']) for s in chosen)))
            output.append(dict(case_id=c['id'], cohort=c['cohort'], family=c['family'], type=c['type'], question=c['question'],
                corpus_size=len(c['source_ids']), official_reference_sources=sorted(refs),
                target_ranks={sid: {k: next((j + 1 for j, v in enumerate(native[k]) if v['source_id'] == sid), None) for k in ['bm25', 'vector']} for sid in sorted(refs)},
                cells=cells))
    finally:
        for db in dbs.values(): db.close()
    summaries = []; pairs = []
    for cohort in sorted({c['cohort'] for c in output}):
        cohort_cases = [c for c in output if c['cohort'] == cohort]
        slices = [('all', cohort_cases)]
        slices += [('type:' + t, [c for c in cohort_cases if c['type'] == t]) for t in sorted({c['type'] for c in cohort_cases})]
        slices += [('family:' + t, [c for c in cohort_cases if c['family'] == t]) for t in sorted({c['family'] for c in cohort_cases})]
        slices += [('reference_count:' + str(t), [c for c in cohort_cases if len(c['official_reference_sources']) == t]) for t in sorted({len(c['official_reference_sources']) for c in cohort_cases})]
        for label, sample in slices:
            for route in ['bm25', 'vector', 'union']:
                for n in range(1, 6):
                    cells = [c['cells'][route][n - 1] for c in sample]
                    summaries.append(dict(cohort=cohort, slice=label, route=route, n=n, cases=len(sample),
                        all_reference=sum(x['all_reference'] for x in cells), any_reference=sum(x['any_hit'] for x in cells),
                        covered_references=sum(x['covered_references'] for x in cells), total_references=sum(x['total_references'] for x in cells),
                        mean_candidates=statistics.mean(x['count'] for x in cells), mean_characters=statistics.mean(x['characters'] for x in cells)))
        for n in range(1, 6):
            bins = collections.defaultdict(list)
            for c in cohort_cases:
                b = c['cells']['bm25'][n - 1]['all_reference']; v = c['cells']['vector'][n - 1]['all_reference']
                bins['both' if b and v else 'bm25_only' if b else 'vector_only' if v else 'neither'].append(c['case_id'])
            pairs.append(dict(cohort=cohort, n=n, **{k: bins[k] for k in ['both', 'bm25_only', 'vector_only', 'neither']}))
    return dict(experiment_id=protocol['id'], protocol_sha256=sha(HERE / 'protocol.json'), cases=output, summaries=summaries,
                paired=pairs, new_generative_calls=0, metric='All official reference source sessions, not custom necessary-fact atoms.'), dict(checks)


def artifacts(result):
    fields = list(result['summaries'][0]); stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, fields)
    writer.writeheader(); writer.writerows(result['summaries'])
    lines = ['# All official reference sources at Top1–5', '',
             'Question-level all-reference coverage. `—` in target ranks means outside retained Top10, not absent from the full index.', '']
    for cohort in sorted({c['cohort'] for c in result['cases']}):
        lines += ['## ' + cohort, '', '| N | BM25 | Vector | Union of each Top N |', '|---|---:|---:|---:|']
        rows = [s for s in result['summaries'] if s['cohort'] == cohort and s['slice'] == 'all']
        for n in range(1, 6):
            cells = []
            for route in ['bm25', 'vector', 'union']:
                s = next(s for s in rows if s['route'] == route and s['n'] == n)
                cells.append(f"{s['all_reference']}/{s['cases']} ({s['all_reference']/s['cases']:.1%})")
            lines.append(f'| {n} | ' + ' | '.join(cells) + ' |')
        lines += ['', '| Case | Type | Corpus | Refs | BM25 minimum N | Vector minimum N | Union minimum N |', '|---|---|---:|---:|---:|---:|---:|']
        for c in result['cases']:
            if c['cohort'] != cohort: continue
            mins = [next((str(x['n']) for x in c['cells'][route] if x['all_reference']), '>5') for route in ['bm25', 'vector', 'union']]
            lines.append(f"| {c['case_id']} | {c['type']} | {c['corpus_size']} | {len(c['official_reference_sources'])} | " + ' | '.join(mins) + ' |')
        lines.append('')
    return {'results.json': dump(result), 'summary.csv': stream.getvalue(), 'case-results.md': '\n'.join(lines) + '\n'}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--check', action='store_true'); p.add_argument('--verify', action='store_true')
    args = p.parse_args(); result, checks = results(args.verify)
    for rel, text in artifacts(result).items():
        path = HERE / rel
        if args.check: assert path.read_bytes() == text.encode(), rel
        else:
            with path.open('x', newline='') as f: f.write(text)
    print(json.dumps(dict(passed=True, questions=len(result['cases']), independent=args.verify, checks=checks, generative_calls=0)))


if __name__ == '__main__': main()
