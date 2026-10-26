"""Verify source-bound inference receipts and summarize extraction quality/cost."""
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from extract import SCHEMA,SYSTEM,digest,payload,sources,validate

def read(p):return json.loads(Path(p).read_text())

def main():
    plan=read(HERE/'plan.json');src=sources();counts=[];times=[];turn_ratios=[];usages=[];adjudicated=[]
    assert len(plan['source_ids'])==272 and plan['model']=='gpt-6-luna' and plan['effort']=='high'
    assert plan['system_sha256']==hashlib.sha256(SYSTEM.encode()).hexdigest()
    assert plan['schema_sha256']==digest(SCHEMA)
    assert plan['protocol_sha256']==hashlib.sha256((HERE/'PROTOCOL.md').read_bytes()).hexdigest()
    for sid in plan['source_ids']:
        r=read(HERE/'results'/(sid+'.json'))
        inp=payload(sid,src[sid]);req={'system':SYSTEM,'payload':inp,'schema':SCHEMA,'model':'gpt-6-luna','effort':'high'}
        assert r['source_id']==sid and r['source_sha256']==src[sid]['source_sha256']==plan['source_hashes'][sid]
        assert r['input']==inp and r['request_sha256']==digest(req)
        assert r['model']=='gpt-6-luna' and r['effort']=='high'
        m=r['metrics'];assert m['selected_model']=='gpt-6-luna' and m['selected_provider']=='openai' and m['tool_calls']==0
        if r['error']:
            a=read(HERE/'adjudications'/(sid+'.json'))
            assert a['raw_output_sha256']==digest(r['output'])
            out=a['effective_output'];adjudicated.append({'source_id':sid,'error':r['error'],'excess':a.get('excess',[]),'short':a.get('short',[])})
            validate(out,inp,min_keywords=2)
        else:
            out=r['output'];validate(out,inp)
        branches=out['branches'];counts.append(len(branches));times.append(m['seconds']);usages.append(m['usage'])
        turns={x['turn']for x in inp['turns']};hit={t for b in branches for t in b['turns']}
        assert hit<=turns
        turn_ratios.append(len(hit)/len(turns))
    result={'source_count':len(counts),'branch_count':sum(counts),'branch_per_source_mean':statistics.mean(counts),
            'branch_per_source_min':min(counts),'branch_per_source_max':max(counts),
            'turn_reference_coverage_mean':statistics.mean(turn_ratios),
            'inference_seconds_sum':sum(times),'inference_seconds_mean':statistics.mean(times),
            'input_tokens_sum':sum(u['prompt_tokens']for u in usages),
            'output_tokens_sum':sum(u['completion_tokens']for u in usages),
            'reasoning_tokens_sum':sum(u['reasoning_tokens']for u in usages),
            'adjudicated':adjudicated,'all_source_hashes_verified':True,
            'all_requests_reconstructed':True,'all_selected_models_verified':True}
    (HERE/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
