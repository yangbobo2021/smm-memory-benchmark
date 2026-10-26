"""Rebuild both views and verify every selected source and reference count."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'experiments/smm-bm25-scale-1000-002'
sys.path.insert(0,str(BASE))
import score
from run import load,sha,user_text
def main():
    protocol=load(HERE/'protocol.json');assert len(protocol['cases'])==57
    base=load(BASE/'protocol.json');plans={x['id']:x for x in base['cases']}
    files={};whole={};user={}
    for cid in protocol['cases']:
        for sid in plans[cid]['original_source_ids']+plans[cid]['distractor_source_ids']:
            if sid in whole:continue
            meta=base['source_bank'][sid];name=meta['file'];assert not name.endswith('.jsonl')
            if name not in files:
                d=load(ROOT/name);files[name]={x['id']:x for x in d['records']} if 'records'in d else {d['id']:d}
            rec=files[name][sid]
            assert hashlib.sha256(rec['text'].encode()).hexdigest()==meta['source_sha256']
            whole[sid]=rec['text'];user[sid]=user_text(rec)
    total=0;any_count=0;all_count=0
    for cid in protocol['cases']:
        x=load(HERE/'results'/f'{cid}.json');plan=plans[cid]
        assert x['protocol_sha256']==sha(HERE/'protocol.json')
        ids=plan['original_source_ids']+plan['distractor_source_ids'];assert len(ids)==1000
        full=score.rank(ids,whole,x['question'])[0]
        usr=score.rank(ids,user,x['question'])[0]
        full_ids=[r['source_id'] for r in full];usr_ids=[r['source_id'] for r in usr]
        assert full_ids[:10]==x['raw']['top10_ids'],cid
        assert usr_ids[:10]==x['user']['top10_ids'],cid
        assert score.measures(full,x['reference_sources'])['reference_positions']==x['raw']['reference_positions'],cid
        assert score.measures(usr,x['reference_sources'])['reference_positions']==x['user']['reference_positions'],cid
        selected=list(dict.fromkeys(full_ids[:5]+usr_ids[:5]+full_ids[5:]))[:10]
        assert len(selected)==10 and selected==x['dual10']['selected_ids'],cid
        m=score.measures([{'source_id':sid} for sid in selected],x['reference_sources'])['top10']
        assert m==x['dual10']['top10'],cid
        total+=1;any_count+=m['any'];all_count+=m['all']
    summary=load(HERE/'summary.json')
    assert summary['cohorts']['all57']['questions']==total
    assert summary['cohorts']['all57']['dual10_any']==any_count
    assert summary['cohorts']['all57']['dual10_all']==all_count
    print(json.dumps({'verified':total,'all':all_count,'any':any_count,'numeric_replay':True}))
if __name__=='__main__':main()
