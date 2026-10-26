"""Independent, fixed lexical arms. No labels are imported here."""
import collections
import math
import sqlite3
import time
from common import *

class Index:
    def __init__(self,rows,passages,src):
        t=time.perf_counter();self.ids=[r['id']for r in rows];self.db=sqlite3.connect(':memory:')
        db=self.db
        for name,tokenizer in [('whole','unicode61'),('stem','porter unicode61'),('local','unicode61')]:
            db.execute(f"create virtual table {name} using fts5(text,tokenize='{tokenizer}')")
        with db:
            for i,r in enumerate(rows,1):
                db.execute('insert into whole(rowid,text)values(?,?)',(i,r['text']))
                db.execute('insert into stem(rowid,text)values(?,?)',(i,r['text']))
            for i,p in enumerate(passages,1):db.execute('insert into local(rowid,text)values(?,?)',(i,chunk_text(p,src)))
        db.execute("create virtual table vocab using fts5vocab(whole,'instance')")
        self.positions=[collections.defaultdict(list)for _ in rows]
        self.lengths=[0]*len(rows)
        for term,doc,offset in db.execute('select term,doc,offset from vocab'):
            self.positions[doc-1][term].append(offset);self.lengths[doc-1]+=1
        self.df=collections.Counter(t for p in self.positions for t in p)
        self.avg=sum(self.lengths)/len(rows);self.passages=passages
        self.setup_seconds=time.perf_counter()-t

    def sql(self,name,question):
        q=expr(question)
        rows=list(self.db.execute(f'select rowid,bm25({name}) from {name} where {name} match ?',(q,)))if q else []
        if name!='local':return {self.ids[i-1]:-float(v)for i,v in rows}
        scores={}
        for i,v in rows:
            s=self.passages[i-1]['source_id'];scores[s]=max(scores.get(s,0),-float(v))
        return scores

    def custom(self,question,k1=1.2,b=.75,kind='bm25'):
        # Query terms here are already individual FTS phrases in the unchanged
        # lexer. Normalize diacritics through unicode61, exactly as the index.
        db=self.db;db.execute("create virtual table if not exists q using fts5(text,tokenize='unicode61')")
        db.execute('delete from q');db.execute('insert into q values(?)',(' '.join(terms(question)),))
        db.execute("create virtual table if not exists qv using fts5vocab(q,'row')")
        ts=[x[0]for x in db.execute('select term from qv')];n=len(self.ids);scores={}
        for sid,l,positions in zip(self.ids,self.lengths,self.positions):
            if not any(t in positions for t in ts):continue
            score=0.;norm=1-b+b*l/self.avg
            for term in ts:
                df=self.df[term]
                if not df:continue
                tf=len(positions.get(term,[]))
                if kind=='bm25plus':
                    idf=math.log((n+1)/df);score+=idf*(1+tf*(k1+1)/(tf+k1*norm))
                elif kind=='bm25l':
                    idf=math.log((n+1)/(df+.5));c=tf/norm
                    score+=idf*(k1+1)*(c+.5)/(k1+c+.5)
                elif tf:
                    idf=max(math.log((n-df+.5)/(df+.5)),1e-6)
                    score+=idf*tf*(k1+1)/(tf+k1*norm)
            scores[sid]=score
        return scores

    def features(self,question,base):
        ts=[t for t in terms(question)if t not in STOP]
        n=len(self.ids);weights={t:math.log1p((n-self.df[t]+.5)/(self.df[t]+.5))for t in ts if self.df[t]}
        total=sum(weights.values());out={};features={}
        for sid,positions in zip(self.ids,self.positions):
            if sid not in base:continue
            events=sorted((p,t)for t in weights for p in positions.get(t,[]))
            whole=sum(weights[t]for t in weights if t in positions)/total if total else 0
            active=collections.Counter();left=0;best=0.;value=0.
            for p,term in events:
                if not active[term]:value+=weights[term]
                active[term]+=1
                while p-events[left][0]>=64:
                    old=events[left][1];active[old]-=1
                    if not active[old]:value-=weights[old]
                    left+=1
                best=max(best,value)
            local=best/total if total else 0
            out[sid]=base[sid]*(1+.25*whole+.25*local)
            features[sid]=dict(coverage=whole,local_64token_coverage=local)
        return out,features

    def run(self,question):
        arms={};timings={}
        def calc(name,fn):
            t=time.perf_counter();values=fn();timings[name]=time.perf_counter()-t;arms[name]=ordered(values);return values
        base=calc('baseline',lambda:self.sql('whole',question))
        parity=self.custom(question)
        assert parity.keys()==base.keys()
        delta=max((abs(base[k]-parity[k])for k in base),default=0)
        assert delta<1e-9,delta
        calc('stem',lambda:self.sql('stem',question))
        t=time.perf_counter();local=self.sql('local',question)
        rr={}
        for values in [arms['baseline'],ordered(local)]:
            for i,x in enumerate(values,1):rr[x['source_id']]=rr.get(x['source_id'],0)+1/(60+i)
        arms['local_rrf']=ordered(rr);timings['local_rrf']=time.perf_counter()-t+timings['baseline']
        t=time.perf_counter();v,features=self.features(question,base)
        arms['coverage_proximity']=ordered(v);timings['coverage_proximity']=time.perf_counter()-t+timings['baseline']
        calc('bm25_b025',lambda:self.custom(question,b=.25))
        calc('bm25_k06',lambda:self.custom(question,k1=.6))
        calc('bm25plus',lambda:self.custom(question,kind='bm25plus'))
        calc('bm25l',lambda:self.custom(question,kind='bm25l'))
        return dict(rankings=arms,timing=timings,custom_parity_max_delta=delta,features=features)

