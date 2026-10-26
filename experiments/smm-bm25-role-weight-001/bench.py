"""Frozen paired BM25 experiment: whole text vs separate role scores at 7:3.

Two independent FTS5 indexes, not bm25(table, .7, .3). Exact raw scores, no
normalization; absent role match=0. The 5:5 diagnostic reuses the same scores.
All originals and existing labels remain in their immutable parent bundles.
"""
import argparse
import collections
import csv
import datetime
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sqlite3
import statistics
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
B = ROOT / 'experiments/smm-baseline-001'
G = ROOT / 'experiments/smm-retrieval-generalization-001'
ARMS = ('whole', 'split50', 'split70')


def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def th(s): return hashlib.sha256(s.encode()).hexdigest()
def dump(x): return json.dumps(x, ensure_ascii=False, indent=2) + '\n'
def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f: f.write(dump(x))


def freeze():
    assert not (HERE / 'protocol.json').exists()
    runtime = []; evaluation = []; inputs = {}
    def bind(p):
        inputs[str(p.relative_to(ROOT))] = sha(p)
        return read(p)
    for c in bind(B / 'data/cases.json'):
        cp = B / c['corpus_file']; bind(cp)
        rp = B / 'data/retrieval' / (c['id'] + '.json'); bind(rp)
        runtime.append(dict(id=c['id'], cohort='original25', question=c['question'], clock=c['known_at'],
                            corpus=str(cp.relative_to(ROOT)), parent_rankings=str(rp.relative_to(ROOT))))
        evaluation.append(dict(id=c['id'], type=c['type'], refs=c['official_reference_sources'],
                               requirements=c['requirements'], parent_case_id=c['id']))
    for c in bind(G / 'data/cases.json'):
        if c['cohort'] != 'longmemeval_new32': continue
        paths = [G / 'data/sources' / (sid + '.json') for sid in c['source_ids']]
        for p in paths: bind(p)
        rp = G / 'rankings' / (c['id'] + '.json'); bind(rp)
        runtime.append(dict(id=c['id'], cohort='previous_new32', question=c['question'], clock=c['known_at'],
                            source_files=[str(p.relative_to(ROOT)) for p in paths], parent_rankings=str(rp.relative_to(ROOT))))
        evaluation.append(dict(id=c['id'], type=c['type'], refs=c['official_reference_sources'], requirements=None,
                               parent_case_id=c['id']))
    assert len(runtime) == 57
    save(HERE / 'runtime.json', runtime); save(HERE / 'evaluation.json', evaluation)
    save(HERE / 'protocol.json', dict(id='SMM-BM25-RW001', frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        hypothesis='User-originated text should have more influence than AI-originated text.',
        primary_candidate='0.7 * BM25(user_text) + 0.3 * BM25(assistant_text)',
        controls=dict(whole='Exact original full-conversation BM25, replay parent Top10 before comparing.',
                      split50='0.5 * BM25(user_text) + 0.5 * BM25(assistant_text), diagnostic only, same component scores.'),
        scope='57 previously measured English LongMemEval questions: original25 development and later32 separately. This is an optimization comparison, not a fresh unseen holdout.',
        excluded='200 LoCoMo questions: both named speakers are human. Do not invent user/AI role labels.',
        field_construction='Concatenate original message blocks of the same explicit role, preserving original role headers and inter-message separators byte-for-byte. A block starts at previous message end and ends at current body end. User and assistant block sets partition the complete original text. No new summaries, rewriting or truncation.',
        indexing='Three independent single-column FTS5 unicode61 tables with identical source membership: whole/user/assistant. Each index has its own document frequencies and average length. Empty role fields remain indexed as empty documents.',
        scoring='Positive scores=-SQLite bm25(). Raw independent role scores, no MinMax, probability calibration, per-case weights or reranking. No match on one role contributes0. Candidates are union of matching role documents; neither role matched => omit. All eligible sources scored before TopN; deterministic sourceID tie break.',
        query='Unmodified original question, same casefold/Unicode word split/dedup/max128 OR terms. No stemming, stopword removal, keyword rewriting, required terms or semantic expansion.',
        metrics='Top1..5 question-level all official reference conversations; any-reference, reference-occurrence coverage, paired gains/losses, reference rank movements and type slices. Existing36 necessary atoms scored only for original25, never invented for later32.',
        interpretation='Compare complete role-split pipeline with original. Splitting changes corpus statistics and length normalization; 7:3 is the requested arithmetic weight, not a calibrated70% contribution guarantee. 5:5 helps diagnose splitting vs weight effects. Do not change weight or labels after outcomes.',
        failures='Retain every first ranking and deterioration. No prompt, gold or threshold tuning, answer/selection model, vector encoding or default deployment.',
        new_queries_at_freeze=0, llm_calls_budget=0, embedding_calls_budget=0,
        parent_inputs=inputs, frozen_local_inputs={p.name:sha(p) for p in [HERE/'bench.py', HERE/'runtime.json', HERE/'evaluation.json']}))
    print(json.dumps(dict(frozen=True, cases=57, arms=list(ARMS), new_queries=0)))


