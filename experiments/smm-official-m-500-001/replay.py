"""Portable independent replay from the pinned upstream 2.74 GB JSON file.

Usage: python3 replay.py --raw /path/to/longmemeval_m_cleaned.json
The raw dataset is fetched separately; it is not included in this repository.
"""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'experiments/smm-bm25-scale-1000-002'))
import score
def load(p):return json.loads(p.read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(8<<20),b''):h.update(chunk)
    return h.hexdigest()
def body(turns):return '\n\n'.join(str(t['role']).upper()+':\n'+str(t['content']) for t in turns)
def read_instances(path):
    decoder=json.JSONDecoder()
    with path.open('r',encoding='utf-8') as f:
        buffer='';position=0;started=False
        while True:
            if position>=len(buffer):
                buffer=f.read(4<<20);position=0
                if not buffer:raise ValueError('unexpected EOF')
            while position<len(buffer) and buffer[position] in ' \n\t\r,':position+=1
            if position>=len(buffer):continue
            if not started:
                assert buffer[position]=='[';position+=1;started=True;continue
            if buffer[position]==']':return
            while True:
                try:
                    item,end=decoder.raw_decode(buffer,position)
                    yield item;position=end
                    if position>(8<<20):buffer=buffer[position:];position=0
                    break
                except json.JSONDecodeError:
                    more=f.read(4<<20)
                    if not more:raise ValueError('truncated JSON record')
                    buffer=buffer[position:]+more;position=0
def when(s):return datetime.strptime(s,'%Y/%m/%d (%a) %H:%M')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',type=Path,required=True);args=ap.parse_args()
    extraction=load(HERE/'extraction.json');assert args.raw.stat().st_size==extraction['raw_bytes']
    assert sha(args.raw)==extraction['raw_sha256']
    protocol=load(HERE/'protocol-v2.json');assert sha(HERE/'protocol-v2.json')==load(HERE/'summary.json')['protocol_sha256']
    archived={load(p)['official_question_id']:load(p) for p in (HERE/'results').glob('*.json')}
    assert len(archived)==57
    seen=set();count=0;future_cases={};future_ref_cases={};scores=Counter()
    for item in read_instances(args.raw):
        count+=1;official=item['question_id']
        if official not in archived:continue
        old=archived[official];cid=old['id'];assert cid not in seen;seen.add(cid)
        assert item['question']==old['question']
        serialized=(json.dumps(item,ensure_ascii=False)+'\n').encode()
        assert hashlib.sha256(serialized).hexdigest()==extraction['matched'][cid]['sha256']
        ids=[];texts={};alias={};canonical={};dates={}
        for sid,turns,stamp in zip(item['haystack_session_ids'],item['haystack_sessions'],item['haystack_dates']):
            txt=body(turns);digest=hashlib.sha256(txt.encode()).hexdigest()
            if digest not in canonical:
                canonical[digest]=sid;ids.append(sid);texts[sid]=txt;dates[sid]=stamp
            alias[sid]=canonical[digest]
        refs=list(dict.fromkeys(alias[sid] for sid in item['answer_session_ids']))
        assert len(ids)==old['official_m_count'] and len(refs)==old['official_m_ref_count']
        ranked,_,_=score.rank(ids,texts,item['question']);m=score.measures(ranked,refs)
        assert m['reference_positions']==old['official_m']['reference_positions'],cid
        assert [r['source_id'] for r in ranked[:10]]==old['official_m']['top10_ids'],cid
        for n in (5,10):
            assert m[f'top{n}']==old['official_m'][f'top{n}'],cid
            scores[(old['cohort'],n,'all')]+=m[f'top{n}']['all']
            scores[(old['cohort'],n,'any')]+=m[f'top{n}']['any']
        future=[sid for sid,stamp in zip(item['haystack_session_ids'],item['haystack_dates']) if when(stamp)>when(item['question_date'])]
        if future:
            future_cases[cid]=len(future)
            fr=sorted(set(future)&set(item['answer_session_ids']))
            if fr:future_ref_cases[cid]=fr
    assert count==500 and len(seen)==57
    summary=load(HERE/'summary.json')['cohorts']
    for cohort in ('P25','L32'):
        for n in (5,10):
            for metric in ('all','any'):
                assert scores[(cohort,n,metric)]==summary[cohort]['official_m'][f'top{n}'][metric]
    print(json.dumps({'replayed':57,'upstream_instances':count,'all57_top5':sum(scores[(c,5,'all')] for c in ('P25','L32')),
                      'all57_top10':sum(scores[(c,10,'all')] for c in ('P25','L32')),
                      'future_session_cases':future_cases,'future_reference_cases':future_ref_cases}))
if __name__=='__main__':main()
