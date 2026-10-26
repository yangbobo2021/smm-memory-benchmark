"""Development-only probe: rerank BM25's first 100 sessions by *received* date.

This intentionally does not infer event dates inside text. It measures whether
cheap session metadata can rescue temporal references, and records regressions.
"""
from __future__ import annotations
import calendar
from datetime import datetime, timedelta, date
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys

HERE=Path(__file__).resolve().parent
BASE=Path('/Users/boboyang/work/smm-memory-benchmark/experiments/smm-bm25-scale-1000-002')
sys.path.insert(0,str(BASE))
import score
from score_m import body

WEEKDAY={x.lower():i for i,x in enumerate(calendar.day_name)}
NUMBER={'a':1,'one':1,'couple':2,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10}
MONTH={x.lower():i for i,x in enumerate(calendar.month_name) if x}
def nvalue(s): return int(s) if s.isdigit() else NUMBER.get(s)
def month_sub(y,m,n):
    total=y*12+m-1-n
    return total//12,(total%12)+1
def month_bounds(y,m):return date(y,m,1),date(y,m,calendar.monthrange(y,m)[1])
def window(question,question_date):
    """Conservative English relative-date rules, fixed before any ranking."""
    q=question.lower(); today=datetime.strptime(question_date,'%Y/%m/%d (%a) %H:%M').date()
    m=re.search(r'\blast (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',q)
    if m:
        delta=(today.weekday()-WEEKDAY[m.group(1)])%7 or 7
        target=today-timedelta(days=delta)
        return target,target,'last-weekday'
    m=re.search(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s+(\d+|a|one|couple|two|three|four|five|six)\s+months?\s+ago\b',q)
    if m:
        y,mo=month_sub(today.year,today.month,nvalue(m.group(2)))
        return *month_bounds(y,mo),'weekday-months-ago'
    if 'past weekend' in q or 'last weekend' in q:
        days=(today.weekday()-5)%7 or 7
        sat=today-timedelta(days=days)
        return sat,sat+timedelta(days=1),'past-weekend'
    m=re.search(r'\b(?:past|last)\s+(\d+|a|one|couple|two|three|four|five|six)\s+(days?|weeks?|months?)\b',q)
    if m:
        n=nvalue(m.group(1));u=m.group(2)
        days=n*(30 if u.startswith('month') else 7 if u.startswith('week') else 1)
        return today-timedelta(days=days),today,'past-period'
    m=re.search(r'\b(\d+|a|one|couple|two|three|four|five|six)\s+(days?|weeks?|months?)\s+ago\b',q)
    if m:
        n=nvalue(m.group(1));u=m.group(2)
        if u.startswith('month'):
            y,mo=month_sub(today.year,today.month,n)
            return *month_bounds(y,mo),'months-ago'
        target=today-timedelta(days=n*(7 if u.startswith('week') else 1))
        pad=3 if u.startswith('week') else 1
        return target-timedelta(days=pad),target+timedelta(days=pad),'days-weeks-ago'
    if re.search(r'\b(?:past|last)\s+month\b',q):
        y,mo=month_sub(today.year,today.month,1)
        return *month_bounds(y,mo),'last-month'
    m=re.search(r'\b(?:in|of|during)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b',q)
    if m:
        mo=MONTH[m.group(1)];y=today.year if mo<=today.month else today.year-1
        return *month_bounds(y,mo),'named-month'
    return None

def main():
    out=HERE/'time-probe';out.mkdir(exist_ok=True)
    code_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    protocol={'id':'SMM-M-TIME-PROBE-001','status':'development-only; frozen before first ranking',
      'base_protocol_sha256':hashlib.sha256((HERE/'protocol-v2.json').read_bytes()).hexdigest(),
      'code_sha256':code_sha,'method':'same original-question BM25; if relative-date rule yields window, stable-promote in-window received_at sessions among raw BM25 first 100, keeping within/outside BM25 order; no hard exclusion',
      'limitation':'received_at can differ from event date; official M includes future sessions and 2 future official references; no blind claim'}
    pp=out/'protocol.json'
    if pp.exists():assert json.loads(pp.read_text())==protocol
    else: pp.write_text(json.dumps(protocol,indent=2)+'\n')
    results=[]
    for cid in sorted(x.stem for x in (HERE/'results').glob('*.json')):
        path=out/'results'/f'{cid}.json'
        if path.exists():results.append(json.loads(path.read_text()));continue
        item=json.loads((HERE/'cases'/f'{cid}.json').read_text())
        ids=[];texts={};dates={};alias={};h2id={}
        for sid,turns,stamp in zip(item['haystack_session_ids'],item['haystack_sessions'],item['haystack_dates']):
            txt=body(turns);digest=hashlib.sha256(txt.encode()).hexdigest()
            if digest not in h2id:
                h2id[digest]=sid;ids.append(sid);texts[sid]=txt;dates[sid]=datetime.strptime(stamp,'%Y/%m/%d (%a) %H:%M').date()
            alias[sid]=h2id[digest]
        refs=list(dict.fromkeys(alias[sid] for sid in item['answer_session_ids']))
        raw,build_s,query_s=score.rank(ids,texts,item['question'])
        w=window(item['question'],item['question_date'])
        if w:
            first=raw[:100]
            front=[r for r in first if w[0]<=dates[r['source_id']]<=w[1]]
            back=[r for r in first if not w[0]<=dates[r['source_id']]<=w[1]]
            ranked=front+back+raw[100:]
        else:ranked=raw
        prior=json.loads((HERE/'results'/f'{cid}.json').read_text())
        assert score.measures(raw,refs)['reference_positions']==prior['official_m']['reference_positions']
        m=score.measures(ranked,refs)
        result={'id':cid,'cohort':prior['cohort'],'type':prior['type'],'question':item['question'],
          'window':None if not w else {'start':str(w[0]),'end':str(w[1]),'rule':w[2]},
          'raw':{'top5':prior['official_m']['top5'],'top10':prior['official_m']['top10'],'reference_positions':prior['official_m']['reference_positions']},
          'probe':{'top5':m['top5'],'top10':m['top10'],'reference_positions':m['reference_positions'],'top10_ids':[r['source_id'] for r in ranked[:10]]},
          'time_bonus_count_in_raw100':sum(w[0]<=dates[r['source_id']]<=w[1] for r in raw[:100]) if w else 0,
          'query_seconds':query_s,'build_seconds':build_s}
        path.parent.mkdir(exist_ok=True)
        with path.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
        results.append(result)
    summary={'protocol_sha256':hashlib.sha256(pp.read_bytes()).hexdigest(),'questions':len(results),'parsed':sum(x['window'] is not None for x in results),'cohorts':{}}
    for cohort in ['P25','L32','all57']:
        arr=results if cohort=='all57' else [x for x in results if x['cohort']==cohort]
        d={'questions':len(arr),'parsed':sum(x['window'] is not None for x in arr)}
        for n in (5,10):
            key=f'top{n}';d[key]={v:{z:sum(x[v][key][z] for x in arr) for z in ['all','any']} for v in ['raw','probe']}
            d[key]['gains']=[x['id'] for x in arr if not x['raw'][key]['all'] and x['probe'][key]['all']]
            d[key]['losses']=[x['id'] for x in arr if x['raw'][key]['all'] and not x['probe'][key]['all']]
        summary['cohorts'][cohort]=d
    target=out/'summary.json';assert not target.exists();target.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))
if __name__=='__main__':main()
