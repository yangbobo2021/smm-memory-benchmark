"""Frozen Luna-high branch extraction; resumable, one source per request."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'experiments/smm-sufficiency-luna-001'))
from lab import sources

MODEL = 'gpt-6-luna'
EFFORT = 'high'
SYSTEM = '''You identify retrieval entry points in complete conversations. For each distinct substantive discussion branch, return a short discriminative label, 3 to 12 canonical English keywords or short phrases, and the zero-based turn numbers supporting it. Cover side topics as well as the main topic, including specific people, places, projects, objects, actions, and time expressions when stated. Separate unrelated matters even when discussed in the same conversation. Group paraphrases of the same matter. Use dictionary forms for common words; retain proper names and their distinct referents. Do not infer unstated facts. Do not use generic umbrella keywords alone. Reply only with the specified JSON.'''
SCHEMA = {'type': 'object', 'additionalProperties': False, 'properties': {
    'branches': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': False,
        'properties': {'label': {'type': 'string'}, 'keywords': {'type': 'array', 'items': {'type': 'string'}},
                       'turns': {'type': 'array', 'items': {'type': 'integer'}}},
        'required': ['label', 'keywords', 'turns']}}}, 'required': ['branches']}

def read(path): return json.loads(Path(path).read_text())
def digest(obj): return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
def put(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f: json.dump(obj, f, ensure_ascii=False, indent=2); f.write('\n')

def plan():
    rt = read(ROOT / 'experiments/smm-sufficiency-luna-001/runtime.json')
    es = read(ROOT / 'experiments/smm-sufficiency-luna-001/evaluation.json')
    cases = [x for x in rt if x['cohort'] == 'locomo_random200']
    assert len(cases) == 200
    ids = sorted({s for c in cases for s in c['source_ids']})
    assert len(ids) == 272
    src = sources()
    names = sorted(ids, key=lambda s: (-len(src[s]['text']), s))
    pilot = [names[0], names[len(names)//3], names[2*len(names)//3], names[-1]]
    out = {'experiment': 'SMM-BR001', 'model': MODEL, 'effort': EFFORT,
           'cohort': 'locomo_random200', 'case_ids': [c['id'] for c in cases],
           'source_ids': ids, 'source_hashes': {s: src[s]['source_sha256'] for s in ids},
           'pilot_source_ids': pilot, 'system_sha256': hashlib.sha256(SYSTEM.encode()).hexdigest(),
           'schema_sha256': digest(SCHEMA), 'protocol_sha256': hashlib.sha256((HERE/'PROTOCOL.md').read_bytes()).hexdigest(),
           'evaluation_sha256': hashlib.sha256((ROOT/'experiments/smm-sufficiency-luna-001/evaluation.json').read_bytes()).hexdigest(),
           'question_count': len(cases), 'semantic_evaluable_count': sum(e['semantic_evaluable'] for e in es if e['id'] in {c['id'] for c in cases})}
    put(HERE/'plan.json', out)
    print(json.dumps({'sources': len(ids), 'cases': len(cases), 'pilot': pilot}))

def payload(sid, source):
    text = source['text']
    parts = source['structure']['parts']
    turns = [{'turn': p['turn'], 'role': p['role'], 'text': text[p['start']:p['end']]} for p in parts]
    assert ''.join(x['text'] for x in turns) or text
    return {'source_id': sid, 'source_sha256': source['source_sha256'], 'turns': turns}

def validate(out, inp, min_keywords=3):
    assert set(out) == {'branches'} and isinstance(out['branches'], list) and out['branches']
    available = {p['turn'] for p in inp['turns']}
    for b in out['branches']:
        assert set(b) == {'label', 'keywords', 'turns'}
        assert 2 <= len(b['label']) <= 120
        assert min_keywords <= len(b['keywords']) <= 12
        assert all(isinstance(k, str) and 1 <= len(k) <= 80 for k in b['keywords'])
        assert b['turns'] and set(b['turns']) <= available

def adjudicate_keyword_overflow(record):
    """Bound one mechanical response overrun without altering its raw receipt."""
    sid=record['source_id'];target=HERE/'adjudications'/(sid+'.json')
    if target.exists():
        a=read(target);assert a['raw_output_sha256']==digest(record['output'])
        validate(a['effective_output'],record['input'],min_keywords=2)
        return a['effective_output']
    assert record['error'] and record['error']['type']=='AssertionError' and record['output']
    import copy
    fixed=copy.deepcopy(record['output'])
    excess=[];short=[]
    for j,b in enumerate(fixed['branches']):
        if len(b['keywords'])>12:
            excess.append({'branch_index':j,'raw_count':len(b['keywords'])})
            b['keywords']=b['keywords'][:12]
        if len(b['keywords'])==2:short.append({'branch_index':j})
    assert excess or short
    validate(fixed,record['input'],min_keywords=2)
    put(target,{'source_id':sid,'rule':'first 12 keywords in overlong branches; retain two-keyword tiny branches',
                'raw_output_sha256':digest(record['output']),'excess':excess,'short':short,'effective_output':fixed})
    return fixed

def run(mode, work, start_index=0, end_index=None):
    plan = read(HERE/'plan.json')
    assert plan['model'] == MODEL and plan['effort'] == EFFORT
    assert plan['system_sha256'] == hashlib.sha256(SYSTEM.encode()).hexdigest()
    assert plan['schema_sha256'] == digest(SCHEMA)
    assert plan['protocol_sha256'] == hashlib.sha256((HERE/'PROTOCOL.md').read_bytes()).hexdigest()
    src = sources()
    assert all(src[s]['source_sha256'] == h for s,h in plan['source_hashes'].items())
    ids = plan['pilot_source_ids'] if mode == 'pilot' else plan['source_ids'][start_index:end_index]
    sys.path.insert(0, str(ROOT/'experiments/smm-baseline-001'))
    from codex_transport import CodexServer
    work = Path(work); work.mkdir(parents=True, exist_ok=True)
    with CodexServer(work, MODEL, window_limit=0) as server:
        model = next(m for m in server.rpc('model/list', {'includeHidden': False})['data'] if m['model'] == MODEL)
        assert EFFORT in {r['reasoningEffort'] for r in model['supportedReasoningEfforts']}
        for n,sid in enumerate(ids, 1):
            dest = HERE/'results'/(sid+'.json')
            if dest.exists():
                record = read(dest)
                if record.get('error'):adjudicate_keyword_overflow(record)
                continue
            inp = payload(sid, src[sid]); req = {'system': SYSTEM, 'payload': inp, 'schema': SCHEMA,
                                                  'model': MODEL, 'effort': EFFORT}
            marker = HERE/'attempts'/(sid+'.json')
            if marker.exists(): raise RuntimeError(f'Uncertain prior attempt {sid}; reconcile before retry')
            put(marker, {'source_id': sid, 'request_sha256': digest(req), 'started_at': time.time()})
            result = None; metrics = {}; error = None
            try:
                result,metrics = server.infer(SYSTEM, inp, effort=EFFORT, schema=SCHEMA)
                assert metrics['selected_model'] == MODEL and metrics['selected_provider'] == 'openai' and metrics['tool_calls'] == 0
                validate(result, inp)
            except Exception as exc:
                error = {'type': type(exc).__name__, 'message': str(exc)}
            put(dest, {'source_id': sid, 'source_sha256': inp['source_sha256'], 'request_sha256': digest(req),
                       'model': MODEL, 'effort': EFFORT, 'input': inp, 'output': result, 'metrics': metrics, 'error': error})
            print(json.dumps({'n': n, 'source_id': sid, 'branches': len(result['branches']) if result else None,
                              'seconds': metrics.get('seconds'), 'error': error}), flush=True)
            if error:
                record=read(dest)
                try:adjudicate_keyword_overflow(record)
                except Exception:raise RuntimeError(f'Extraction failed for {sid}: {error}')

if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode', choices=['plan','pilot','all']);ap.add_argument('--work',default=str(Path(os.environ.get('SMM_WORK_DIR',tempfile.gettempdir()))/'smm-branch-keywords-001'));ap.add_argument('--start-index',type=int,default=0);ap.add_argument('--end-index',type=int);args=ap.parse_args()
    if args.mode=='plan':plan()
    else:run(args.mode,args.work,args.start_index,args.end_index)
