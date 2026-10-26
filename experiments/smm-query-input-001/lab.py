"""Fixed single-query input experiment; no generative API or document encoding."""
import argparse
import collections
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import sqlite3
import statistics
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
B = ROOT / 'experiments/smm-baseline-001'
G = ROOT / 'experiments/smm-retrieval-generalization-001'
sys.path.insert(0, str(G / 'implementation'))


def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def th(s): return hashlib.sha256(s.encode()).hexdigest()
def put(p, x):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f: json.dump(x, f, ensure_ascii=False, indent=2); f.write('\n')
def terms(s): return list(dict.fromkeys(re.findall(r'[^\W_]+', s.casefold(), re.UNICODE)))[:128]
def expr(s): return ' OR '.join('"' + t + '"' for t in terms(s))
def ordered(scores): return [dict(source_id=s, score=float(v)) for s, v in sorted(scores.items(), key=lambda x: (-x[1], x[0]))]


def guard():
    protocol = read(HERE / 'protocol.json')
    for rel, h in protocol['files'].items(): assert sha(ROOT / rel) == h, rel
    return protocol


def sources():
    out = {}
    for rel in read(HERE / 'source-files.json'):
        d = read(ROOT / rel)
        records = d['records'] if 'records' in d else [d]
        for r in records:
            assert th(r['text']) == r['source_sha256']
            if r['id'] in out: assert out[r['id']] == r
            out[r['id']] = r
    return out


