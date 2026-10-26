"""Print a recorded visible task input and/or actual output. Never calls a model."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];BUNDLE=ROOT/'experiments/smm-baseline-001'
sys.path.insert(0,str(BUNDLE));sys.dont_write_bytecode=True
import harness as h

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('case_id');p.add_argument('--model',required=True);p.add_argument('--effort',choices=['low','high'],required=True);p.add_argument('--task',choices=h.TASKS,default='candidate_answer');p.add_argument('--section',choices=['input','output','all'],default='all');a=p.parse_args()
    rows=[json.loads(s)for s in(ROOT/'docs/traces.jsonl').read_text().splitlines()if s]
    matches=[r for r in rows if(r['case_id'],r['model'],r['effort'],r['task'])==(a.case_id,a.model,a.effort,a.task)]
    if len(matches)!=1:p.error('Unknown case/model/effort/task combination')
    row=matches[0];req=h.read(ROOT/row['request_file']);receipt=h.read(ROOT/row['record_file'])
    if h.file_hash(ROOT/row['record_file'])!=row['record_sha256']or h.digest(req['request'])!=row['request_sha256']:raise ValueError('Archived input/output binding changed')
    result=dict(case_id=a.case_id,run_id=row['run_id'],task=a.task,request_sha256=row['request_sha256'],
        scope='Canonical visible task plus actual archived final result. Provider wrappers are separate; no hidden reasoning or inference here.')
    if a.section in ['input','all']:result['input']=req['request']
    if a.section in ['output','all']:result['result']=receipt
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
