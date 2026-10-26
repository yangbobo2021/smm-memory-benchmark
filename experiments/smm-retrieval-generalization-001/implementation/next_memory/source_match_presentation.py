"""Common, source-only lexical/semantic snippets for already-ranked candidates.

Never ranks conversations, knows gold, calls a generative model or follows a
link. All coordinates refer to immutable original messages. Sidecar vectors
are exact fixed-model source chunks; candidate matching stays in native arms.
"""
import math,re,sqlite3
import numpy as np

# Generic English function words; these affect snippets, not native retrieval.
STOP=set('a an and are as at be been being but by can could did do does for from had has have how i if in into is it its me my of on or our should so than that the their them there these they this those to us was we were what when where which who why will with would you your'.split())

def terms(query):
    all_terms=list(dict.fromkeys(re.findall(r'[^\W_]+',query.casefold(),re.UNICODE)))
    return [t for t in all_terms if t not in STOP] or all_terms

def best_window(text,start,end,query,cap):
    """Pick a query-near contiguous original window; never stitch factual text."""
    if end-start<=cap:return start,end
    hits=[]
    for term in terms(query):
        hits.extend((m.start(),term)for m in re.finditer(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text[start:end],re.I))
    options={0,end-start-cap}
    options.update(max(0,min(end-start-cap,p-cap//3))for p,t in hits)
    def key(lo):
        matched={t for p,t in hits if lo<=p<lo+cap}
        return (sum(1+math.log1p(len(t))for t in matched),len(matched),-lo)
    lo=max(options,key=key)
    return start+lo,start+lo+cap

def matched_spans(record,chunks,query,query_vector,*,limit=800):
    """At most two distinct original windows, lexical and semantic, one source.

    Chunk offsets and raw text are checked even when vectors were reused. The
    two route ranks do not change the native candidate/conversation order.
    """
    if limit<2:raise ValueError('Snippet budget too small')
    text=record['text'];db=sqlite3.connect(':memory:')
    db.execute("create virtual table passages using fts5(text,tokenize='unicode61')")
    vectors=[]
    for i,row in enumerate(chunks):
        c=row['chunk'];a,b=c['start'],c['end']
        if c['source_id']!=record['id']or not 0<=a<b<=len(text)or text[a:b]!=c['text']:raise ValueError('Sidecar does not match original')
        v=np.asarray(row['vector'],dtype=np.float64)
        if v.shape!=(384,)or not np.isfinite(v).all():raise ValueError('Invalid source vector')
        db.execute('insert into passages(rowid,text)values(?,?)',(i+1,c['text']));vectors.append(v)
    if not chunks:db.close();return []
    q=np.asarray(query_vector,dtype=np.float64)
    if q.shape!=(384,)or not np.isfinite(q).all():raise ValueError('Invalid query vector')
    expr=' OR '.join('"'+t.replace('"','""')+'"'for t in terms(query))
    lexical=[int(i)-1 for i,z in db.execute('select rowid,bm25(passages)from passages where passages match ? order by bm25(passages),rowid',(expr,))]if expr else []
    db.close();scores=np.asarray(vectors)@q
    semantic=sorted(range(len(chunks)),key=lambda i:(-float(scores[i]),i))
    candidates=[]
    for depth in range(max(len(lexical),len(semantic))):
        for route,order in [('lexical',lexical),('semantic',semantic)]:
            if depth<len(order):candidates.append((route,depth+1,order[depth]))
    selected=[];remaining=limit
    for route,rank,i in candidates:
        c=chunks[i]['chunk'];cap=min(400,remaining)
        if cap<=0:break
        a,b=best_window(text,c['start'],c['end'],query,cap)
        if any(max(0,min(b,s['end'])-max(a,s['start']))>=min(b-a,s['end']-s['start'])*.5 for s in selected):continue
        selected.append(dict(start=a,end=b,route=route,route_rank=rank,chunk_id=c['id']))
        remaining-=b-a
        if len(selected)==2:break
    return selected

class SourceChunkSidecar:
    """Read-only same-model source coordinates/vectors, restricted to candidates."""
    def __init__(self,path):
        self.db=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)
        self.read_sources=[]
    def chunks(self,source_id):
        import json
        self.read_sources.append(source_id)
        return [dict(chunk=json.loads(c),vector=np.frombuffer(v,dtype=np.float32))for c,v in self.db.execute('select chunk_json,vector from chunk_meta where source_id=? order by rowid',(source_id,))]
    def close(self):self.db.close()

class MiniLMQueryEncoder:
    """Same224/32 normalized-window encoder as the prior shared gateway."""
    def __init__(self,cache):
        from fastembed import TextEmbedding
        from tokenizers import Tokenizer
        self.model=TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2',cache_dir=str(cache),threads=2)
        self.tokenizer=Tokenizer.from_str(self.model.model.tokenizer.to_str())
        self.tokenizer.no_truncation();self.tokenizer.no_padding()
    def encode(self,text):
        enc=self.tokenizer.encode(text,add_special_tokens=False);windows=[]
        if len(enc.ids)<=224:windows=[text or ' ']
        else:
            begin=0
            while begin<len(enc.ids):
                end=min(begin+224,len(enc.ids));a=0 if begin==0 else enc.offsets[begin][0];b=len(text)if end==len(enc.ids)else enc.offsets[end][0]
                windows.append(text[a:b])
                if end==len(enc.ids):break
                begin=end-32
        v=np.stack(list(self.model.embed(windows))).mean(axis=0);v/=np.linalg.norm(v)
        return v