def prepare(args):
    assert not (HERE / 'protocol.json').exists()
    authored = {}
    for line in (HERE / 'authored-inputs.tsv').read_text().splitlines():
        cid, bm, vec = line.split('\t')
        assert cid not in authored and bm.strip() and vec.strip()
        assert len(terms(bm)) <= 30 and len(vec) < 1000
        authored[cid] = (bm, vec)
    inputs = []; gold = []; baselines = {}; sourcefiles = []; bindings = {}
    oldcases = read(B / 'data/cases.json'); newcases = read(G / 'data/cases.json')
    for base, cases, cohort in [(B, oldcases, 'original25'), (G, newcases, None)]:
        bindings[str((base / 'data/cases.json').relative_to(ROOT))] = sha(base / 'data/cases.json')
        for c in cases:
            cid = c['id']; bm, vec = authored[cid]
            if cohort:
                corpus = B / c['corpus_file']; data = read(corpus)
                ids = sorted(r['id'] for r in data['records'])
                sourcefiles.append(str(corpus.relative_to(ROOT)))
                parent = B / 'data/retrieval' / (cid + '.json'); raw = read(parent)['native']['native']
            else:
                ids = c['source_ids']; parent = G / 'rankings' / (cid + '.json'); raw = read(parent)['native']
            bindings[str(parent.relative_to(ROOT))] = sha(parent)
            baselines[cid] = {k: raw[k] for k in ('bm25', 'vector')}
            inputs.append(dict(id=cid, cohort=cohort or c['cohort'], question=c['question'],
                               bm25_input=bm, vector_input=vec, clock=c['known_at'], source_ids=ids))
            gold.append(dict(id=cid, refs=c['official_reference_sources'], requirements=c.get('requirements', [])))
    assert len(inputs) == 257 and set(authored) == {c['id'] for c in inputs}
    for f in sorted((G / 'data/sources').glob('*.json')): sourcefiles.append(str(f.relative_to(ROOT)))
    put(HERE / 'runtime.json', inputs); put(HERE / 'evaluation.json', gold)
    put(HERE / 'baselines.json', baselines); put(HERE / 'source-files.json', sourcefiles)
    src = sources(); assert len(src) == 2947
    # Export existing original25 chunk vectors; never re-encode original sources.
    oldvecs = []; oldkeys = []; seen = {}; passages = []; seenpassages = {}; dbbindings = []
    for c in oldcases:
        p = Path(args.old_indexes) / (c['namespace'] + '.sqlite')
        dbbindings.append(dict(file=p.name, sha256=sha(p)))
        db = sqlite3.connect('file:' + str(p) + '?mode=ro', uri=True)
        actual = {sid for sid, in db.execute('select id from source_meta')}
        expected = set(next(i for i in inputs if i['id'] == c['id'])['source_ids']); assert actual == expected
        for raw, blob in db.execute('select chunk_json,vector from chunk_meta order by rowid'):
            ch = json.loads(raw); text = src[ch['source_id']]['text'][ch['start']:ch['end']]
            assert text == ch['text']; h = th(text); v = np.frombuffer(blob, dtype='<f4')
            assert v.shape == (384,) and np.isfinite(v).all() and abs(float(np.linalg.norm(v)) - 1) < 1e-5
            if h not in seen: seen[h] = len(oldvecs); oldkeys.append(h); oldvecs.append(v.copy())
            else: assert np.array_equal(oldvecs[seen[h]], v), 'A single text hash has different old vectors'
            key = ch['source_id'], ch['id']
            rec = dict(source_id=ch['source_id'], id=ch['id'], start=ch['start'], end=ch['end'], text_sha256=h)
            if key in seenpassages: assert seenpassages[key] == rec
            else: seenpassages[key] = rec; passages.append(rec)
        db.close()
    np.save(HERE / 'old-documents.npy', np.stack(oldvecs))
    put(HERE / 'old-document-keys.json', oldkeys)
    passages += read(G / 'vectors/passages.json')
    assert len(passages) == 40844
    put(HERE / 'passages.json', passages)
    put(HERE / 'reuse-receipt.json', dict(old_indexes=dbbindings, old_unique_vectors=len(oldvecs),
        old_passages=len(seenpassages), existing_generalization_vectors=22773, new_document_encodes=0))
    # Pre-outcome author review, distinct from automated parsing/shape checks.
    reviews = [dict(id=c['id'], review='author_query_only_semantic_review', identity_preserved=True,
        event_and_requested_attribute_preserved=True, temporal_and_scope_qualifiers_preserved_in_vector=True,
        no_answer_specific_entities_or_values_added=True,
        bm25_temporal_or_negative_constraints_are_not_hard_filters=True) for c in inputs]
    put(HERE / 'input-review.json', dict(status='reviewed_before_retrieval', independent_review=False,
        optimum_quality_proven=False, author_historical_exposure=True, cases=reviews,
        corrections_before_any_new_ranking=['P22 remove downloaded', 'C035 remove added country',
            'C176 remove guessed answer types', 'L022 remove guessed equipment type']))
    files = dict(bindings)
    for p in [HERE / 'METHOD.md', HERE / 'authored-inputs.tsv', HERE / 'lab.py',
              HERE / 'runtime.json', HERE / 'evaluation.json', HERE / 'baselines.json', HERE / 'source-files.json',
              HERE / 'old-documents.npy', HERE / 'old-document-keys.json', HERE / 'passages.json',
              HERE / 'reuse-receipt.json', HERE / 'input-review.json']:
        files[str(p.relative_to(ROOT))] = sha(p)
    for rel in sourcefiles: files[rel] = sha(ROOT / rel)
    for p in (G / 'vectors').iterdir():
        if p.is_file(): files[str(p.relative_to(ROOT))] = sha(p)
    # Bind exact implementation and model asset receipts from the parent experiment.
    for p in (G / 'implementation').rglob('*.py'): files[str(p.relative_to(ROOT))] = sha(p)
    put(HERE / 'protocol.json', dict(id='SMM-QI001', cases=257,
        cohorts={'original25': 25, 'longmemeval_new32': 32, 'locomo_random200': 200},
        primary='raw/raw versus rewritten/rewritten; all official reference conversations at N=1..5',
        diagnostic_unions=['raw/raw', 'rewrite/raw', 'raw/rewrite', 'rewrite/rewrite'],
        inputs_per_route_per_case=1, rerolls=0, query_rewrite_author='Codex in conversation',
        external_generative_calls=0, new_document_encodes=0, files=files))
    print(json.dumps(dict(prepared=True, cases=len(inputs), sources=len(src), passages=len(passages),
                          old_vectors=len(oldvecs), ranking_runs=0)), flush=True)


def encode(args):
    guard(); assert not (HERE / 'encoding.json').exists()
    from next_memory.source_match_presentation import MiniLMQueryEncoder
    assets = read(G / 'vectors/build.json')['assets']
    for rel, h in assets.items(): assert sha(Path(args.model_cache) / rel) == h, rel
    t = time.perf_counter(); encoder = MiniLMQueryEncoder(Path(args.model_cache)); load = time.perf_counter() - t
    rows = read(HERE / 'runtime.json'); keys = []; values = []; receipts = []
    # Original25 query embeddings are reconstructed solely to verify old ranking parity.
    for c in rows:
        variants = [('rewritten', c['vector_input'])]
        if c['cohort'] == 'original25': variants.insert(0, ('raw', c['question']))
        for variant, text in variants:
            t = time.perf_counter(); v = encoder.encode(text.replace('\n', ' ')).astype(np.float32)
            assert v.shape == (384,) and np.isfinite(v).all()
            keys.append([c['id'], variant]); values.append(v)
            receipts.append(dict(id=c['id'], variant=variant, sha256=th(text), seconds=time.perf_counter() - t))
    np.save(HERE / 'queries.npy', np.stack(values)); put(HERE / 'query-keys.json', keys)
    put(HERE / 'encoding.json', dict(model='sentence-transformers/all-MiniLM-L6-v2',
        model_assets=assets, model_load_seconds=load, receipts=receipts,
        new_query_encodes=len(keys), rewritten_query_encodes=257, original25_parity_encodes=25,
        new_document_encodes=0, external_generative_calls=0,
        versions={k: importlib.metadata.version(k) for k in ['numpy', 'fastembed', 'onnxruntime', 'tokenizers']},
        files={n: sha(HERE / n) for n in ['queries.npy', 'query-keys.json']}))
    print(json.dumps(dict(encoded=len(keys), rewritten_queries=257, original25_parity_queries=25)), flush=True)


