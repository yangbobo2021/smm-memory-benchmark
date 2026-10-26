"""Materialize explicit review decisions; never infer semantic grades."""
import json
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import harness as h

def main():
    phase=Path(__file__).resolve().parent;p=h.read(phase/'protocol.json')
    parser=argparse.ArgumentParser();parser.add_argument('--model',choices=p['models']);args=parser.parse_args()
    decisions=[json.loads(s)for s in(phase/'review-decisions.jsonl').read_text().splitlines()if s]
    extra=h.read(phase/'selection-extra-reviews.json')if(phase/'selection-extra-reviews.json').exists()else[]
    seen={(r['model'],r['case_id'],r['task'])for r in decisions};assert len(seen)==len(decisions)
    for model,spec in p['models'].items():
        if args.model and args.model!=model:continue
        folder=ROOT/'runs'/spec['run_id'];rows=[r for r in decisions if r['model']==model]
        done=h.read(folder/'completion.json');assert done['calls']==75 and done['status']=='completed'
        expected=set()
        for f in(folder/'records').glob('*/*.json'):
            if f.name.endswith('.started.json')or f.parent.name=='candidate_select':continue
            r=h.read(f)
            if r.get('output')is not None:expected.add((f.stem,f.parent.name))
        assert {(r['case_id'],r['task'])for r in rows}==expected,(model,'Missing/extra actual-output reviews')
        for r in rows:
            receipt=h.read(folder/'records'/r['task']/(r['case_id']+'.json'))
            assert h.digest(receipt['output'])==r['response_sha256']and receipt['request_sha256']==r['request_sha256']
        h.write_new(folder/'reviews.json',dict(run_id=spec['run_id'],model=model,answer_reviews=rows,
            selection_extra_labels=[r for r in extra if r['model']==model],scope='Actual high outputs individually reviewed by parent researcher; no copied low labels or model judge.'))
    print(h.compact(dict(reviewed_generated_answers=len(decisions),extra_source_reviews=len(extra))))

if __name__=='__main__':main()
