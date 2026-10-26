"""Evaluation-only evidence packets. Never used to construct model requests."""
import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import harness as h

def main():
    p=argparse.ArgumentParser();p.add_argument('--start',type=int,default=1);p.add_argument('--end',type=int,default=25)
    p.add_argument('--model',choices=['glm-5.3-flash','glm-5.3']);p.add_argument('--task');args=p.parse_args()
    models=[args.model]if args.model else ['glm-5.3-flash','glm-5.3']
    for i in range(args.start,args.end+1):
        cid=f'P{i:02d}';c=h.cases()[cid]
        print(h.compact(dict(case=cid,question=c['question'],reference=c['reference_answer_for_evaluation_only'],
            ambiguous=c['answer_ambiguity'],needs=[dict(id=a['id'],quotes=[w['quote']for w in a['witnesses']])for a in c['requirements']])))
        for model in models:
            for task in ([args.task]if args.task else h.TASKS):
                path=ROOT/'runs'/(model+'-low-first')/'records'/task/(cid+'.json')
                if not path.exists():continue
                r=h.read(path);packet=dict(model=model,task=task,case=cid,output=r['output'],error=r['error'])
                if r['output']is not None:
                    m=h.mechanical(task,cid,r['output']);packet['format_errors']=m['errors'];packet['quote_valid']=m['quote_valid']
                    if task=='candidate_select'and not m['errors']:
                        packet['selection']=h.selection_score(cid,r['output'],{})
                    else:
                        packet['citation_roles']=[dict(claim_index=v['claim_index'],roles=v['possible_message_roles'],source=v['source_id'])for v in m.get('citations',[])]
                        packet['quote_errors']=m.get('quote_errors',[])
                print(h.compact(packet))

if __name__=='__main__':main()
