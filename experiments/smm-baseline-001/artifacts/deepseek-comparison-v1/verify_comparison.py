"""Offline integrity verification for the DeepSeek SMM-B001 run."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import harness as h
from deepseek_transport import BASE_URL,MODEL,PROFILE,body_hash,wire_body

def verify():
    if not __debug__:raise ValueError('Run without -O')
    phase=Path(__file__).resolve().parent;p=h.read(phase/'protocol.json');base=h.verify();checks=base['checks']
    assert h.file_hash(ROOT/'manifest.json')==p['manifest_sha256'];checks+=1
    assert h.file_hash(phase/'deepseek_transport.py')==p['transport_sha256'];checks+=1
    assert h.file_hash(phase/'run_deepseek.py')==p['runner_sha256'];checks+=1
    folder=ROOT/'runs'/p['run_id'];meta=h.read(folder/'run.json');done=h.read(folder/'completion.json')
    assert meta['model']==MODEL and meta['base_url']==BASE_URL and meta['transport_profile']==PROFILE;checks+=1
    assert meta['effort']=='low'and meta['thinking']=='enabled'and meta['response_format']=='json_object';checks+=1
    assert meta['case_ids']==p['case_ids']and meta['tasks']==p['tasks'];checks+=1
    assert meta['protocol_sha256']==h.file_hash(phase/'protocol.json');checks+=1
    assert done['status']=='completed'and done['calls']==75 and done['no_retries'];checks+=1
    files=[f for f in(folder/'records').glob('*/*.json')if not f.name.endswith('.started.json')]
    assert len(files)==len(list((folder/'records').glob('*/*.started.json')))==75;checks+=1
    ratings=h.read(folder/'reviews.json');manual=h.read(phase/'manual-review-decisions.json')
    assert manual['status']=='completed';checks+=1
    generated=0;failures=[]
    for f in files:
        task=f.parent.name;cid=f.stem;req=h.request(task,cid);q=req['request'];r=h.read(f)
        assert r['model']==MODEL and r['case_id']==cid and r['task']==task;checks+=1
        assert r['request_sha256']==req['request_sha256']==p['request_sha256'][task+'/'+cid];checks+=1
        assert h.digest(q)==req['request_sha256'];checks+=1
        body=wire_body(q['system'],q['payload'],q['schema'])
        assert body_hash(body)==p['wire_body_sha256'][task+'/'+cid]==r['metrics']['wire_body_sha256'];checks+=1
        assert json.loads(body['messages'][1]['content'])==q['payload'];checks+=1
        assert body['messages'][0]['content'].startswith(q['system']);checks+=1
        raw=None
        if r.get('raw_response'):
            path=folder/r['raw_response'];assert h.file_hash(path)==r['raw_response_sha256'];checks+=1
            raw=h.read(path);assert'reasoning_content'not in raw;checks+=1
        if r['error']:
            failures.append(dict(task=task,case_id=cid,error=r['error']));assert r['output']is None;checks+=1
        else:
            generated+=1
            assert r['metrics']['selected_model']==r['metrics']['response_model']==MODEL;checks+=1
            assert r['metrics']['tool_calls']==0 and r['metrics']['transport_profile']==PROFILE;checks+=1
            assert raw['model']==MODEL and json.loads(raw['final_content'])==r['output'];checks+=1
            assert h.mechanical(task,cid,r['output'])==r['mechanical'];checks+=1
            if task!='candidate_select':
                rv=next(v for v in ratings['answer_reviews']if(v['task'],v['case_id'])==(task,cid))
                original=next(v for v in manual['rows']if(v['task'],v['case_id'])==(task,cid))
                assert rv['response_sha256']==h.digest(r['output'])and rv['request_sha256']==req['request_sha256'];checks+=1
                for key in ['complete_answer','official_reference_match','evidence_semantic_valid','core_evidence_valid','note']:
                    assert rv[key]==original[key];checks+=1
    score=h.score_run(p['run_id']);assert score['full_suite'];checks+=1
    assert all(v['review_complete']for v in score['summary'].values());checks+=1
    # Verify previous models' sealed results remain readable without changing their scores.
    previous={label:h.score_run(label)['summary']for label in ['gpt-6-luna','gpt-6.1-sol','glm-5.3-flash-low-first','glm-5.3-low-first']}
    return dict(experiment_id='SMM-B001',phase='deepseek-comparison-v1',passed=True,checks=checks,
        formal_attempts=75,generated_outputs=generated,failures=failures,summary=score['summary'],previous_summaries=previous,
        scope='Mechanical first-attempt/request/wire/output/review bindings. Semantic labels are parent-researcher review, not independent external truth.')

if __name__=='__main__':print(h.compact(verify()))
