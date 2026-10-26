"""Offline verification of the effort ablation, receipts, and review bindings."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).resolve().parent))
import harness as h
from deepseek_high_transport import wire_body,body_hash

def verify(require_complete=True):
    if not __debug__:raise ValueError('Assertions required')
    phase=Path(__file__).resolve().parent;p=h.read(phase/'protocol.json');base=h.verify();checks=base['checks']
    assert h.file_hash(ROOT/'manifest.json')==p['frozen_manifest_sha256'];checks+=1
    for rel,want in p['code_sha256'].items():assert h.file_hash(ROOT/rel)==want;checks+=1
    for label,entry in p['paired_low_manifests'].items():
        # The inference-time protocol kept the original absolute audit path.
        # Resolve only the declared known run-manifest suffix in a relocated bundle;
        # do not read the original project or change the frozen protocol.
        stored=Path(entry['manifest'])
        rel=Path('manifest.json')if label in ['gpt-6-luna','gpt-6.1-sol']else Path('runs')/label/'run-manifest.json'
        assert (stored==rel)or(stored.is_absolute()and stored.parts[-len(rel.parts):]==rel.parts)
        assert h.file_hash(ROOT/rel)==entry['sha256'];checks+=1
        h.score_run(label);checks+=1  # Enforces every previously sealed low receipt hash.
    decisions=[]
    if (phase/'review-decisions.jsonl').exists():decisions=[json.loads(s)for s in(phase/'review-decisions.jsonl').read_text().splitlines()if s]
    d={(r['model'],r['case_id'],r['task']):r for r in decisions};assert len(d)==len(decisions);checks+=1
    outcomes=[]
    for model,spec in p['models'].items():
        folder=ROOT/'runs'/spec['run_id'];meta=h.read(folder/'run.json');done=h.read(folder/'completion.json')
        assert meta['model']==model and meta['effort']=='high'and meta['paired_low_run']==spec['low'];checks+=1
        assert meta['transport_profile']==spec['profile'];checks+=1
        assert meta['protocol_sha256']==h.file_hash(phase/'protocol.json');checks+=1
        assert done['no_retries']and done['calls']<=75;checks+=1
        if require_complete:assert done['calls']==75 and done['status']=='completed';checks+=1
        files=[f for f in(folder/'records').glob('*/*.json')if not f.name.endswith('.started.json')]
        starts=list((folder/'records').glob('*/*.started.json'));assert len(files)==len(starts)==done['calls'];checks+=1
        generated=0;errors=[]
        for f in files:
            r=h.read(f);t=f.parent.name;cid=f.stem;q=h.request(t,cid)
            assert r['case_id']==cid and r['task']==t and r['model']==model and r['effort']=='high';checks+=1
            assert r['request_sha256']==q['request_sha256']==p['request_sha256'][t+'/'+cid];checks+=1
            assert h.digest(q['request'])==q['request_sha256'];checks+=1
            assert h.read(f.with_suffix('.started.json'))['request_sha256']==q['request_sha256'];checks+=1
            if r.get('error'):assert r['output']is None;errors.append(dict(case_id=cid,task=t,error=r['error']));checks+=1;continue
            generated+=1;metrics=r['metrics']
            assert metrics['selected_model']==model and metrics['tool_calls']==0;checks+=1
            if spec['backend']=='codex':assert metrics['selected_provider']=='openai';checks+=1
            else:
                assert metrics['transport_profile']==spec['profile'];checks+=1
                assert metrics['response_model']==model;checks+=1
            assert r['mechanical']==h.mechanical(t,cid,r['output']);checks+=1
            if model=='deepseek-flash':
                body=wire_body(**q['request'])
                assert body_hash(body)==p['deepseek_high_wire_sha256'][t+'/'+cid]==metrics['wire_body_sha256'];checks+=1
                raw=h.read(folder/r['raw_response']);assert h.file_hash(folder/r['raw_response'])==r['raw_response_sha256'];checks+=1
                assert 'reasoning_content'not in raw and json.loads(raw['final_content'])==r['output'];checks+=1
            if t!='candidate_select':
                rv=d.get((model,cid,t));assert rv is not None;checks+=1
                assert rv['response_sha256']==h.digest(r['output'])and rv['request_sha256']==q['request_sha256'];checks+=1
                live=next(v for v in h.read(folder/'reviews.json')['answer_reviews']if(v['task'],v['case_id'])==(t,cid))
                for k in ['official_reference_match','complete_answer','evidence_semantic_valid','core_evidence_valid','note','response_sha256','request_sha256']:
                    assert live[k]==rv[k];checks+=1
        scores=h.score_run(spec['run_id']);assert all(s['review_complete']for s in scores['summary'].values());checks+=1
        if require_complete:assert scores['full_suite'];checks+=1
        outcomes.append(dict(model=model,calls=done['calls'],generated=generated,errors=errors,summary=scores['summary']))
    return dict(passed=True,checks=checks,frozen_files=base['frozen_files'],models=outcomes,formal_calls=sum(v['calls']for v in outcomes),new_model_calls_for_verification=0,scope='Receipt/input/effort/review bindings and frozen score replay; semantic labels are researcher review, not external blind truth.')

if __name__=='__main__':print(h.compact(verify()))
