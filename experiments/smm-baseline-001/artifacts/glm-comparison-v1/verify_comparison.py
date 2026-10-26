"""Offline verification of the GLM first-attempt comparison; no model calls."""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import harness as h

def verify():
    if not __debug__:raise ValueError('Run without -O')
    base=h.verify();checks=base['checks'];folder=ROOT/'artifacts/glm-comparison-v1'
    protocol=h.read(folder/'protocol.json');ratings=h.read(folder/'manual-review-decisions.json')
    assert h.file_hash(ROOT/'manifest.json')==protocol['manifest_sha256'];checks+=1
    assert h.file_hash(ROOT/'http_transport.py')==protocol['http_transport_sha256'];checks+=1
    assert ratings['status']=='completed'and len(ratings['rows'])==98;checks+=1
    expected={('glm-5.3-flash','oracle_answer','P25'),('glm-5.3','oracle_answer','P06')}
    actual=set();total=success=0;summary={}
    for model,label in zip(protocol['models'],protocol['run_ids'],strict=True):
        run=ROOT/'runs'/label;meta=h.read(run/'run.json')
        assert meta['model']==model and meta['effort']=='low'and meta['base_url']==protocol['endpoint'];checks+=1
        assert meta['response_format']=='json_schema'and meta['backend']=='chat';checks+=1
        assert meta['case_ids']==protocol['case_ids']and meta['tasks']==protocol['tasks'];checks+=1
        records=[p for p in(run/'records').glob('*/*.json')if not p.name.endswith('.started.json')]
        assert len(records)==len(list((run/'records').glob('*/*.started.json')))==75;checks+=1
        start=h.read(run/'continuation-start.json');done=h.read(run/'continuation-completion.json')
        assert done['status']=='completed'and done['original_records_unchanged'];checks+=1
        assert h.read(run/'completion.json')['status']=='failed';checks+=1
        for rel,value in start['original_record_hashes'].items():
            assert h.file_hash(run/rel)==value;checks+=1
        assert done['attempted']==len(start['pending_pairs'])==done['pending_before'];checks+=1
        pending={(p['task'],p['case_id'])for p in start['pending_pairs']}
        for p in records:
            r=h.read(p);task=p.parent.name;cid=p.stem;req=h.request(task,cid)
            assert r['task']==task and r['case_id']==cid and r['model']==model;checks+=1
            assert r['request_sha256']==protocol['request_sha256'][task+'/'+cid]==req['request_sha256'];checks+=1
            assert h.digest(req['request'])==req['request_sha256'];checks+=1
            assert bool(r.get('continuation'))==((task,cid)in pending);checks+=1
            if r['error']:
                actual.add((model,task,cid));assert r['output']is None and r['error']['type']=='TimeoutError';checks+=1
            else:
                metrics=r['metrics'];assert metrics['selected_model']==metrics['response_model']==model;checks+=1
                assert metrics['tool_calls']==0 and metrics['transport_profile']==meta['transport_profile'];checks+=1
                assert h.mechanical(task,cid,r['output'])==r['mechanical'];checks+=1
                if task!='candidate_select':
                    review=next(x for x in ratings['rows']if(x['model'],x['task'],x['case_id'])==(model,task,cid))
                    assert review['response_sha256']==h.digest(r['output'])and review['request_sha256']==req['request_sha256'];checks+=1
                success+=1
            total+=1
        score=h.score_run(label);assert score['full_suite'];checks+=1
        assert all(v['review_complete']for v in score['summary'].values());checks+=1
        summary[model]=score['summary']
    assert actual==expected and total==150 and success==148;checks+=1
    assert tuple(summary['glm-5.3-flash'][t]['primary_correct']for t in h.TASKS)==(23,25,21);checks+=1
    assert tuple(summary['glm-5.3'][t]['primary_correct']for t in h.TASKS)==(20,24,21);checks+=1
    assert summary['glm-5.3-flash']['candidate_select']['pending_source_labels']==summary['glm-5.3']['candidate_select']['pending_source_labels']==0;checks+=1
    return dict(experiment_id='SMM-B001',phase='glm-comparison-v1',passed=True,checks=checks,
        benchmark_attempts=total,successful_generations=success,timeout_first_attempts=[dict(model=m,task=t,case_id=c)for m,t,c in sorted(actual)],
        semantic_answer_reviews=98,selection_outputs=50,original_baseline_unchanged=True,summary=summary,
        scope='Mechanical input/output/first-attempt/rating bindings. Semantic labels remain parent-researcher review, not external blind truth.')

if __name__=='__main__':print(h.compact(verify()))
