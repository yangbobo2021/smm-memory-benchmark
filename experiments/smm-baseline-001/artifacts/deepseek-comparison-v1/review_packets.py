"""Evaluation-only output/evidence display; never used in model input construction."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import harness as h

def main():
    p=argparse.ArgumentParser();p.add_argument('--start',type=int,default=1);p.add_argument('--end',type=int,default=25)
    args=p.parse_args()
    for i in range(args.start,args.end+1):
        cid=f'P{i:02d}';c=h.cases()[cid]
        print(h.compact(dict(case=cid,question=c['question'],reference=c['reference_answer_for_evaluation_only'],ambiguous=c['answer_ambiguity'],
            needs=[dict(id=a['id'],quotes=[w['quote']for w in a['witnesses']])for a in c['requirements']])))
        for task in h.TASKS:
            path=ROOT/'runs/deepseek-flash-low-first/records'/task/(cid+'.json')
            if not path.exists():continue
            r=h.read(path);packet=dict(task=task,case=cid,output=r['output'],error=r['error'])
            if r['output']is not None:
                m=h.mechanical(task,cid,r['output']);packet['format_errors']=m['errors'];packet['quote_valid']=m['quote_valid']
                if task=='candidate_select'and not m['errors']:packet['selection']=h.selection_score(cid,r['output'],{})
                else:
                    packet['citation_roles']=[dict(claim_index=v['claim_index'],roles=v['possible_message_roles'],source=v['source_id'])for v in m.get('citations',[])]
                    packet['quote_errors']=m.get('quote_errors',[])
            print(h.compact(packet))

if __name__=='__main__':main()
