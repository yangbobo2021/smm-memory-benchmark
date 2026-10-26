"""Transfer previously fixed input and source-view variants to official M.

All variants existed before this M comparison; no variant chosen by M labels.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
REPO=Path('/Users/boboyang/work/smm-memory-benchmark')
BASE=REPO/'experiments/smm-bm25-scale-1000-002'
QI=REPO/'experiments/smm-scale-query-1000-001'
sys.path.insert(0,str(BASE))
import score
from score_m import body
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fusion(a,b,k=60):
    scores={};a_ids={r['source_id'] for r in a};b_ids={r['source_id'] for r in b}
    for rank,row in enumerate(a,1):scores[row['source_id']]=scores.get(row['source_id'],0)+1/(k+rank)
    for rank,row in enumerate(b,1):scores[row['source_id']]=scores.get(row['source_id'],0)+1/(k+rank)
    return [{'source_id':sid,'score':v} for sid,v in sorted(scores.items(),key=lambda p:(-p[1],p[0]))]
def main():
    out=HERE/'transfer-probe';out.mkdir(exist_ok=True)
    protocol={'id':'SMM-M-TRANSFER-001','status':'development transfer; fixed variants predate M comparison',
      'official_m_protocol_sha256':sha(HERE/'protocol-v2.json'),
      'prior_query_protocol_sha256':sha(QI/'protocol.json'),
      'code_sha256':sha(Path(__file__)),
      'variants':['raw-whole','prior-authored-whole','prior-stopword-whole','raw-user-only','RRF60(raw-whole,raw-user-only)'],
      'warning':'prior authored queries are hand-written, previously evaluated, not deployable Agent outputs or blind validation'}
    pp=out/'protocol.json'
    if pp.exists():assert load(pp)==protocol
    else:pp.write_text(json.dumps(protocol,indent=2)+'\n')
    queries={x['id']:x for x in load(QI/'protocol.json')['cases']}
    results=[]
    for cid in sorted(x.stem for x in (HERE/'results').glob('*.json')):
        path=out/'results'/f'{cid}.json'
        if path.exists():results.append(load(path));continue
        item=load(HERE/'cases'/f'{cid}.json'); prior=load(HERE/'results'/f'{cid}.json')
        unique=[];texts={};user={};canonical={};alias={}
        for sid,turns in zip(item['haystack_session_ids'],item['haystack_sessions']):
            b=body(turns);h=hashlib.sha256(b.encode()).hexdigest()
            if h not in canonical:
                canonical[h]=sid;unique.append(sid);texts[sid]=b
                user[sid]='\n\n'.join('USER:\n'+str(t['content']) for t in turns if t['role'].lower()=='user')
            alias[sid]=canonical[h]
        refs=list(dict.fromkeys(alias[sid] for sid in item['answer_session_ids']))
        q=queries[cid]
        ranks={}
        ranks['raw-whole']=score.rank(unique,texts,item['question'])[0]
        assert score.measures(ranks['raw-whole'],refs)['reference_positions']==prior['official_m']['reference_positions']
        ranks['prior-authored-whole']=score.rank(unique,texts,q['authored_query'])[0]
        ranks['prior-stopword-whole']=score.rank(unique,texts,q['stopword_query'])[0]
        ranks['raw-user-only']=score.rank(unique,user,item['question'])[0]
        ranks['RRF60(raw-whole,raw-user-only)']=fusion(ranks['raw-whole'],ranks['raw-user-only'])
        result={'id':cid,'cohort':prior['cohort'],'type':prior['type'],'question':item['question'],
                'queries':{'authored':q['authored_query'],'stopword':q['stopword_query']},'variants':{}}
        for name,ranked in ranks.items():
            m=score.measures(ranked,refs)
            result['variants'][name]={'top5':m['top5'],'top10':m['top10'],'reference_positions':m['reference_positions'],
                                     'top10_ids':[r['source_id'] for r in ranked[:10]]}
        path.parent.mkdir(exist_ok=True)
        with path.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
        results.append(result)
    summary={'protocol_sha256':sha(pp),'questions':len(results),'cohorts':{}}
    for cohort in ['P25','L32','all57']:
        arr=results if cohort=='all57' else [r for r in results if r['cohort']==cohort]
        d={'questions':len(arr)}
        for name in protocol['variants']:
            d[name]={}
            for n in (5,10):
                key=f'top{n}'
                d[name][key]={'all':sum(x['variants'][name][key]['all'] for x in arr),
                              'any':sum(x['variants'][name][key]['any'] for x in arr),
                              'reference_hits':sum(x['variants'][name][key]['reference_count'] for x in arr),
                              'gains':[x['id'] for x in arr if not x['variants']['raw-whole'][key]['all'] and x['variants'][name][key]['all']],
                              'losses':[x['id'] for x in arr if x['variants']['raw-whole'][key]['all'] and not x['variants'][name][key]['all']]}
        summary['cohorts'][cohort]=d
    target=out/'summary.json';assert not target.exists();target.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'complete':57,'summary':str(target)}))
if __name__=='__main__':main()
