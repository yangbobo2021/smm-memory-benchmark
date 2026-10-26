"""Existing source-BM25/max-chunk-cosine SMM, adapted to a fixed source budget.

No extracted facts, summaries, query rewriting, answer/gold access, or score
fusion. Two independent route orders are interleaved lexical-first, duplicates
retained until the frozen common source mapper sees them.
"""
import collections, hashlib, json, re, sqlite3, urllib.request
from pathlib import Path
import numpy as np
from tokenizers import Tokenizer
from .conversation_topics import lexical_expression
from .vector_recall_probe import chunks_for_source

MODEL='sentence-transformers/all-MiniLM-L6-v2'

def preview(record,chunk,query,limit=400):
    a,b=chunk['start'],chunk['end'];text=record['text'][a:b]
    terms=list(dict.fromkeys(re.findall(r'[^\W_]+',query.casefold(),re.UNICODE)))
    occurrences=[m.start() for term in sorted(terms,key=lambda t:(-len(t),t))
                 for m in list(re.finditer(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text,re.I))[:1]]
    if len(text)>limit:
        lo=max(0,(occurrences[0] if occurrences else 0)-limit//3);lo=min(lo,len(text)-limit)
        a+=lo;b=a+limit
    return dict(text=record['text'][a:b],start=a,end=b)

def interleave(bm25,vector,limit=10):
    return [dict(row,route=route,route_rank=i+1) for i in range(limit)
            for route,rows in [('bm25',bm25),('vector',vector)] if i<len(rows)
            for row in [rows[i]]]

class SMMControlIndex:
    def __init__(self,folder,tokenizer_path,gateway='http://127.0.0.1:15501/smm/v1/embeddings'):
        self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
        self.tokenizer=Tokenizer.from_file(str(tokenizer_path));self.tokenizer.no_truncation();self.tokenizer.no_padding()
        self.gateway=gateway;self.clients={};self.cache={}

    def db(self,namespace):
        if not re.fullmatch('[A-Za-z0-9_-]{1,100}',namespace):raise ValueError('Invalid isolated namespace')
        if namespace not in self.clients:
            db=sqlite3.connect(self.folder/(namespace+'.sqlite'))
            db.executescript('''
            create table if not exists source_meta(id text primary key,record_json text,structure_json text);
            create table if not exists chunk_meta(id text primary key,source_id text,chunk_json text,vector blob);
            create virtual table if not exists source_fts using fts5(text,tokenize='unicode61');
            create virtual table if not exists chunk_fts using fts5(text,tokenize='unicode61');
            ''');self.clients[namespace]=db
        return self.clients[namespace]

    def embed(self,texts):
        data=json.dumps(dict(model=MODEL,input=texts,encoding_format='float')).encode()
        request=urllib.request.Request(self.gateway,data,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=120)as response:raw=json.load(response)
        values=np.asarray([x['embedding']for x in sorted(raw['data'],key=lambda x:x['index'])],dtype=np.float32)
        if values.shape!=(len(texts),384) or not np.isfinite(values).all():raise ValueError('Invalid shared-model vectors')
        return values

    def ingest(self,namespace,record,structure):
        db=self.db(namespace)
        if db.execute('select 1 from source_meta where id=?',(record['id'],)).fetchone():raise ValueError('Refuse duplicate formal source write')
        if hashlib.sha256(record['text'].encode()).hexdigest()!=record['source_sha256']:raise ValueError('Original changed')
        chunks=chunks_for_source(record,structure['parts'],self.tokenizer,tokens=256,overlap=48)
        vectors=np.concatenate([self.embed([c['text']for c in chunks[i:i+16]])for i in range(0,len(chunks),16)])
        with db:
            row=db.execute('insert into source_meta values(?,?,?)',(record['id'],json.dumps(record),json.dumps(structure))).lastrowid
            db.execute('insert into source_fts(rowid,text)values(?,?)',(row,record['text']))
            for c,v in zip(chunks,vectors):
                row=db.execute('insert into chunk_meta values(?,?,?,?)',(c['id'],record['id'],json.dumps(c),v.tobytes())).lastrowid
                db.execute('insert into chunk_fts(rowid,text)values(?,?)',(row,c['text']))
        self.cache.pop(namespace,None)
        return dict(source_id=record['id'],source_sha256=record['source_sha256'],chunks=len(chunks),
                    original_chars=len(record['text']),embedding_model=MODEL,extraction_llm_calls=0)

    def corpus(self,namespace):
        if namespace not in self.cache:
            db=self.db(namespace)
            records={s:json.loads(r)for s,r in db.execute('select id,record_json from source_meta')}
            rows=list(db.execute('select rowid,chunk_json,vector from chunk_meta order by rowid'))
            chunks=[json.loads(c)for i,c,v in rows]
            vectors=np.asarray([np.frombuffer(v,dtype=np.float32)for i,c,v in rows],dtype=np.float64)
            self.cache[namespace]=(records,chunks,vectors,{i:c for (i,raw,v),c in zip(rows,chunks)})
        return self.cache[namespace]

    def search(self,namespace,query,clock):
        if not isinstance(query,str)or not query.strip()or len(query)>1500:raise ValueError('Bounded query required')
        records,chunks,vectors,byrow=self.corpus(namespace);db=self.db(namespace)
        allowed={s for s,r in records.items()if r['received_at']<=clock};expr=lexical_expression(query)
        lexical=[];best_bm={}
        if expr:
            lexical=[dict(source_id=s,score=-float(z))for s,z in db.execute('select source_meta.id,bm25(source_fts)from source_fts join source_meta on source_meta.rowid=source_fts.rowid where source_fts match ?',(expr,))if s in allowed]
            lexical.sort(key=lambda x:(-x['score'],x['source_id']))
            for i,z in db.execute('select rowid,bm25(chunk_fts)from chunk_fts where chunk_fts match ?order by bm25(chunk_fts),rowid',(expr,)):
                c=byrow[i]
                if c['source_id']in allowed:best_bm.setdefault(c['source_id'],c)
        q=self.embed([query])[0].astype(np.float64);sims=vectors@q;best_v={};scores={}
        for c,z in zip(chunks,sims):
            s=c['source_id'];z=float(z)
            if s in allowed and(s not in scores or z>scores[s]):scores[s]=z;best_v[s]=c
        semantic=[dict(source_id=s,score=scores[s])for s in sorted(scores,key=lambda s:(-scores[s],s))]
        items=[]
        for row in interleave(lexical,semantic):
            s=row['source_id'];c=(best_bm if row['route']=='bm25'else best_v).get(s)
            if c is None:raise ValueError('Matched source lacks route passage')
            window=preview(records[s],c,query)
            items.append(dict(item_id=row['route']+':'+c['id'],source_ids=[s],hint=window['text'],
                              kind=row['route']+'-original-match-index',score=row['score'],
                              metadata=dict(row,chunk_id=c['id'],start=window['start'],end=window['end'],source_sha256=records[s]['source_sha256'])))
        return dict(native=dict(bm25=lexical[:10],vector=semantic[:10],ordering='lexical-first round-robin; no score fusion'),items=items)

    def close(self):
        for db in self.clients.values():db.close()