def vector_store():
    newkeys = read(G / 'vectors/document-keys.json'); oldkeys = read(HERE / 'old-document-keys.json')
    new = np.load(G / 'vectors/documents.npy'); old = np.load(HERE / 'old-documents.npy')
    keys = list(newkeys); lookup = {h: i for i, h in enumerate(keys)}; extras = []
    for h, v in zip(oldkeys, old):
        if h in lookup: assert np.array_equal(new[lookup[h]], v)
        else: lookup[h] = len(keys); keys.append(h); extras.append(v)
    matrix = np.concatenate([new, np.asarray(extras)], axis=0).astype(np.float64)
    assert len(keys) == 39369
    bysource = collections.defaultdict(list)
    for p in read(HERE / 'passages.json'): bysource[p['source_id']].append(lookup[p['text_sha256']])
    return matrix, bysource


def query_vectors():
    info = read(HERE / 'encoding.json')
    for rel, h in info['files'].items(): assert sha(HERE / rel) == h
    out = {tuple(k): v.astype(np.float64) for k, v in zip(read(HERE / 'query-keys.json'), np.load(HERE / 'queries.npy'))}
    for cid, v in zip(read(G / 'vectors/query-keys.json'), np.load(G / 'vectors/queries.npy')):
        out[cid, 'raw'] = v.astype(np.float64)
    return out


def compute(check=False):
    guard(); src = sources(); matrix, bysource = vector_store(); queries = query_vectors()
    baseline = read(HERE / 'baselines.json'); cases = read(HERE / 'runtime.json'); outputs = []; dbs = {}; maxdelta = 0.0
    start = time.perf_counter()
    try:
        for c in cases:
            key = tuple(c['source_ids'])
            if key not in dbs:
                db = sqlite3.connect(':memory:'); db.execute("create virtual table f using fts5(text,tokenize='unicode61')")
                db.executemany('insert into f(rowid,text) values(?,?)', [(i + 1, src[s]['text']) for i, s in enumerate(key)])
                dbs[key] = db
            db = dbs[key]
            assert all(src[s]['received_at'] <= c['clock'] for s in key)
            rankings = {}; times = {}
            for variant, text in [('raw', c['question']), ('rewritten', c['bm25_input'])]:
                t = time.perf_counter()
                rankings['bm25_' + variant] = ordered({key[i - 1]: -float(z) for i, z in db.execute('select rowid,bm25(f) from f where f match ?', (expr(text),))})
                times['bm25_' + variant] = time.perf_counter() - t
            indices = np.array(sorted({i for s in key for i in bysource[s]})); sub = matrix[indices]
            local = {g: i for i, g in enumerate(indices)}
            local_source = {s: [local[i] for i in bysource[s]] for s in key}
            for variant in ('raw', 'rewritten'):
                t = time.perf_counter(); scores = sub @ queries[c['id'], variant]
                rankings['vector_' + variant] = ordered({s: max(scores[ix]) for s, ix in local_source.items()})
                times['vector_' + variant] = time.perf_counter() - t
            assert rankings['bm25_raw'][:10] == baseline[c['id']]['bm25'], c['id']
            v = rankings['vector_raw'][:10]; old = baseline[c['id']]['vector']
            assert [x['source_id'] for x in v] == [x['source_id'] for x in old], c['id']
            delta = max(abs(x['score'] - y['score']) for x, y in zip(v, old)); maxdelta = max(maxdelta, delta)
            assert delta < 1e-6, (c['id'], delta)
            result = dict(id=c['id'], cohort=c['cohort'], rankings=rankings)
            file = HERE / 'rankings' / (c['id'] + '.json')
            if check: assert read(file) == result, c['id']
            else: put(file, result)
            outputs.append(result)
        if not check:
            put(HERE / 'rankings/complete.json', dict(cases=len(cases), original_bm25_exact_replays=257,
                original_vector_top10_order_replays=257, original_vector_max_score_difference=maxdelta,
                arithmetic_seconds=time.perf_counter() - start,
                files={c['id'] + '.json': sha(HERE / 'rankings' / (c['id'] + '.json')) for c in cases}))
    finally:
        for db in dbs.values(): db.close()
    print(json.dumps(dict(ranking_replay=check, cases=len(cases), original_vector_max_delta=maxdelta)), flush=True)


