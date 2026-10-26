"""Independent source-level replay of published coverage counts."""
import collections
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def read(p):return json.loads(Path(p).read_text())
def covered(reqs,ids):
    got=set(ids);flags=[any(set(w)<=got for w in u)for u in reqs]
    return {'any':any(flags),'all':all(flags),'units':sum(flags),'total_units':len(flags)}

def main():
    plan=read(HERE/'plan.json');runtime={x['id']:x for x in read(ROOT/'experiments/smm-sufficiency-luna-001/runtime.json')}
    labels={x['id']:x for x in read(ROOT/'experiments/smm-sufficiency-luna-001/evaluation.json')}
    rankings=read(HERE/'rankings.json');outcomes=read(HERE/'case-outcomes.json')
    unions=read(HERE/'union-outcomes.json');summary=read(HERE/'summary.json')
    assert len(rankings)==200 and len(outcomes)==178*7*6 and len(unions)==178*3
    assert set(rankings)==set(plan['case_ids'])
    out={(x['id'],x['route'],x['n']):x for x in outcomes}
    union={(x['id'],x['variant']):x for x in unions}
    for cid in plan['case_ids']:
        case=runtime[cid];routes=rankings[cid]['rankings'];available=set(case['source_ids'])
        assert rankings[cid]['question']==case['question']
        for route,rows in routes.items():
            ids=[x['source_id']for x in rows]
            assert len(ids)==len(set(ids)) and set(ids)<=available
            assert all(rows[i]['score']>=rows[i+1]['score']-1e-12 for i in range(len(rows)-1))
            if labels[cid]['semantic_evaluable']:
                for n in [1,2,3,4,5,10]:
                    x=out[(cid,route,n)]
                    assert {k:x[k]for k in ['any','all','units','total_units']}==covered(labels[cid]['requirements'],ids[:n])
                    assert x['candidates']==min(n,len(ids))
        if labels[cid]['semantic_evaluable']:
            for variant,a,b in [('historical_raw','whole_bm25_raw','whole_vector_raw'),
                                ('normalized_whole','whole_bm25_normalized','whole_vector_normalized'),
                                ('branch','branch_bm25','branch_vector')]:
                ids=list(dict.fromkeys([x['source_id']for x in routes[a][:5]]+[x['source_id']for x in routes[b][:5]]))
                x=union[(cid,variant)]
                assert x['source_ids']==ids and x['candidates']==len(ids)
                assert {k:x[k]for k in ['any','all','units','total_units']}==covered(labels[cid]['requirements'],ids)
    for s in summary['rows']:
        a=[x for x in outcomes if x['route']==s['route']and x['n']==s['n']]
        assert len(a)==s['cases']==178
        assert sum(x['any']for x in a)==s['any'] and sum(x['all']for x in a)==s['all']
        assert sum(x['units']for x in a)==s['unit_hits'] and sum(x['total_units']for x in a)==s['unit_total']
    for s in summary['unions']:
        a=[x for x in unions if x['variant']==s['variant']]
        assert len(a)==s['cases']==178
        assert sum(x['any']for x in a)==s['any'] and sum(x['all']for x in a)==s['all']
    result={'verified':True,'questions':200,'clear_dependency_cases':178,'ambiguous_cases':22,
            'source_candidates_unique_and_visible':True,'case_outcomes_replayed':len(outcomes),
            'union_outcomes_replayed':len(unions),'summary_rows_replayed':len(summary['rows'])}
    (HERE/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':main()
