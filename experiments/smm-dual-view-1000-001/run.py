"""Fixed ten-source lexical dual view: whole dialogue and all USER utterances."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys
import statistics

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'experiments/smm-bm25-scale-1000-002'
sys.path.insert(0,str(BASE))
import score

MARKER=re.compile(r'(?:^|\n\n)(USER|ASSISTANT):\n')
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read_new(p,d):
    p.parent.mkdir(exist_ok=True)
    with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
def user_text(record):
    raw=record['text'];parts=record.get('structure',{}).get('parts')
    if parts:
        values=[raw[x['start']:x['end']] for x in parts if x['role'].upper()=='USER']
    else:
        matches=list(MARKER.finditer(raw));assert matches and matches[0].start()==0
        values=[raw[m.end():matches[i+1].start() if i+1<len(matches) else len(raw)]
                for i,m in enumerate(matches) if m.group(1)=='USER']
    return '\n\n'.join('USER:\n'+x for x in values)
def main():
    protocol=load(HERE/'protocol.json')
    assert protocol['id']=='SMM-DUAL-VIEW-1000-001'
    assert sha(Path(__file__))==protocol['code_sha256']
    assert sha(BASE/'protocol.json')==protocol['base_protocol_sha256']
    base=load(BASE/'protocol.json'); plans={x['id']:x for x in base['cases']}
    oldcases={x['id']:x for x in load(ROOT/'experiments/smm-baseline-001/data/cases.json')}
    newcases={x['id']:x for x in load(ROOT/'experiments/smm-retrieval-generalization-001/data/cases.json')}
    files={};whole={};user={}
    needed={sid for cid in protocol['cases'] for sid in plans[cid]['original_source_ids']+plans[cid]['distractor_source_ids']}
    for sid in needed:
        meta=base['source_bank'][sid];name=meta['file'];assert not name.endswith('.jsonl')
        if name not in files:
            d=load(ROOT/name);files[name]={x['id']:x for x in d['records']} if 'records'in d else {d['id']:d}
        rec=files[name][sid];assert hashlib.sha256(rec['text'].encode()).hexdigest()==meta['source_sha256']
        whole[sid]=rec['text'];user[sid]=user_text(rec)
    results=[]
    for cid in protocol['cases']:
        path=HERE/'results'/f'{cid}.json'
        if path.exists():
            x=load(path);assert x['protocol_sha256']==sha(HERE/'protocol.json');results.append(x);continue
        plan=plans[cid];ids=plan['original_source_ids']+plan['distractor_source_ids'];assert len(ids)==len(set(ids))==1000
        case=oldcases[cid] if cid in oldcases else newcases[cid]
        ref=case['official_reference_sources'];raw,raw_build,raw_query=score.rank(ids,whole,case['question'])
        old=load(BASE/'results'/f'{cid}.json')
        assert score.measures(raw,ref)['reference_positions']==old['expanded']['reference_positions']
        usr,user_build,user_query=score.rank(ids,user,case['question'])
        selected=list(dict.fromkeys([r['source_id'] for r in raw[:5]]+[r['source_id'] for r in usr[:5]]+
                                        [r['source_id'] for r in raw[5:]]))[:10]
        selected_rows=[{'source_id':sid} for sid in selected]
        selected_m=score.measures(selected_rows,ref);user_m=score.measures(usr,ref)
        result={'id':cid,'cohort':plan['cohort'],'protocol_sha256':sha(HERE/'protocol.json'),
          'question':case['question'],'reference_sources':ref,
          'raw':{'top5':old['expanded']['top5'],'top10':old['expanded']['top10'],'reference_positions':old['expanded']['reference_positions'],
                 'top10_ids':[r['source_id'] for r in raw[:10]]},
          'user':{'top5':user_m['top5'],'top10':user_m['top10'],'reference_positions':user_m['reference_positions'],
                  'top10_ids':[r['source_id'] for r in usr[:10]]},
          'dual10':{'top10':selected_m['top10'],'selected_ids':selected},
          'seconds':{'raw_build':raw_build,'raw_query':raw_query,'user_build':user_build,'user_query':user_query}}
        read_new(path,result);results.append(result)
    summary={'id':protocol['id'],'protocol_sha256':sha(HERE/'protocol.json'),'cohorts':{}}
    for cohort in ['P25','L32','all57']:
        arr=results if cohort=='all57' else [x for x in results if x['cohort']==cohort]
        d={'questions':len(arr),'raw_top10_all':sum(x['raw']['top10']['all'] for x in arr),
           'user_top10_all':sum(x['user']['top10']['all'] for x in arr),
           'dual10_all':sum(x['dual10']['top10']['all'] for x in arr),
           'dual10_any':sum(x['dual10']['top10']['any'] for x in arr),
           'dual10_gains':[x['id'] for x in arr if not x['raw']['top10']['all'] and x['dual10']['top10']['all']],
           'dual10_losses':[x['id'] for x in arr if x['raw']['top10']['all'] and not x['dual10']['top10']['all']],
           'user_build_median_s':statistics.median(x['seconds']['user_build'] for x in arr),
           'user_query_median_s':statistics.median(x['seconds']['user_query'] for x in arr)}
        summary['cohorts'][cohort]=d
    read_new(HERE/'summary.json',summary);print(json.dumps(summary))
if __name__=='__main__':main()
