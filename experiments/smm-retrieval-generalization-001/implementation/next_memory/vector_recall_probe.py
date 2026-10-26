"""Experimental source-bound vector recall, without fact synthesis or ANN."""
import hashlib
import sqlite3
import time
import numpy as np
from .conversation_topics import lexical_expression


def chunks_for_source(source, parts, tokenizer, *, tokens=256, overlap=48):
    if not 0 <= overlap < tokens: raise ValueError('Invalid overlap')
    text=source['text']; output=[];pending=None
    def add(start,end):
        chunk=text[start:end]
        if not chunk:return
        output.append({'id':source['id']+f'-c{len(output):04d}','source_id':source['id'],
            'start':start,'end':end,'text':chunk,'source_sha256':hashlib.sha256(text.encode()).hexdigest(),
            'received_at':source['received_at']})
    def length(start,end):return len(tokenizer.encode(text[start:end],add_special_tokens=False).ids)
    previous=0
    for part in parts:
        start,end=previous,part['end'];previous=end
        if length(start,end)>tokens:
            if pending:add(*pending);pending=None
            offsets=tokenizer.encode(text[start:end],add_special_tokens=False).offsets
            begin=0
            while begin<len(offsets):
                stop=min(begin+tokens,len(offsets))
                a=0 if begin==0 else offsets[begin][0]
                b=len(text[start:end]) if stop==len(offsets) else offsets[stop][0]
                add(start+a,start+b)
                if stop==len(offsets):break
                begin=stop-overlap
        elif pending is None:pending=(start,end)
        elif length(pending[0],end)<=tokens:pending=(pending[0],end)
        else:add(*pending);pending=(start,end)
    if pending:add(*pending)
    if previous!=len(text):raise ValueError('Provider turns must span entire original')
    covered=0
    for row in output:
        if row['start']>covered:raise ValueError('Unindexed original gap')
        covered=max(covered,row['end'])
    if covered!=len(text):raise ValueError('Unindexed original suffix')
    return output


class LocalE5:
    def __init__(self, folder, *, threads=4):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        start=time.perf_counter()
        options=ort.SessionOptions();options.intra_op_num_threads=threads;options.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(folder/'onnx/model.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        self.tokenizer=Tokenizer.from_file(str(folder/'tokenizer.json'));self.tokenizer.no_truncation()
        self.tokenizer.enable_padding(pad_id=1,pad_token='<pad>')
        self.offset_tokenizer=Tokenizer.from_file(str(folder/'tokenizer.json'))
        self.offset_tokenizer.no_truncation();self.offset_tokenizer.no_padding()
        self.load_seconds=time.perf_counter()-start;self.calls=0;self.texts=0

    def encode(self,texts,*,kind):
        if kind not in ['query','passage']:raise ValueError('Explicit E5 input kind required')
        encodings=self.tokenizer.encode_batch([kind+': '+t for t in texts])
        if any(len(x.ids)>512 for x in encodings):raise ValueError('Input exceeds512; no silent truncation')
        ids=np.array([x.ids for x in encodings],dtype=np.int64)
        mask=np.array([x.attention_mask for x in encodings],dtype=np.int64)
        values={'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)}
        inputs={item.name:values[item.name] for item in self.session.get_inputs()}
        hidden=self.session.run(None,inputs)[0]
        active=mask.astype(np.float32)[...,None]
        pooled=(hidden*active).sum(axis=1)/active.sum(axis=1)
        pooled=pooled/np.linalg.norm(pooled,axis=1,keepdims=True)
        self.calls+=1;self.texts+=len(texts)
        if pooled.shape!=(len(texts),384) or not np.isfinite(pooled).all():raise ValueError('Invalid embeddings')
        return pooled.astype(np.float32)


def dense_rank(vectors,query,chunks,*,limit=20):
    matrix=np.asarray(vectors,dtype=np.float64);matrix=matrix/np.linalg.norm(matrix,axis=1,keepdims=True)
    q=np.asarray(query,dtype=np.float64);q=q/np.linalg.norm(q)
    sims=matrix@q;best={}
    for n,chunk in enumerate(chunks):
        value=round(float(sims[n]),6);sid=chunk['source_id']
        item={'source_id':sid,'score':value,'chunk_id':chunk['id'],'start':chunk['start'],'end':chunk['end']}
        if sid not in best or (-value,chunk['id'])<(-best[sid]['score'],best[sid]['chunk_id']):best[sid]=item
    return sorted(best.values(),key=lambda x:(-x['score'],x['source_id']))[:limit]


class LexicalControl:
    def __init__(self,path,records,chunks):
        self.db=sqlite3.connect(path)
        self.db.executescript('''
          create table source_meta(id text primary key);
          create table chunk_meta(id text primary key,source_id text);
          create virtual table body_fts using fts5(content,tokenize='porter unicode61');
          create virtual table chunk_fts using fts5(content,tokenize='porter unicode61');
        ''')
        with self.db:
            for r in records:
                cursor=self.db.execute('insert into source_meta values(?)',(r['id'],))
                self.db.execute('insert into body_fts(rowid,content) values(?,?)',(cursor.lastrowid,r['text']))
            for r in chunks:
                cursor=self.db.execute('insert into chunk_meta values(?,?)',(r['id'],r['source_id']))
                self.db.execute('insert into chunk_fts(rowid,content) values(?,?)',(cursor.lastrowid,r['text']))
        self.body_attempts=[]
        def authorizer(action,table,column,database,trigger):
            if action==sqlite3.SQLITE_READ and table in ['body_fts','chunk_fts','body_fts_content','chunk_fts_content'] and column in ['content','c0']:
                self.body_attempts.append([table,column]);return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.db.set_authorizer(authorizer)

    def search(self,question,*,chunked=False,limit=20):
        expr=lexical_expression(question)
        if not expr:return []
        if not chunked:
            return [r[0] for r in self.db.execute('select source_meta.id from body_fts join source_meta on source_meta.rowid=body_fts.rowid where body_fts match ? order by bm25(body_fts),source_meta.id limit ?',(expr,limit))]
        rows=self.db.execute('select chunk_meta.source_id,bm25(chunk_fts) from chunk_fts join chunk_meta on chunk_meta.rowid=chunk_fts.rowid where chunk_fts match ?',(expr,))
        best={}
        for sid,score in rows:best[sid]=min(best.get(sid,float('inf')),score)
        return sorted(best,key=lambda sid:(best[sid],sid))[:limit]

    def close(self):self.db.close()
