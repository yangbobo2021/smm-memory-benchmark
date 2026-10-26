"""Evaluation-only display of actual outputs; never imported by inference code."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import harness as h
from run_high import SPECS

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=SPECS);p.add_argument('--start',type=int,default=1);p.add_argument('--end',type=int,default=25);p.add_argument('--selection',action='store_true');p.add_argument('--unreviewed',action='store_true');a=p.parse_args()
    decisions=Path(__file__).resolve().parent/'review-decisions.jsonl'
    reviewed={(r['model'],r['case_id'],r['task'])for r in(json.loads(s)for s in decisions.read_text().splitlines())}if decisions.exists()else set()
    for model,spec in SPECS.items():
        if a.model and model!=a.model:continue
        for i in range(a.start,a.end+1):
            cid=f'P{i:02d}';c=h.cases()[cid]
            for task in (['candidate_select']if a.selection else['oracle_answer','candidate_answer']):
                if a.unreviewed and (model,cid,task)in reviewed:continue
                path=ROOT/'runs'/spec['run_id']/'records'/task/(cid+'.json')
                if not path.exists():continue
                r=h.read(path);o=r.get('output');packet=dict(model=model,case=cid,task=task,error=r.get('error'))
                if o is not None:
                    m=h.mechanical(task,cid,o);packet.update(format=m['errors'],quote_valid=m['quote_valid'])
                    if task=='candidate_select':packet.update(output=o,selection=h.selection_score(cid,o,{})if not m['errors']else None)
                    else:
                        selected=o.get('selected_sources',[])
                        if len(selected)>12:selected=dict(unique=list(dict.fromkeys(selected)),count=len(selected))
                        packet.update(status=o.get('status'),answer=o.get('answer'),selected=selected,
                            claims=[dict(claim=v.get('claim'),quotes=[dict(evidence=cite.get('evidence_id'),quote=cite.get('quote'))for cite in v.get('citations',[])])for v in o.get('claims',[])],missing=o.get('missing'),quote_errors=m.get('quote_errors'),roles=[v['possible_message_roles']for v in m.get('citations',[])])
                print(h.compact(packet))

if __name__=='__main__':main()
