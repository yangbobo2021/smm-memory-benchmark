"""Shared source-only inputs; scoring labels are deliberately loaded elsewhere."""
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
B = ROOT / 'experiments/smm-baseline-001'
G = ROOT / 'experiments/smm-retrieval-generalization-001'
LOCAL = Path('/Users/boboyang/work/next-app/work/smm-method-comparison-001')
sys.path.insert(0, str(G / 'implementation'))
STOP = set('a an and are as at be been being but by can could did do does for from had has have how i if in into is it its me my of on or our should so than that the their them there these they this those to us was we were what when where which who why will with would you your'.split())

def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def th(t): return hashlib.sha256(t.encode()).hexdigest()
def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x')as f: json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def terms(q):return list(dict.fromkeys(re.findall(r'[^\W_]+',q.casefold(),re.UNICODE)))[:128]
def expr(q):return ' OR '.join('"'+x+'"'for x in terms(q))
def runtime():return read(HERE/'runtime.json')
def sources():
    out={}
    for rel in read(HERE/'source-files.json')['corpora']:
        d=read(ROOT/rel)
        for r in d['records']:
            r=dict(r,structure=d['structure'][r['id']])
            if r['id']in out:assert out[r['id']]['text']==r['text']
            out[r['id']]=r
    for rel in read(HERE/'source-files.json')['sources']:
        r=read(ROOT/rel)
        if r['id']in out:assert out[r['id']]['text']==r['text']
        out[r['id']]=r
    assert all(th(r['text'])==r['source_sha256']for r in out.values())
    return out
def guard():
    p=read(HERE/'protocol.json')
    amendment=read(HERE/'compute-amendment.json')if(HERE/'compute-amendment.json').exists()else None
    if amendment:assert amendment['protocol_sha256']==sha(HERE/'protocol.json')
    for rel,h in p['files'].items():
        if amendment and rel in amendment['changed_files']:
            change=amendment['changed_files'][rel]
            assert h==change['original_sha256']==sha(HERE/change['original_copy'])
            h=change['amended_sha256']
        assert sha(ROOT/rel)==h,rel
    return p
def ordered(scores):return [dict(source_id=s,score=float(v))for s,v in sorted(scores.items(),key=lambda x:(-x[1],x[0]))]
def chunks():return read(HERE/'passages.json')
def chunk_text(chunk,src):
    t=src[chunk['source_id']]['text'][chunk['start']:chunk['end']]
    assert th(t)==chunk['text_sha256'];return t
