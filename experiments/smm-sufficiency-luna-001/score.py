"""Evaluation only. Never imported by the model runner; no new model calls."""
import argparse
import collections
import json
from pathlib import Path
import statistics
import sys

from contract import validate
from lab import guard, read, digest, sha, search, sources, document_payload, request

HERE=Path(__file__).resolve().parent


def coverage(e,ids,view):
    ids=set(ids)
    if view=='official':
        units=[[[s]]for s in e['official_refs']]
    else:units=e['requirements']
    covered=[i for i,u in enumerate(units)if any(set(w)<=ids for w in u)]
    return dict(complete=len(covered)==len(units),covered=covered,missing=[i for i in range(len(units))if i not in covered],total=len(units))


def calculate(verify=False,require_complete=True):
    guard();runtime=read(HERE/'runtime.json');labels={x['id']:x for x in read(HERE/'evaluation.json')};src=sources()
    rows=[];pending=[];checks=collections.Counter()
    for c in runtime:
        cid=c['id'];firstfile=HERE/'records/round1'/(cid+'.json')
        if not firstfile.exists():pending.append([cid,'round1']);continue
        first=read(firstfile);req=read(HERE/'requests/round1'/(cid+'.json'))
        assert req==request(document_payload(c,c['initial_source_ids'],src));checks['first_payload_complete']+=1
        assert first['request_sha256']==req['request_sha256'];checks['first_request_binding']+=1
        if first['error']is None:
            assert first['validation']==validate(first['output'],req['request']['payload'])
            assert first['metrics']['selected_model']=='gpt-6-luna'and first['effort']=='high'
            assert first['metrics']['selected_provider']=='openai'and first['metrics']['tool_calls']==0
        if first['error']is None and first['output']['decision']=='insufficient':
            fp=HERE/'followups'/(cid+'.json')
            if not fp.exists():pending.append([cid,'followup']);continue
            f=read(fp);q=first['output']['next_query'];assert q==f['query']and f['origin_response_sha256']==digest(first['output'])
            assert f['excluded_source_ids']==c['initial_source_ids']
            extra=[x['source_id']for x in f['returned']];visible=c['initial_source_ids']+extra
            assert not set(c['initial_source_ids'])&set(extra)and len(visible)==len(set(visible))and len(extra)<=5
            assert f['visible_source_ids']==visible;checks['followup_no_repeat']+=1
            if verify:
                replay=search(c['source_ids'],q,src,exclude=c['initial_source_ids'])
                assert replay['all_ranked']==f['full_corpus_ranking']and replay['eligible_ranked']==f['complete_eligible_ranking']
                assert replay['eligible_ranked'][:5]==f['returned'];checks['followup_numeric_replay']+=1
            if extra:
                secondfile=HERE/'records/round2'/(cid+'.json')
                if not secondfile.exists():pending.append([cid,'round2']);continue
                second=read(secondfile);rq=read(HERE/'requests/round2'/(cid+'.json'))
                assert rq==request(document_payload(c,visible,src,previous=first['output']))
                assert second['request_sha256']==rq['request_sha256'];checks['second_payload_complete']+=1
                if second['error']is None:
                    assert second['validation']==validate(second['output'],rq['request']['payload'])
                    assert second['metrics']['selected_model']=='gpt-6-luna'and second['effort']=='high'
                    assert second['metrics']['selected_provider']=='openai'and second['metrics']['tool_calls']==0
            else:second=None
        else:
            f=None;second=None;extra=[];visible=c['initial_source_ids']
            assert not (HERE/'followups'/(cid+'.json')).exists();checks['no_search_after_stop_or_error']+=1
        e=labels[cid]
        first_decision=first['output']['decision']if first['error']is None else'error'
        second_decision=second['output']['decision']if second and second['error']is None else'error'if second else None
        end_decision=second_decision if second else first_decision
        row=dict(id=cid,cohort=c['cohort'],question=c['question'],semantic_evaluable=e['semantic_evaluable'],ambiguity=e['ambiguity'],
            initial_sources=c['initial_source_ids'],added_sources=extra,visible_sources=visible,
            first_decision=first_decision,second_decision=second_decision,final_decision=end_decision,
            next_query=f['query']if f else None,first_error=first['error'],second_error=second['error']if second else None,
            first_literal_quotes_valid=first['validation']['literal_quotes_valid']if first['validation']else None,
            second_literal_quotes_valid=second['validation']['literal_quotes_valid']if second and second['validation']else None,
            views={view:dict(initial=coverage(e,c['initial_source_ids'],view),after=coverage(e,visible,view))for view in ['official','dependency']})
        rows.append(row)
    if require_complete:assert not pending,pending
    summaries=[]
    for cohort in ['original25','longmemeval_new32','locomo_random200']:
        sample=[r for r in rows if r['cohort']==cohort]
        for view in ['official','dependency']:
            eligible=[r for r in sample if view=='official'or r['semantic_evaluable']]
            complete=[r for r in eligible if r['views'][view]['initial']['complete']]
            incomplete=[r for r in eligible if not r['views'][view]['initial']['complete']]
            searched=[r for r in eligible if r['next_query']is not None]
            needed_search=[r for r in incomplete if r['next_query']is not None]
            after_complete=[r for r in eligible if r['second_decision']is not None and r['views'][view]['after']['complete']]
            after_incomplete=[r for r in eligible if r['second_decision']is not None and not r['views'][view]['after']['complete']]
            summaries.append(dict(cohort=cohort,view=view,cases=len(eligible),ambiguous_separate=sum(not r['semantic_evaluable']for r in sample)if view=='dependency'else 0,
                complete_initial=len(complete),complete_judged_sufficient=sum(r['first_decision']=='sufficient'for r in complete),
                complete_judged_insufficient=sum(r['first_decision']=='insufficient'for r in complete),
                complete_call_errors=sum(r['first_decision']=='error'for r in complete),
                incomplete_initial=len(incomplete),incomplete_judged_insufficient=sum(r['first_decision']=='insufficient'for r in incomplete),
                incomplete_premature_stop=sum(r['first_decision']=='sufficient'for r in incomplete),
                incomplete_call_errors=sum(r['first_decision']=='error'for r in incomplete),
                searches=len(searched),necessary_searches=len(needed_search),
                needed_search_adds_any_missing_unit=sum(bool(set(r['views'][view]['initial']['missing'])&set(r['views'][view]['after']['covered']))for r in needed_search),
                needed_search_completes_all=sum(r['views'][view]['after']['complete']for r in needed_search),
                all_initial_incomplete_recovered=sum(r['views'][view]['after']['complete']for r in incomplete),
                after_search_complete=len(after_complete),after_search_complete_judged_sufficient=sum(r['second_decision']=='sufficient'for r in after_complete),
                after_search_incomplete=len(after_incomplete),after_search_incomplete_judged_insufficient=sum(r['second_decision']=='insufficient'for r in after_incomplete),
                correct_final_stops=sum(r['final_decision']=='sufficient'and r['views'][view]['after']['complete']for r in eligible),
                incorrect_final_stops=sum(r['final_decision']=='sufficient'and not r['views'][view]['after']['complete']for r in eligible),
                final_dependency_coverage=sum(r['views'][view]['after']['complete']for r in eligible),
                recovered_and_stopped=sum(r['final_decision']=='sufficient'and r['views'][view]['after']['complete']for r in incomplete)))
    records=[read(p)for stage in ['round1','round2']for p in (HERE/'records'/stage).glob('*.json')if not p.name.endswith('.started.json')]
    times=[r['metrics']['seconds']for r in records if r['metrics'].get('seconds')is not None]
    usage=collections.Counter()
    for r in records:
        for k,v in r['metrics'].get('usage',{}).items():usage[k]+=v or 0
    return dict(id='SMM-SF-LUNA001',model='gpt-6-luna',effort='high',cases=rows,summaries=summaries,pending=pending,
        calls=dict(logical_attempts=len(records),round1=sum(r['stage']=='round1'for r in records),round2=sum(r['stage']=='round2'for r in records),
                   errors=sum(r['error']is not None for r in records),literal_quote_failures=sum(bool(r['validation'])and not r['validation']['literal_quotes_valid']for r in records),
                   median_seconds=statistics.median(times)if times else None,reported_usage=dict(usage)),
        checks=dict(checks),scope='Fixed pre-inference researcher dependency labels, not omniscient certainty or final answer accuracy.' )


def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');p.add_argument('--check',action='store_true');p.add_argument('--partial',action='store_true');a=p.parse_args()
    d=calculate(verify=a.verify,require_complete=not a.partial)
    if not a.partial:
        if a.check:assert read(HERE/'results.json')==d
        else:
            with (HERE/'results.json').open('x')as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(dict(completed=len(d['cases']),pending=len(d['pending']),calls=d['calls'],summaries=d['summaries']),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