def guard():
    p = read(HERE / 'protocol.json')
    for rel, h in p['parent_inputs'].items(): assert sha(ROOT / rel) == h, rel
    for rel, h in p['frozen_local_inputs'].items():
        if rel == 'bench.py' and (HERE / 'execution-amendment.json').exists():
            amendment = read(HERE / 'execution-amendment.json')
            assert amendment['protocol_sha256'] == sha(HERE / 'protocol.json')
            assert amendment['original_script_sha256'] == h == sha(HERE / 'provenance/bench-initial.py')
            assert amendment['ranking_files_before_repair'] == 0
            h = amendment['repaired_script_sha256']
        assert sha(HERE / rel) == h, rel
    return p


def corpus(case):
    if 'corpus' in case:
        d = read(ROOT / case['corpus'])
        rows = [dict(r, structure=d['structure'][r['id']]) for r in d['records']]
    else: rows = [read(ROOT / rel) for rel in case['source_files']]
    assert len({r['id'] for r in rows}) == len(rows)
    assert all(r['received_at'] <= case['clock'] for r in rows)
    return sorted(rows, key=lambda r: r['id'])


def split_roles(record):
    assert th(record['text']) == record['source_sha256']
    blocks = {'user': [], 'assistant': []}; spans = []; previous = 0
    for part in record['structure']['parts']:
        role = part['role']; assert role in blocks
        assert previous <= part['start'] <= part['end'] <= len(record['text'])
        block = record['text'][previous:part['end']]
        assert block.lstrip().startswith(role.upper() + ':\n')
        blocks[role].append(block); spans.append(dict(role=role, start=previous, end=part['end']))
        previous = part['end']
    assert previous == len(record['text'])
    fields = {role: ''.join(bs) for role, bs in blocks.items()}
    assert sum(len(s) for s in fields.values()) == len(record['text'])
    assert ''.join(record['text'][s['start']:s['end']] for s in spans) == record['text']
    return fields, spans


def expression(question):
    tokens = list(dict.fromkeys(re.findall(r'[^\W_]+', question.casefold(), re.UNICODE)))
    return ' OR '.join('"' + t + '"' for t in tokens[:128])


def compute(case):
    started = time.perf_counter(); rows = corpus(case); db = sqlite3.connect(':memory:')
    try:
        for field in ['whole', 'user', 'assistant']:
            db.execute(f"create virtual table {field} using fts5(text,tokenize='unicode61')")
        receipts = []
        with db:
            for i, r in enumerate(rows, 1):
                fields, spans = split_roles(r)
                for field, text in dict(whole=r['text'], **fields).items():
                    db.execute(f'insert into {field}(rowid,text)values(?,?)', (i, text))
                receipts.append(dict(source_id=r['id'], original_sha256=r['source_sha256'],
                    source_characters=len(r['text']), role_fields={k:dict(sha256=th(v), characters=len(v),
                    messages=sum(s['role']==k for s in spans)) for k,v in fields.items()}, original_blocks=spans))
        setup = time.perf_counter() - started; scores = {}; elapsed = {}; query = expression(case['question'])
        for field in ['whole', 'user', 'assistant']:
            t = time.perf_counter()
            scores[field] = {rows[i-1]['id']: -float(z) for i,z in db.execute(f'select rowid,bm25({field})from {field} where {field} match ?', (query,))} if query else {}
            elapsed[field] = time.perf_counter() - t
        # Keep role nonmatches explicit, preserving a distinction from low scores.
        components = [dict(source_id=r['id'], whole=scores['whole'].get(r['id'],0),
             user=scores['user'].get(r['id'],0), assistant=scores['assistant'].get(r['id'],0),
             whole_hit=r['id'] in scores['whole'], user_hit=r['id'] in scores['user'], assistant_hit=r['id'] in scores['assistant']) for r in rows]
        assert set(scores['whole']) == set(scores['user']) | set(scores['assistant'])
        assert all(math.isfinite(v) and v >= 0 for c in components for v in [c['whole'],c['user'],c['assistant']])
        orders = {}
        for arm in ARMS:
            values = {c['source_id']: c['whole'] if arm=='whole' else
                      ((.7*c['user']+.3*c['assistant']) if arm=='split70' else (.5*c['user']+.5*c['assistant']))
                      for c in components if c['whole_hit']}
            orders[arm] = [dict(source_id=s,score=values[s]) for s in sorted(values,key=lambda s:(-values[s],s))]
        parent = read(ROOT / case['parent_rankings'])
        expected = parent['native']['native']['bm25'] if 'corpus' in case else parent['native']['bm25']
        assert [x['source_id'] for x in orders['whole'][:10]] == [x['source_id'] for x in expected], case['id']
        delta = max(abs(a['score']-b['score']) for a,b in zip(orders['whole'][:10],expected))
        assert delta < 1e-10, (case['id'], delta)
        return dict(case_id=case['id'], cohort=case['cohort'], query=case['question'], clock=case['clock'],
                    expression=query, source_count=len(rows), source_receipts=receipts, components=components, rankings=orders,
                    original_control_top10_equal=True, original_max_score_difference=delta,
                    timing=dict(index_build_seconds=setup, field_search_seconds=elapsed))
    finally: db.close()


