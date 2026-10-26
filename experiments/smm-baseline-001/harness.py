"""SMM-B001 portable evaluation. Python standard library only."""
import hashlib
import html
import json
import re
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TASKS=('oracle_answer','candidate_select','candidate_answer')

def read(p):return json.loads(Path(p).read_text())
def compact(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
def digest(value):return hashlib.sha256(compact(value).encode()).hexdigest()
def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_new(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x')as f:f.write(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def experiment():return read(ROOT/'experiment.json')
def cases():return {c['id']:c for c in read(ROOT/'data/cases.json')}
def request(task,cid):return read(ROOT/'requests'/task/(cid+'.json'))
def safe_id(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}',value):raise ValueError('Use a simple run/model label')
    return value
def run_path(label):
    safe_id(label)
    for folder in ['baselines','runs']:
        p=ROOT/folder/label
        if (p/'run.json').is_file():return p
    raise ValueError('Unknown run: '+label)


def schema_errors(value,schema,path='$'):
    errors=[];kind=schema.get('type')
    valid={'object':isinstance(value,dict),'array':isinstance(value,list),'string':isinstance(value,str),
        'integer':isinstance(value,int)and not isinstance(value,bool),'boolean':isinstance(value,bool),
        'number':isinstance(value,(int,float))and not isinstance(value,bool),'null':value is None}
    if kind and not valid.get(kind,False):return [path+': expected '+kind]
    if 'enum'in schema and value not in schema['enum']:errors.append(path+': illegal enum value')
    if kind=='object':
        for k in schema.get('required',[]):
            if k not in value:errors.append(path+': missing '+k)
        props=schema.get('properties',{})
        if schema.get('additionalProperties')is False:
            errors.extend(path+': unknown field '+k for k in value if k not in props)
        for k,v in value.items():
            if k in props:errors+=schema_errors(v,props[k],path+'.'+k)
    if kind=='array':
        if len(value)<schema.get('minItems',0)or len(value)>schema.get('maxItems',10**9):errors.append(path+': array length')
        for i,v in enumerate(value):errors+=schema_errors(v,schema.get('items',{}),path+f'[{i}]')
    if kind=='string'and len(value)<schema.get('minLength',0):errors.append(path+': string length')
    if kind in ['integer','number']:
        if value<schema.get('minimum',float('-inf'))or value>schema.get('maximum',float('inf')):errors.append(path+': range')
    return errors


def mechanical(task,cid,output):
    req=request(task,cid);errors=schema_errors(output,req['request']['schema'])
    result=dict(schema_valid=not errors,errors=errors,quote_valid=None,citations=[])
    if errors:return result
    selected=output['selected_sources']
    if len(selected)!=len(set(selected)):result['errors'].append('duplicate selected source')
    if task=='candidate_select':return result
    by={e['evidence_id']:e for e in req['ledger']};quote_errors=[]
    corpus=read(ROOT/cases()[cid]['corpus_file'])
    for i,claim in enumerate(output['claims']):
        for cite in claim['citations']:
            e=by.get(cite['evidence_id']);ok=bool(e and cite['quote']and cite['quote']in e['text'])
            if not ok:quote_errors.append(dict(claim_index=i,**cite,reason='not an exact contiguous original quote'))
            if e and e['source_id']not in selected:quote_errors.append(dict(claim_index=i,**cite,reason='cited source was not selected'))
            roles=[]
            if e:
                for p in corpus['structure'][e['original_source_id']]['parts']:
                    if cite['quote']in e['text'][p['start']:p['end']]:roles.append(p['role'])
            result['citations'].append(dict(claim_index=i,**cite,valid=ok,
                source_id=e['original_source_id']if e else None,possible_message_roles=sorted(set(roles)),
                source_date=e['received_at']if e else None))
    result['quote_valid']=not quote_errors
    result['quote_errors']=quote_errors
    return result


def review_map(path):
    p=path/'reviews.json'
    if not p.exists():return {},{}
    data=read(p)
    return {(r['task'],r['case_id']):r for r in data.get('answer_reviews',[])},\
           {(r['case_id'],r['source_id']):r for r in data.get('selection_extra_labels',[])}


def selection_score(cid,output,extra_reviews):
    c=cases()[cid];req=request('candidate_select',cid);by={e['source_id']:e for e in req['ledger']}
    selected={by[a]['original_source_id']for a in output['selected_sources']}
    refs=set(c['official_reference_sources']);known={a['id']for a in c['requirements']if any(w['source_id']in selected for w in a['witnesses'])}
    extended=set(known);pending=[];unrelated=[];labels=[]
    for sid in sorted(selected-refs):
        r=extra_reviews.get((cid,sid))
        if not r or r.get('label')not in ['direct','related_history','unrelated']:
            pending.append(sid);continue
        labels.append(r)
        if r['label']=='unrelated':unrelated.append(sid)
        else:
            e=next(e for e in req['ledger']if e['original_source_id']==sid)
            for w in r.get('alternative_evidence',[]):
                if w.get('atom_id')not in {a['id']for a in c['requirements']}or not w.get('quote')or w['quote']not in e['text']:
                    raise ValueError('Invalid reviewed alternative evidence: '+cid+'/'+sid)
                extended.add(w['atom_id'])
    needed={a['id']for a in c['requirements']}
    return dict(selected_source_count=len(selected),selected_original_sources=sorted(selected),
        baseline_sources_total=len(refs),baseline_sources_selected=len(selected&refs),all_baseline_sources_selected=refs<=selected,
        registered_atoms_total=len(needed),registered_atoms_selected=len(known),registered_complete=known==needed,
        reviewed_atoms_selected=len(extended),reviewed_complete=extended==needed,
        unrelated_count=len(unrelated),unrelated_sources=unrelated,pending_extra_sources=pending,
        selection_correct=None if pending else extended==needed and not unrelated,
        caveat='Registered evidence is a source-based proxy, not proof of answering or of actually quoting the evidence.')


def score_run(label):
    folder=run_path(label);meta=read(folder/'run.json');ratings,extra=review_map(folder);cs=cases();rows=[]
    if (folder/'run-manifest.json').exists():
        for rel,h in read(folder/'run-manifest.json')['files'].items():
            if file_hash(folder/rel)!=h:raise ValueError('Sealed run file changed: '+rel)
    totals={}
    for task in meta['tasks']:
        task_rows=[]
        for cid in meta['case_ids']:
            rp=folder/'records'/task/(cid+'.json');req=request(task,cid)
            row=dict(task=task,case_id=cid,ambiguous=cs[cid]['answer_ambiguity'],recorded=rp.exists())
            if not rp.exists():row.update(state='not_run',correct=None);task_rows.append(row);continue
            record=read(rp)
            if record.get('case_id')!=cid or record.get('task')!=task or record.get('model')!=meta['model']:
                raise ValueError('Run/model/task record binding changed')
            if record['request_sha256']!=req['request_sha256']:raise ValueError('Request binding changed')
            if record.get('error')or record.get('output')is None:
                row.update(state='generation_error',error=record.get('error'),correct=False);task_rows.append(row);continue
            output=record['output'];m=mechanical(task,cid,output)
            row.update(output=output,mechanical=m,seconds=record.get('metrics',{}).get('seconds'))
            if not m['schema_valid']or m['errors']:
                row.update(state='format_error',correct=False);task_rows.append(row);continue
            if task=='candidate_select':
                s=selection_score(cid,output,extra);row.update(selection=s,correct=s['selection_correct'],state='needs_source_review'if s['pending_extra_sources']else'scored')
            else:
                rv=ratings.get((task,cid))
                if rv and(rv.get('response_sha256')!=digest(output)or rv.get('request_sha256')!=req['request_sha256']):raise ValueError('Review does not match actual response: '+task+'/'+cid)
                required=['official_reference_match']+([]if cs[cid]['answer_ambiguity']else['complete_answer','evidence_semantic_valid'])
                reviewed=rv and all(type(rv.get(k))is bool for k in required)
                row.update(review=rv,state='scored'if reviewed else'needs_semantic_review',
                    correct=rv.get('complete_answer')if reviewed and not cs[cid]['answer_ambiguity']else None)
            task_rows.append(row)
        completed=[r for r in task_rows if r['state']in ['scored','format_error','generation_error']]
        if task=='candidate_select':
            values=[r['selection']for r in task_rows if'selection'in r]
            ready=len(completed)==len(task_rows)
            totals[task]=dict(primary_correct=sum(r.get('correct')is True for r in task_rows)if ready else None,
                primary_denominator=len(task_rows),review_complete=ready,
                registered_evidence_complete=sum(s['registered_complete']for s in values),
                registered_evidence_atoms_selected=sum(s['registered_atoms_selected']for s in values),
                registered_evidence_atoms_total=sum(len(cs[cid]['requirements'])for cid in meta['case_ids']),
                selected_sources=sum(s['selected_source_count']for s in values),
                baseline_sources_selected=sum(s['baseline_sources_selected']for s in values),
                baseline_sources_total=sum(len(cs[cid]['official_reference_sources'])for cid in meta['case_ids']),
                all_baseline_sources_questions=sum(s['all_baseline_sources_selected']for s in values),
                unrelated_selected=sum(s['unrelated_count']for s in values),pending_source_labels=sum(len(s['pending_extra_sources'])for s in values),
                note='Unrelated selected / selected outputs; never call this a whole-corpus FPR.')
        else:
            clear=[r for r in task_rows if not r['ambiguous']];ready=all(r['state']in ['scored','format_error','generation_error']for r in clear)
            reference_ready=len(completed)==len(task_rows)
            totals[task]=dict(primary_correct=sum(r.get('correct')is True for r in clear)if ready else None,
                primary_denominator=len(clear),review_complete=ready,
                official_reference_match=sum(bool((r.get('review')or{}).get('official_reference_match'))for r in task_rows)if reference_ready else None,
                official_reference_denominator=len(task_rows),
                strict_supported_correct=sum(bool(r.get('correct'))and bool((r.get('review')or{}).get('evidence_semantic_valid'))and r.get('mechanical',{}).get('quote_valid')is True for r in clear)if ready else None,
                exact_quote_valid=sum(r.get('mechanical',{}).get('quote_valid')is True for r in task_rows),
                ambiguity_case_ids=[r['case_id']for r in task_rows if r['ambiguous']],
                note='Semantic review is required. A reference number, source ID, or valid quote alone is not correctness.')
        times=[r['seconds']for r in task_rows if isinstance(r.get('seconds'),(int,float))]
        totals[task]['median_model_seconds']=statistics.median(times)if times else None
        totals[task]['recorded']=sum(r['recorded']for r in task_rows)
        rows.extend(task_rows)
    return dict(experiment_id='SMM-B001',run_id=meta['run_id'],model=meta['model'],backend=meta['backend'],
        transport_profile=meta.get('transport_profile',meta.get('transport_wrapper')),
        review_file_sha256=file_hash(folder/'reviews.json')if(folder/'reviews.json').exists()else None,
        effort=meta.get('effort'),full_suite=set(meta['tasks'])==set(TASKS)and set(meta['case_ids'])==set(experiment()['case_ids'])and all(r['recorded']for r in rows),
        summary=totals,rows=rows,
        semantic_review='Imported baseline ratings are parent-researcher reviews, not external blind labels; new runs must be reviewed independently of desired ranking.')


def verify():
    if not __debug__:raise ValueError('Run without -O: integrity assertions must remain enabled')
    checked=0
    manifest=read(ROOT/'manifest.json')
    for rel,h in manifest['files'].items():
        path=ROOT/rel
        if path.is_symlink()or not path.is_file()or file_hash(path)!=h:raise ValueError('Frozen file mismatch: '+rel)
        checked+=1
    frozen_prefixes=tuple(manifest['frozen_roots'])
    actual={str(p.relative_to(ROOT))for p in ROOT.rglob('*')if p.is_file()and not p.is_symlink()and '__pycache__'not in p.parts
            and(str(p.relative_to(ROOT))in manifest['files']or str(p.relative_to(ROOT)).startswith(frozen_prefixes))}
    if actual!=set(manifest['files']):raise ValueError('Unlisted/missing frozen files')
    cs=cases();reference_audit=read(ROOT/'data/reference-sessions.json');source_audit={a['case_id']:a for a in reference_audit['cases']}
    for cid,c in cs.items():
        corpus=read(ROOT/c['corpus_file']);records={r['id']:r for r in corpus['records']}
        for r in records.values():
            assert hashlib.sha256(r['text'].encode()).hexdigest()==r['source_sha256'];checked+=1
            for p in corpus['structure'][r['id']]['parts']:
                assert 0<=p['start']<=p['end']<=len(r['text']);checked+=1
        frozen=read(ROOT/'data/retrieval'/(cid+'.json'))
        pool={x['source_id']for k in ['bm25','vector']for x in frozen['native']['native'][k][:5]}
        for task in TASKS:
            req=request(task,cid);assert digest(req['request'])==req['request_sha256'];checked+=1
            expected=set(c['official_reference_sources'])if task=='oracle_answer'else pool
            assert {e['original_source_id']for e in req['ledger']}==expected;checked+=1
            for shown,e in zip(req['request']['payload']['observed_evidence'],req['ledger'],strict=True):
                assert shown['text']==e['text']==records[e['original_source_id']]['text'];checked+=1
                assert shown['received_at']==e['received_at']==records[e['original_source_id']]['received_at']<=c['known_at'];checked+=1
                assert shown['complete_conversation']and not shown['omitted_before']and not shown['omitted_after'];checked+=1
        assert request('candidate_answer',cid)['request']['payload']==request('candidate_select',cid)['request']['payload'];checked+=1
        for s in source_audit[cid]['sessions']:
            raw='\n\n'.join(m['role'].upper()+':\n'+m['content']for m in s['messages'])
            assert raw==s['text']==records[s['source_id']]['text'];checked+=1
    baseline_summaries={}
    for model,key in [('gpt-6-luna','luna'),('gpt-6.1-sol','sol')]:
        folder=run_path(model)
        for task in TASKS:
            for cid in cs:
                record=read(folder/'records'/task/(cid+'.json'));raw=folder/record['raw_receipt']
                assert file_hash(raw)==record['raw_receipt_sha256'];checked+=1
                original=read(raw);assert record['output']==original['output']and record['metrics']==original['metrics'];checked+=1
                assert record['request_sha256']==request(task,cid)['request_sha256'];checked+=1
                if'reused_first_result'in record:
                    reused=ROOT/record['reused_first_result'];assert file_hash(reused)==record['reused_first_result_sha256'];checked+=1
                    assert read(reused)['output']==record['output'];checked+=1
        scores=score_run(model);baseline_summaries[model]=scores['summary']
        for task,n in experiment()['expected_primary'][key].items():assert scores['summary'][task]['primary_correct']==n;checked+=1
    return dict(passed=True,checks=checked,frozen_files=len(manifest['files']),baseline_summaries=baseline_summaries,
        scope='File/data/receipt/rating bindings and deterministic score replay, not independent semantic truth or repeated-model success.')


def report_html(scores):
    def esc(x):return html.escape(str(x))
    rows=''
    for s in scores:
        cells=[]
        for task in TASKS:
            m=s['summary'].get(task,{})
            cells.append('<td>'+esc(m.get('primary_correct','—'))+'/'+esc(m.get('primary_denominator','—'))+'</td>')
        rows+='<tr><td>'+esc(s['run_id'])+'</td>'+''.join(cells)+'</tr>'
    return '<!doctype html><html lang="zh"><meta charset="utf-8"><title>SMM-B001</title><style>body{font:16px/1.6 system-ui;max-width:1200px;margin:40px auto;padding:0 20px}td,th{border:1px solid #ccc;padding:10px}table{border-collapse:collapse}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>SMM-B001：完整对话模型基线</h1><p>主指标依次为：准确上下文完整回答/23明确题，混合Top5筛选成功/25题，混合Top5完整回答/23明确题。None表示尚未完成语义审阅，不是零分。</p><table><tr><th>模型运行</th><th>准确上下文回答</th><th>混合候选筛选</th><th>混合候选回答</th></tr>'+rows+'</table><p>固定25道已知公开英文正例；两道时间适用歧义另列，全25原参考对照始终保留。筛选不要求选齐冗余旧记录；无关误选分母是模型选中的段次。模型首次结果与评分记录分开保存。</p>'+''.join('<details><summary>'+esc(s['run_id'])+' 完整评分</summary><pre>'+esc(json.dumps(s,ensure_ascii=False,indent=2))+'</pre></details>'for s in scores)+'</html>'
