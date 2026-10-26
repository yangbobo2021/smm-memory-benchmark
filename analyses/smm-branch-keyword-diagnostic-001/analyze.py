"""No-model ablations of archived SMM-BR001 discussion branches."""
import collections
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
EXP=ROOT/'experiments/smm-branch-keywords-001'
sys.path.insert(0,str(EXP))
import score

def read(path):return json.loads(Path(path).read_text())

def main():
    plan=read(EXP/'plan.json');runs={x['id']:x for x in read(ROOT/'experiments/smm-sufficiency-luna-001/runtime.json')}
    labels={x['id']:x for x in read(ROOT/'experiments/smm-sufficiency-luna-001/evaluation.json')}
    frozen=read(EXP/'rankings.json');methods={x:{} for x in ['keywords','label_plus_keywords','branch_turn_text']}
    chars=collections.Counter()
    for sid in plan['source_ids']:
        r=read(EXP/'results'/(sid+'.json'))
        adj=EXP/'adjudications'/(sid+'.json')
        branches=read(adj)['effective_output']['branches'] if adj.exists() else r['output']['branches']
        turns={x['turn']:x['text'] for x in r['input']['turns']}
        methods['keywords'][sid]=branches
        methods['label_plus_keywords'][sid]=[{'keywords':[b['label']]+b['keywords']}for b in branches]
        methods['branch_turn_text'][sid]=[{'keywords':[' '.join(turns[t] for t in b['turns'])]}for b in branches]
        chars['original_turns']+=sum(len(x)for x in turns.values())
        chars['keyword_text']+=sum(len(' '.join(b['keywords']))for b in branches)
        chars['branch_turn_text']+=sum(len(' '.join(turns[t]for t in b['turns']))for b in branches)
    ranks={};summary={name:{str(n):collections.Counter()for n in [1,3,5,10]}for name in methods}
    for cid in plan['case_ids']:
        c=runs[cid];e=labels[cid];ranks[cid]={'question':c['question'],'requirement_count':len(e['requirements']),
                                           'clear':e['semantic_evaluable'],'methods':{}}
        for name,entries in methods.items():
            rows=score.bm25(c,entries,score.norm(c['question']))
            if name=='keywords':
                assert [x['source_id']for x in rows[:10]]==[x['source_id']for x in frozen[cid]['rankings']['branch_bm25'][:10]]
            witnesses=sorted({s for u in e['requirements']for w in u for s in w})
            positions={x['source_id']:i+1 for i,x in enumerate(rows)}
            record={'witness_source_positions':{s:positions.get(s)for s in witnesses},
                    'top5_source_ids':[x['source_id']for x in rows[:5]]}
            for n in [1,3,5,10]:
                if not e['semantic_evaluable']:continue
                x=score.covered(e['requirements'],[v['source_id']for v in rows[:n]])
                summary[name][str(n)]['all']+=x['all'];summary[name][str(n)]['any']+=x['any']
                summary[name][str(n)]['unit_hits']+=x['units']
                record[f'top{n}_all']=x['all']
            ranks[cid]['methods'][name]=record
    clear=[cid for cid in plan['case_ids']if labels[cid]['semantic_evaluable']]
    old_miss={cid for cid in clear if not ranks[cid]['methods']['keywords']['top5_all']}
    turn_hit={cid for cid in clear if ranks[cid]['methods']['branch_turn_text']['top5_all']}
    old_hit=set(clear)-old_miss
    whole_hit={cid for cid in clear if score.covered(labels[cid]['requirements'],
                  [x['source_id']for x in frozen[cid]['rankings']['whole_bm25_normalized'][:5]])['all']}
    whole_summary={}
    for n in [1,3,5,10]:
        whole_summary[str(n)]={'all':sum(score.covered(labels[cid]['requirements'],
            [x['source_id'] for x in frozen[cid]['rankings']['whole_bm25_normalized'][:n]])['all']
            for cid in clear)}
    result={'source_count':len(plan['source_ids']),'clear_question_count':len(clear),'ambiguous_question_count':200-len(clear),
            'character_counts':dict(chars),'summary':{m:{n:dict(v)for n,v in d.items()}for m,d in summary.items()},
            'whole_bm25_normalized_all':whole_summary,
            'keyword_top5_misses':sorted(old_miss),'recovered_by_branch_turn_text':sorted(old_miss&turn_hit),
            'newly_lost_by_branch_turn_text':sorted(old_hit-turn_hit),
            'recovered_keyword_misses_that_whole_text_found':len(old_miss&turn_hit&whole_hit),
            'recovered_keyword_misses_that_whole_text_missed':len((old_miss&turn_hit)-whole_hit),
            'case_rows':ranks}
    assert result['summary']['keywords']['5']['all']==133
    assert result['summary']['keywords']['10']['all']==154
    assert result['summary']['branch_turn_text']['5']['all']==158
    assert whole_summary['5']['all']==150 and whole_summary['10']['all']==167
    (HERE/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k!='case_rows'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