def score(check=False):
    guard(); gold = {c['id']: c for c in read(HERE / 'evaluation.json')}
    complete = read(HERE / 'rankings/complete.json')
    for rel, h in complete['files'].items(): assert sha(HERE / 'rankings' / rel) == h
    rows = []; routes = ['bm25_raw', 'bm25_rewritten', 'vector_raw', 'vector_rewritten',
                        'union_raw_raw', 'union_rewritten_raw', 'union_raw_rewritten', 'union_rewritten_rewritten']
    for c in read(HERE / 'runtime.json'):
        rankings = read(HERE / 'rankings' / (c['id'] + '.json'))['rankings']; g = gold[c['id']]; refs = set(g['refs']); cells = {}
        for route in routes:
            cells[route] = []
            for n in range(1, 6):
                if route.startswith('union_'):
                    a, b = route.removeprefix('union_').split('_'); selected = {v['source_id'] for k in ['bm25_' + a, 'vector_' + b] for v in rankings[k][:n]}
                else: selected = {v['source_id'] for v in rankings[route][:n]}
                hit = refs & selected; req = g['requirements']
                atom_hits = sum(any(w['source_id'] in selected for w in a['witnesses']) for a in req)
                cells[route].append(dict(n=n, selected=sorted(selected), count=len(selected),
                    all_reference=refs <= selected, any_reference=bool(hit), reference_hits=len(hit),
                    missing=sorted(refs - selected), necessary_atoms=atom_hits if req else None,
                    necessary_total=len(req) if req else None, all_necessary=(atom_hits == len(req)) if req else None))
        rows.append(dict(id=c['id'], cohort=c['cohort'], question=c['question'], refs=sorted(refs), cells=cells,
            reference_ranks={s: {k: next((i + 1 for i, x in enumerate(v) if x['source_id'] == s), None)
                                 for k, v in rankings.items()} for s in sorted(refs)}))
    summaries = []; pairs = []
    for cohort in dict.fromkeys(c['cohort'] for c in rows):
        sample = [c for c in rows if c['cohort'] == cohort]
        for route in routes:
            for n in range(1, 6):
                cells = [c['cells'][route][n - 1] for c in sample]
                summaries.append(dict(cohort=cohort, route=route, n=n, cases=len(sample),
                    all_reference=sum(x['all_reference'] for x in cells), any_reference=sum(x['any_reference'] for x in cells),
                    reference_hits=sum(x['reference_hits'] for x in cells), reference_total=sum(len(c['refs']) for c in sample),
                    mean_candidates=statistics.mean(x['count'] for x in cells),
                    necessary_all=sum(x['all_necessary'] for x in cells) if cohort == 'original25' else None,
                    necessary_hits=sum(x['necessary_atoms'] for x in cells) if cohort == 'original25' else None))
        for old, new in [('bm25_raw', 'bm25_rewritten'), ('vector_raw', 'vector_rewritten'), ('union_raw_raw', 'union_rewritten_rewritten')]:
            for n in range(1, 6):
                gain = [c['id'] for c in sample if not c['cells'][old][n-1]['all_reference'] and c['cells'][new][n-1]['all_reference']]
                loss = [c['id'] for c in sample if c['cells'][old][n-1]['all_reference'] and not c['cells'][new][n-1]['all_reference']]
                pairs.append(dict(cohort=cohort, old=old, new=new, n=n, gains=gain, losses=loss))
    result = dict(id='SMM-QI001', metric='all official reference source conversations, not answer accuracy',
                  summaries=summaries, paired=pairs, cases=rows)
    if check: assert read(HERE / 'results.json') == result
    else: put(HERE / 'results.json', result)
    print(json.dumps(dict(score_replay=check, cases=257, top5=[s for s in summaries if s['n'] == 5])), flush=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('mode', choices=['prepare', 'encode', 'rank', 'score', 'verify'])
    parser.add_argument('--old-indexes'); parser.add_argument('--model-cache'); args = parser.parse_args()
    if args.mode == 'prepare': prepare(args)
    elif args.mode == 'encode': encode(args)
    elif args.mode == 'rank': compute()
    elif args.mode == 'score': score()
    else: compute(check=True); score(check=True)


if __name__ == '__main__': main()
