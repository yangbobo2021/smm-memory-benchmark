"""BM25 Top5 -> sufficiency decision -> one excluded-source Top5 follow-up."""
import argparse
import collections
import concurrent.futures
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import threading
import time

from contract import SCHEMA, SYSTEM, validate

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
B = ROOT / 'experiments/smm-baseline-001'
G = ROOT / 'experiments/smm-retrieval-generalization-001'
Q = ROOT / 'experiments/smm-query-input-001'
MODEL = 'gpt-6-luna'
EFFORT = 'high'


def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x): return hashlib.sha256(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def put(p, x):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f: json.dump(x, f, ensure_ascii=False, indent=2); f.write('\n')
def terms(s): return list(dict.fromkeys(re.findall(r'[^\W_]+', s.casefold(), re.UNICODE)))[:128]
def expr(s): return ' OR '.join('"' + t + '"' for t in terms(s))


def sources():
    out = {}
    for rel in read(Q / 'source-files.json'):
        d = read(ROOT / rel)
        for r in d['records'] if 'records' in d else [d]:
            assert hashlib.sha256(r['text'].encode()).hexdigest() == r['source_sha256']
            if r['id'] in out: assert out[r['id']] == r
            out[r['id']] = r
    return out


def search(source_ids, query, src, exclude=()):
    # Score in the original full corpus; filtering does not change DF or BM25 scores.
    db = sqlite3.connect(':memory:')
    try:
        db.execute("create virtual table f using fts5(text,tokenize='unicode61')")
        db.executemany('insert into f(rowid,text)values(?,?)', [(i+1, src[s]['text']) for i, s in enumerate(source_ids)])
        raw = [dict(source_id=source_ids[i-1], score=-float(z)) for i,z in db.execute('select rowid,bm25(f)from f where f match ?', (expr(query),))] if expr(query) else []
        raw.sort(key=lambda x:(-x['score'],x['source_id']))
        excluded = set(exclude)
        return dict(all_ranked=raw, eligible_ranked=[r for r in raw if r['source_id'] not in excluded])
    finally: db.close()


def document_payload(c, ids, src, previous=None):
    obj = dict(question=c['question'], current_time=c['clock'], timezone='UTC',
               round=2 if previous is not None else 1,
               documents=[dict(document_id='D'+str(i+1), authored_at=src[s]['received_at'],
                               text=src[s]['text']) for i,s in enumerate(ids)])
    if previous is not None: obj['previous_assessment'] = previous
    return obj


def request(payload):
    body = dict(model=MODEL, effort=EFFORT, system=SYSTEM, payload=payload, schema=SCHEMA)
    return dict(request=body, request_sha256=digest(body))


def prepare():
    from dependency_annotations import AMBIGUOUS, OVERRIDES, NOTES
    assert not (HERE/'protocol.json').exists()
    src = sources(); base = read(Q/'baselines.json'); runtime=[]; evaluations=[]; bindings={}
    old={c['id']:c for c in read(B/'data/cases.json')}; new={c['id']:c for c in read(G/'data/cases.json')}
    for c in read(Q/'runtime.json'):
        cid=c['id']; ids=[x['source_id'] for x in base[cid]['bm25'][:5]]
        raw=search(c['source_ids'],c['question'],src)['all_ranked']
        assert raw[:10]==base[cid]['bm25'],cid
        assert len(ids)==5 and all(src[s]['received_at']<=c['clock'] for s in c['source_ids'])
        rt={k:c[k] for k in ['id','cohort','question','clock','source_ids']};rt['initial_source_ids']=ids
        runtime.append(rt); put(HERE/'requests/round1'/(cid+'.json'),request(document_payload(rt,ids,src)))
        label=old.get(cid) or new[cid]; refs=label['official_reference_sources']
        if cid in old:
            units=[[[s]for s in sorted({w['source_id']for w in a['witnesses']})]for a in label['requirements']]
        elif cid in OVERRIDES: units=OVERRIDES[cid]
        else: units=[[[s]]for s in refs]
        if cid=='L010':
            answer_sources=[s for s in refs if '#plankchallenge'in src[s]['text'].casefold()]
            assert answer_sources;units=[[[s]for s in answer_sources]]
        assert units and all(set(w)<=set(c['source_ids'])for u in units for w in u),(cid,units)
        covered=sum(any(set(w)<=set(ids)for w in u)for u in units)
        evaluations.append(dict(id=cid,official_refs=refs,requirements=units,
            dependency_interpretation='researcher pre-inference source-witness dependency audit',
            semantic_evaluable=cid not in AMBIGUOUS, ambiguity=AMBIGUOUS.get(cid),note=NOTES.get(cid),
            initial_official_complete=set(refs)<=set(ids),
            initial_dependency_complete=(covered==len(units))if cid not in AMBIGUOUS else None,
            original_reference_answer_evaluation_only=label.get('official_reference_answer_evaluation_only',label.get('reference_answer_for_evaluation_only'))))
    # Synthetic exclusion invariant, independent of benchmark labels or model output.
    fake={'a':{'text':'alpha alpha'},'b':{'text':'alpha'},'c':{'text':'beta'}}
    allrank=search(['a','b','c'],'alpha',fake); filtered=search(['a','b','c'],'alpha',fake,exclude=['a'])
    assert filtered['eligible_ranked']==[r for r in allrank['all_ranked']if r['source_id']!='a']
    put(HERE/'runtime.json',runtime);put(HERE/'evaluation.json',evaluations)
    put(HERE/'preflight.json',dict(passed=True,cases=257,raw_top10_exact_replays=257,
        official_complete=sum(e['initial_official_complete']for e in evaluations),
        official_incomplete=sum(not e['initial_official_complete']for e in evaluations),
        semantic_slices=dict(collections.Counter('ambiguous'if not e['semantic_evaluable']else'complete'if e['initial_dependency_complete']else'incomplete'for e in evaluations)),
        exclusion_preserves_corpus_scoring=True,no_truncation=True,model_calls=0,
        payload_characters=sum(len(read(HERE/'requests/round1'/(c['id']+'.json'))['request']['payload']['documents'][i]['text'])for c in runtime for i in range(5))))
    for rel in read(Q/'source-files.json'):bindings[rel]=sha(ROOT/rel)
    for p in [Q/'source-files.json',Q/'runtime.json',Q/'baselines.json',B/'data/cases.json',G/'data/cases.json',B/'codex_transport.py']:
        bindings[str(p.relative_to(ROOT))]=sha(p)
    for p in HERE.rglob('*'):
        if p.is_file()and'__pycache__'not in p.parts:bindings[str(p.relative_to(ROOT))]=sha(p)
    put(HERE/'protocol.json',dict(id='SMM-SF-LUNA001',model=MODEL,effort=EFFORT,cases=257,
        max_calls=514,initial_candidates=5,followup_candidates=5,followup_searches_max=1,
        initial_method='unchanged original-question full-conversation BM25',
        followup_method='same corpus and formula, Agent plain-word query, exclude first5 after scoring before Top5',
        pilot_cases=['P01','C037','L011','P07'],pilot_gate='plumbing and contract only; no accuracy-based rerolls',
        workers_max=1,application_retries=1,tool_calls_allowed=0,full_original_conversations=True,
        metrics=['P(stop|dependencies complete)','P(search|dependencies incomplete)',
                 'followup covers missing dependency units','followup completes all dependencies',
                 'P(stop after supplement|dependencies now complete)',
                 'P(search after supplement|dependencies still incomplete)',
                 'premature stopping','unnecessary search'],
        semantic_evaluation_scope='pre-inference audited source-witness units; all references retained as separate unchanged proxy; no answer accuracy claim',
        uncertain_annotation_cases_in_full_run=True,files=bindings))
    print(json.dumps(read(HERE/'preflight.json')),flush=True)


def guard():
    p=read(HERE/'protocol.json');assert p['model']==MODEL and p['effort']==EFFORT
    for rel,h in p['files'].items():assert sha(ROOT/rel)==h,rel
    return p


def invoke(server,cid,stage,req):
    folder=HERE/'records'/stage; dest=folder/(cid+'.json');marker=folder/(cid+'.started.json')
    if dest.exists():return read(dest)
    assert not marker.exists(),('Started call has no receipt; must retain and explicitly reconcile, never silently rerun',cid,stage)
    put(marker,dict(id=cid,stage=stage,request_sha256=req['request_sha256'],started=time.time()))
    output=None;metrics={};error=None;validation=None
    try:
        b=req['request'];output,metrics=server.infer(b['system'],b['payload'],effort=EFFORT,schema=b['schema'])
        assert metrics['selected_model']==MODEL and metrics['selected_provider']=='openai'and metrics['tool_calls']==0
        validation=validate(output,b['payload'])
    except Exception as exc:error=dict(type=type(exc).__name__,message=str(exc))
    record=dict(id=cid,stage=stage,model=MODEL,effort=EFFORT,request_sha256=req['request_sha256'],output=output,metrics=metrics,error=error,validation=validation)
    put(dest,record)
    print(json.dumps(dict(id=cid,stage=stage,decision=output.get('decision')if output else None,error=error,seconds=metrics.get('seconds'))),flush=True)
    return record


def run(args):
    guard();sys.path.insert(0,str(B));from codex_transport import CodexServer
    src=sources();runtime=read(HERE/'runtime.json');chosen=set(args.cases.split(','))if args.cases!='all'else{c['id']for c in runtime}
    assert chosen<={c['id']for c in runtime};assert 1<=args.workers<=2
    work=Path(args.work);work.mkdir(parents=True,exist_ok=True);stop=threading.Event()
    with CodexServer(work,MODEL,window_limit=0)as server:
        model=next(m for m in server.rpc('model/list',{'includeHidden':False})['data']if m['model']==MODEL)
        assert EFFORT in{x['reasoningEffort']for x in model['supportedReasoningEfforts']}
        def path(c):
            if stop.is_set():return
            cid=c['id'];first=invoke(server,cid,'round1',read(HERE/'requests/round1'/(cid+'.json')))
            if first['error']:
                if first['error']['type']not in ['AssertionError','ValueError']:stop.set()
                return
            o=first['output']
            if o['decision']=='sufficient':return
            target=HERE/'followups'/(cid+'.json')
            if target.exists():followup=read(target)
            else:
                t=time.perf_counter();ranked=search(c['source_ids'],o['next_query'],src,exclude=c['initial_source_ids']);seconds=time.perf_counter()-t
                hits=ranked['eligible_ranked'][:5];extra=[x['source_id']for x in hits]
                assert not set(extra)&set(c['initial_source_ids'])and len(extra)==len(set(extra))
                followup=dict(id=cid,query=o['next_query'],origin_response_sha256=digest(o),excluded_source_ids=c['initial_source_ids'],
                    returned=hits,complete_eligible_ranking=ranked['eligible_ranked'],full_corpus_ranking=ranked['all_ranked'],search_with_index_build_seconds=seconds,
                    visible_source_ids=c['initial_source_ids']+extra)
                put(target,followup)
            if not followup['returned']or stop.is_set():return
            rf=HERE/'requests/round2'/(cid+'.json')
            if not rf.exists():put(rf,request(document_payload(c,followup['visible_source_ids'],src,previous=o)))
            second=invoke(server,cid,'round2',read(rf))
            if second['error']and second['error']['type']not in ['AssertionError','ValueError']:stop.set()
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers)as pool:
            futures=[pool.submit(path,c)for c in runtime if c['id']in chosen]
            for f in concurrent.futures.as_completed(futures):f.result()
    records=list((HERE/'records/round1').glob('*.json'));records=[p for p in records if not p.name.endswith('.started.json')]
    total2=[p for p in (HERE/'records/round2').glob('*.json')if not p.name.endswith('.started.json')]
    print(json.dumps(dict(run_ended=True,round1=len(records),round2=len(total2),service_stop=stop.is_set(),chosen=len(chosen))),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run']);p.add_argument('--cases',default='all');p.add_argument('--workers',type=int,default=1);p.add_argument('--work');a=p.parse_args()
    if a.mode=='prepare':prepare()
    else:run(a)


if __name__=='__main__':main()