def rank():
    guard(); folder = HERE / 'rankings'; folder.mkdir(exist_ok=False)
    for c in read(HERE / 'runtime.json'):
        save(folder / (c['id'] + '.json'), compute(c))
    save(folder / 'complete.json', dict(cases=57, sqlite_version=sqlite3.sqlite_version,
         files={p.name:sha(p) for p in sorted(folder.glob('*.json'))}, llm_calls=0, embedding_calls=0))
    print(json.dumps(dict(ranked=57, arms=3, original_top10_replays=57, llm_calls=0, embeddings=0)))


def report(check=False):
    guard(); complete = read(HERE / 'rankings/complete.json')
    assert len(complete['files']) == 57
    for rel,h in complete['files'].items(): assert sha(HERE / 'rankings' / rel) == h
    gold = {c['id']:c for c in read(HERE / 'evaluation.json')}; cases = []
    for c in read(HERE / 'runtime.json'):
        r = read(HERE / 'rankings' / (c['id'] + '.json')); ev = gold[c['id']]; refs = set(ev['refs'])
        assert refs <= {x['source_id'] for x in r['source_receipts']}
        if check:
            replay = compute(c)
            for key in ['rankings', 'components', 'source_receipts', 'query', 'expression']:
                assert replay[key] == r[key], (c['id'],key)
        cells = {}
        for arm in ARMS:
            cells[arm] = []
            for n in range(1,6):
                chosen = {x['source_id'] for x in r['rankings'][arm][:n]}; hits = len(chosen & refs)
                atoms = ev['requirements']
                atom_hits = None if atoms is None else sum(any(w['source_id'] in chosen for w in a['witnesses']) for a in atoms)
                cells[arm].append(dict(n=n, selected=sorted(chosen), all_reference=refs<=chosen, any_reference=bool(hits),
                    covered_references=hits,total_references=len(refs), missing_references=sorted(refs-chosen),
                    atoms_covered=atom_hits, all_atoms=None if atoms is None else atom_hits==len(atoms)))
        cases.append(dict(case_id=c['id'],cohort=c['cohort'],type=ev['type'],question=c['question'],
            refs=sorted(refs), cells=cells, target_ranks={s:{a:next(i+1 for i,v in enumerate(r['rankings'][a]) if v['source_id']==s) if any(v['source_id']==s for v in r['rankings'][a]) else None for a in ARMS}for s in sorted(refs)}))
    summaries = []; paired = []
    for cohort in ['original25','previous_new32']:
        group = [c for c in cases if c['cohort']==cohort]
        for label,subset in [('all',group)]+[(t,[c for c in group if c['type']==t])for t in sorted({c['type']for c in group})]:
            for arm in ARMS:
                for n in range(1,6):
                    cells = [c['cells'][arm][n-1] for c in subset]
                    summaries.append(dict(cohort=cohort,slice=label,arm=arm,n=n,cases=len(subset),all_reference=sum(x['all_reference']for x in cells),
                        any_reference=sum(x['any_reference']for x in cells),covered_references=sum(x['covered_references']for x in cells),total_references=sum(x['total_references']for x in cells),
                        all_atoms=None if cohort!='original25' else sum(x['all_atoms']for x in cells)))
        for arm in ARMS[1:]:
            for n in range(1,6):
                better = [c['case_id']for c in group if c['cells'][arm][n-1]['all_reference']and not c['cells']['whole'][n-1]['all_reference']]
                worse = [c['case_id']for c in group if c['cells']['whole'][n-1]['all_reference']and not c['cells'][arm][n-1]['all_reference']]
                paired.append(dict(cohort=cohort,arm=arm,n=n,improved=better,regressed=worse))
    out = dict(id='SMM-BM25-RW001',protocol_sha256=sha(HERE/'protocol.json'),cases=cases,summaries=summaries,paired=paired,
               llm_calls=0,embedding_calls=0,scope='Previously used57 questions, no pooled new-generalization claim.')
    stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=list(summaries[0]),lineterminator='\n');w.writeheader();w.writerows(summaries)
    files={'results.json':dump(out),'summary.csv':stream.getvalue()}
    for name,text in files.items():
        p=HERE/name
        if check:assert p.read_bytes()==text.encode(),name
        else:
            with p.open('x')as f:f.write(text)
    print(json.dumps(dict(passed=True,check=check,cases=57,original_replays=57,role_replays=57 if check else 0,llm_calls=0,embeddings=0)))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['freeze','rank','score','check']);a=p.parse_args()
    if a.mode=='freeze':freeze()
    elif a.mode=='rank':rank()
    else:report(a.mode=='check')


if __name__=='__main__':main()
