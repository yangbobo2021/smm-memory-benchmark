"""Branch-level BM25/vector retrieval, aggregated to complete conversations."""
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'experiments/smm-sufficiency-luna-001'))
from lab import sources

STOP=set('a an and are as at be been but by can could did do does for from had has have how i in into is it its of on or our she he they their them that the there these this those to was were what when where which who why with would you your'.split())

def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def norm(q):
    # FTS5's frozen Porter tokenizer stems both these terms and indexed text.
    # Keep dictionary-shaped words for MiniLM instead of embedding Porter fragments.
    return list(dict.fromkeys(w.lower() for w in re.findall(r"[A-Za-z0-9]+",q) if w.lower() not in STOP))

def bm25(case,entries,query):
    db=sqlite3.connect(':memory:')
    try:
        db.execute("create virtual table idx using fts5(text,tokenize='porter unicode61')")
        branch=[]
        for sid in case['source_ids']:
            for j,b in enumerate(entries[sid]):branch.append((sid,j,' '.join(b['keywords'])))
        db.executemany('insert into idx(rowid,text) values(?,?)',[(i+1,v[2])for i,v in enumerate(branch)])
        if not query:return []
        expr=' OR '.join('"'+t+'"' for t in query)
        rows=db.execute('select rowid,bm25(idx) from idx where idx match ?',(expr,)).fetchall()
        best={}
        for rid,value in rows:
            sid,j,_=branch[rid-1];score=-float(value)
            if sid not in best or score>best[sid]['score']:
                best[sid]={'source_id':sid,'branch_index':j,'score':score}
        return sorted(best.values(),key=lambda x:(-x['score'],x['source_id']))
    finally:db.close()

def whole_bm25(case,src,query):
    db=sqlite3.connect(':memory:')
    try:
        db.execute("create virtual table idx using fts5(text,tokenize='porter unicode61')")
        ids=case['source_ids']
        db.executemany('insert into idx(rowid,text) values(?,?)',[(i+1,src[s]['text'])for i,s in enumerate(ids)])
        if not query:return []
        expr=' OR '.join('"'+t+'"' for t in query)
        rows=db.execute('select rowid,bm25(idx) from idx where idx match ?',(expr,)).fetchall()
        return sorted(({'source_id':ids[rid-1],'score':-float(v)}for rid,v in rows),key=lambda x:(-x['score'],x['source_id']))
    finally:db.close()

def windows(text,tokenizer):
    enc=tokenizer.encode(text,add_special_tokens=False)
    if len(enc.ids)<=224:return [text or ' ']
    out=[];begin=0
    while begin<len(enc.ids):
        end=min(begin+224,len(enc.ids))
        a=0 if begin==0 else enc.offsets[begin][0]
        b=len(text) if end==len(enc.ids) else enc.offsets[end][0]
        out.append(text[a:b])
        if end==len(enc.ids):break
        begin=end-32
    return out

def covered(reqs, ids):
    found=set(ids)
    flags=[any(set(w)<=found for w in unit)for unit in reqs]
    return {'any':any(flags),'all':all(flags),'units':sum(flags),'total_units':len(flags)}