def synthetic():
    texts=['I attend classes every Wednesday.','A class for Thursday.','A different document about cooking.']
    rows=[dict(id=str(i),text=t)for i,t in enumerate(texts)]
    ix=Index(rows,[],{})
    out=ix.run('class')
    assert '0'not in {x['source_id']for x in out['rankings']['baseline']}
    assert '0'in {x['source_id']for x in out['rankings']['stem']}
    out=ix.run('classes cooking Wednesday')
    assert out['custom_parity_max_delta']<1e-9
    ix.db.close();print('synthetic lexical and independent SQLite formula parity passed')

def main():
    guard();src=sources();ps=chunks();by=collections.defaultdict(list)
    for p in ps:by[p['source_id']].append(p)
    cache={};done=0;folder=HERE/'rankings/lexical';folder.mkdir(parents=True,exist_ok=True)
    for c in runtime():
        path=folder/(c['id']+'.json')
        if path.exists():continue
        key=tuple(c['source_ids'])
        if key not in cache:
            ix=Index([src[s]for s in key],[p for s in key for p in by[s]],src);cache[key]=ix
        ix=cache[key];out=ix.run(c['question']);parent=read(ROOT/c['parent_rankings'])
        old=parent['native']['native']if c['cohort']=='original25'else parent['native']
        assert [x['source_id']for x in out['rankings']['baseline'][:10]]==[x['source_id']for x in old['bm25']]
        delta=max(abs(a['score']-b['score'])for a,b in zip(out['rankings']['baseline'],old['bm25']))
        assert delta<1e-10
        out.update(case_id=c['id'],corpus_index_build_seconds=ix.setup_seconds,parent_top10_max_delta=delta)
        out['rankings']['archived_vector']=old['vector']
        save(path,out);done+=1
        if done%10==0:print(json.dumps(dict(lexical_completed=done,last=c['id'])),flush=True)
    for ix in cache.values():ix.db.close()
    print(json.dumps(dict(completed=len(list(folder.glob('*.json'))))))

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='synthetic':synthetic()
    else:main()