def main():
    import numpy as np
    from fastembed import TextEmbedding
    plan=read(HERE/'plan.json');assert plan['model']=='gpt-6-luna'and plan['effort']=='high'
    assert hashlib.sha256((HERE/'PROTOCOL.md').read_bytes()).hexdigest()==plan['protocol_sha256']
    assert hashlib.sha256((ROOT/'experiments/smm-sufficiency-luna-001/evaluation.json').read_bytes()).hexdigest()==plan['evaluation_sha256']
    src=sources();entries={};all_branches=[];texts=[]
    for sid in plan['source_ids']:
        r=read(HERE/'results'/(sid+'.json'))
        assert r['model']=='gpt-6-luna' and r['effort']=='high'
        assert r['source_sha256']==plan['source_hashes'][sid]==src[sid]['source_sha256']
        assert r['metrics']['selected_provider']=='openai'and r['metrics']['tool_calls']==0
        if r['error']:
            a=read(HERE/'adjudications'/(sid+'.json'))
            assert a['source_id']==sid and a['raw_output_sha256']==digest(r['output'])
            assert a['rule'] in {'first 12 keywords in any overlong branch',
                                 'first 12 keywords in overlong branches; retain two-keyword tiny branches'}
            output=a['effective_output']
        else:output=r['output']
        entries[sid]=output['branches']
        for j,b in enumerate(entries[sid]):
            all_branches.append((sid,j));texts.append(' '.join(b['keywords']))
    runtimes=read(ROOT/'experiments/smm-sufficiency-luna-001/runtime.json')
    cases=[c for c in runtimes if c['id']in plan['case_ids']]
    evals={x['id']:x for x in read(ROOT/'experiments/smm-sufficiency-luna-001/evaluation.json')}
    baseline=ROOT/'experiments/smm-query-input-001/rankings'
    cache=Path(os.environ.get('SMM_MINILM_CACHE',str(Path.home()/'.cache/smm-branch-keywords-001')))
    cache.mkdir(parents=True,exist_ok=True)
    t=time.monotonic();model=TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2',cache_dir=str(cache),threads=2)
    branch_vec=np.asarray(list(model.embed(texts)),dtype=np.float32)
    branch_vec/=np.linalg.norm(branch_vec,axis=1,keepdims=True)
    from tokenizers import Tokenizer
    tokenizer=Tokenizer.from_str(model.model.tokenizer.to_str())
    tokenizer.no_truncation();tokenizer.no_padding()
    window_texts=[];bounds={}
    for sid in plan['source_ids']:
        begin=len(window_texts);window_texts.extend(windows(src[sid]['text'],tokenizer));bounds[sid]=(begin,len(window_texts))
    window_vec=np.asarray(list(model.embed(window_texts)),dtype=np.float32)
    whole_vec={sid:window_vec[a:b].mean(axis=0)for sid,(a,b) in bounds.items()}
    whole_vec={sid:v/np.linalg.norm(v)for sid,v in whole_vec.items()}
    queries=[norm(c['question'])for c in cases]
    query_vec=np.asarray(list(model.embed([' '.join(q) or ' ' for q in queries])),dtype=np.float32)
    query_vec/=np.linalg.norm(query_vec,axis=1,keepdims=True)
    vector_seconds=time.monotonic()-t
    idx={b:i for i,b in enumerate(all_branches)}
    outcomes=[];unions=[];ranks={};started=time.monotonic()
    for qi,c in enumerate(cases):
        cid=c['id'];q=queries[qi]
        lexical=bm25(c,entries,q)
        whole_lexical=whole_bm25(c,src,q)
        sims=branch_vec@query_vec[qi]
        vector=[]
        for sid in c['source_ids']:
            z=max(((float(sims[idx[(sid,j)]]),j)for j in range(len(entries[sid]))),key=lambda x:x[0])
            vector.append({'source_id':sid,'branch_index':z[1],'score':z[0]})
        vector.sort(key=lambda x:(-x['score'],x['source_id']))
        whole_vector=sorted(({'source_id':sid,'score':float(whole_vec[sid]@query_vec[qi])}for sid in c['source_ids']),
                            key=lambda x:(-x['score'],x['source_id']))
        old=read(baseline/(cid+'.json'))['rankings']
        rank={'branch_bm25':lexical,'branch_vector':vector,
              'whole_bm25_normalized':whole_lexical,'whole_vector_normalized':whole_vector,
              'whole_bm25_raw':old['bm25_raw'],'whole_vector_raw':old['vector_raw'],
              'whole_bm25_rewritten':old['bm25_rewritten']}
        ranks[cid]={'id':cid,'question':c['question'],'normalized_terms':q,'rankings':rank}
        label=evals[cid]
        if not label['semantic_evaluable']:continue
        for route,rows in rank.items():
            for n in (1,2,3,4,5,10):
                cov=covered(label['requirements'],[x['source_id']for x in rows[:n]])
                outcomes.append({'id':cid,'route':route,'n':n,**cov,'candidates':min(n,len(rows))})
        for variant,left,right in [('historical_raw','whole_bm25_raw','whole_vector_raw'),
                                    ('normalized_whole','whole_bm25_normalized','whole_vector_normalized'),
                                    ('branch','branch_bm25','branch_vector')]:
            ids=list(dict.fromkeys([x['source_id']for x in rank[left][:5]]+[x['source_id']for x in rank[right][:5]]))
            unions.append({'id':cid,'variant':variant,'source_ids':ids,'candidates':len(ids),
                           **covered(label['requirements'],ids)})
    write(HERE/'rankings.json',ranks)
    write(HERE/'case-outcomes.json',outcomes)
    write(HERE/'union-outcomes.json',unions)
    summary=[]
    for route in ['whole_bm25_raw','whole_vector_raw','whole_bm25_rewritten','whole_bm25_normalized',
                  'whole_vector_normalized','branch_bm25','branch_vector']:
        for n in (1,2,3,4,5,10):
            a=[x for x in outcomes if x['route']==route and x['n']==n]
            summary.append({'route':route,'n':n,'cases':len(a),'any':sum(x['any']for x in a),
                            'all':sum(x['all']for x in a),'unit_hits':sum(x['units']for x in a),
                            'unit_total':sum(x['total_units']for x in a),
                            'mean_candidates':sum(x['candidates']for x in a)/len(a)})
    write(HERE/'summary.json',{'sources':len(entries),'branches':len(all_branches),'questions':len(cases),
                               'clear_questions':len({x['id']for x in outcomes}),
                               'embedding_seconds_with_model_load':vector_seconds,
                               'ranking_seconds':time.monotonic()-started,'rows':summary,
                               'unions':[{'variant':v,'cases':len(a),'any':sum(x['any']for x in a),
                                          'all':sum(x['all']for x in a),'unit_hits':sum(x['units']for x in a),
                                          'unit_total':sum(x['total_units']for x in a),
                                          'mean_candidates':sum(x['candidates']for x in a)/len(a)}
                                         for v in ['historical_raw','normalized_whole','branch']
                                         for a in [[x for x in unions if x['variant']==v]]]})
    print(json.dumps(read(HERE/'summary.json'),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
