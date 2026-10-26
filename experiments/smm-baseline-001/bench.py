#!/usr/bin/env python3
"""Portable CLI for frozen SMM-B001 tasks and new model runs."""
import argparse
import json
import shutil
import sys
import time
from contextlib import contextmanager
from pathlib import Path

sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from harness import ROOT,TASKS,cases,compact,digest,experiment,mechanical,read,report_html,request,run_path,safe_id,score_run,verify,write_new


def chosen(value,allowed):
    values=list(allowed)if value=='all'else value.split(',')
    if not values or len(values)!=len(set(values))or not set(values)<=set(allowed):raise ValueError('Invalid task/case selection')
    return values


def make_run(args,backend=None):
    label=safe_id(args.run_id);folder=ROOT/'runs'/label
    if (ROOT/'baselines'/label).exists()or folder.exists():raise ValueError('Run already exists; choose a new ID, never overwrite a first attempt')
    tasks=chosen(args.tasks,TASKS);ids=chosen(args.cases,experiment()['case_ids'])
    meta=dict(experiment_id='SMM-B001',run_id=label,model=args.model,effort=args.effort,
        backend=backend or args.backend,tasks=tasks,case_ids=ids,status='running',created_at=time.time(),
        intended_calls=len(tasks)*len(ids),temperature='provider default, not pinned',
        transport_profile='codex-base-v1'if(backend or args.backend)=='codex'else('external-envelope-unverified'if backend else'chat-completions-system-wrapper-v1'))
    if not backend and args.backend=='chat':meta.update(base_url=args.base_url,response_format=args.response_format)
    write_new(folder/'run.json',meta)
    return folder,meta


@contextmanager
def guarded_transport(factory,folder):
    try:
        with factory(folder)as transport:yield transport
    except BaseException as exc:
        if not(folder/'completion.json').exists():
            write_new(folder/'completion.json',dict(status='failed_preflight_or_runtime',
                recorded_results=sum(not p.name.endswith('.started.json')for p in(folder/'records').glob('*/*.json')),
                error_type=type(exc).__name__,no_retry=True,finished_at=time.time()))
        raise


def run(args):
    verify()
    if args.backend=='codex':
        from codex_transport import CodexServer
        if not shutil.which('codex'):raise ValueError('Codex CLI must be installed and signed in')
        if args.effort=='omit':raise ValueError('Codex requires an explicit supported effort')
        factory=lambda folder:CodexServer(folder,args.model,window_limit=0)
    else:
        from http_transport import ChatTransport
        factory=lambda folder:ChatTransport(args.model,args.base_url,args.key_env,args.effort,args.response_format)
    folder,meta=make_run(args);count=0;failed=False
    with guarded_transport(factory,folder)as transport:
        if args.backend=='codex':
            info=next((m for m in transport.rpc('model/list',dict(includeHidden=False))['data']if m['model']==args.model),None)
            if not info or args.effort not in {v['reasoningEffort']for v in info['supportedReasoningEfforts']}:raise ValueError('Exact model/effort unavailable; no substitution')
            write_new(folder/'model-availability.json',info)
        for cid in meta['case_ids']:
            for task in meta['tasks']:
                obj=request(task,cid);target=folder/'records'/task/(cid+'.json')
                write_new(target.with_suffix('.started.json'),dict(at=time.time(),request_sha256=obj['request_sha256']))
                receipt=dict(experiment_id='SMM-B001',case_id=cid,task=task,model=args.model,effort=args.effort,
                    backend=args.backend,request_sha256=obj['request_sha256'],imported=False)
                try:
                    output,metrics=transport.infer(obj['request']['system'],obj['request']['payload'],effort=args.effort,schema=obj['request']['schema'])
                    receipt.update(output=output,metrics=metrics,error=None,mechanical=mechanical(task,cid,output))
                except Exception as exc:
                    # Provider bodies/authorization headers and environment values are never recorded.
                    message=str(exc)
                    raw_text=getattr(exc,'doc',None)
                    if args.backend=='chat':
                        import os
                        secret=os.environ.get(args.key_env)
                        if secret:
                            message=message.replace(secret,'[REDACTED]')
                            if raw_text:raw_text=raw_text.replace(secret,'[REDACTED]')
                    receipt.update(output=None,raw_output_text=raw_text,metrics={},error=dict(type=type(exc).__name__,message=message));failed=True
                write_new(target,receipt);count+=1
                print(compact(dict(case_id=cid,task=task,error=receipt['error'],completed=count)),flush=True)
                if failed:break
            if failed:break
    write_new(folder/'completion.json',dict(status='failed'if failed else'completed',calls=count,intended_calls=meta['intended_calls'],
        transport_closed=True,finished_at=time.time(),no_retries=True))
    if failed:raise ValueError('First failure retained. Do not reuse this run ID for a retry.')


def export_requests(args):
    verify();tasks=chosen(args.tasks,TASKS);ids=chosen(args.cases,experiment()['case_ids']);out=Path(args.out)
    with out.open('x')as f:
        for cid in ids:
            for task in tasks:
                obj=request(task,cid)
                f.write(compact(dict(experiment_id='SMM-B001',case_id=cid,task=task,request_sha256=obj['request_sha256'],request=obj['request']))+'\n')
    print(compact(dict(requests=len(tasks)*len(ids),output=str(out))))


def ingest(args):
    verify();tasks=chosen(args.tasks,TASKS);ids=chosen(args.cases,experiment()['case_ids'])
    incoming=[json.loads(line)for line in Path(args.file).read_text().splitlines()if line.strip()]
    expected={(t,c)for t in tasks for c in ids};by={(r['task'],r['case_id']):r for r in incoming}
    if len(by)!=len(incoming)or set(by)!=expected:raise ValueError('Import requires exactly the requested task/case pairs, with no duplicates/missing rows')
    for (task,cid),r in by.items():
        if r['request_sha256']!=request(task,cid)['request_sha256']:raise ValueError('Imported request hash does not match')
    folder,meta=make_run(args,'external-jsonl-import')
    for (task,cid),r in by.items():
        write_new(folder/'records'/task/(cid+'.json'),dict(experiment_id='SMM-B001',case_id=cid,task=task,model=args.model,
            effort=args.effort,backend='external-jsonl-import',request_sha256=r['request_sha256'],output=r.get('output'),
            metrics=r.get('metrics',{}),error=r.get('error'),identity='Unverified external model assertion; record provider/adapter details separately'))
    write_new(folder/'completion.json',dict(status='imported',calls=0,imported_results=len(by),source_sha256=__import__('hashlib').sha256(Path(args.file).read_bytes()).hexdigest()))


def review_template(args):
    folder=run_path(args.run);meta=read(folder/'run.json');answers=[];extras={};cs=cases()
    for cid in meta['case_ids']:
        for task in meta['tasks']:
            p=folder/'records'/task/(cid+'.json')
            if not p.exists():continue
            record=read(p)
            if record.get('output')is None or not mechanical(task,cid,record['output'])['schema_valid']:continue
            obj=request(task,cid);output=record['output']
            if task=='candidate_select':
                by={e['source_id']:e['original_source_id']for e in obj['ledger']}
                for alias in output.get('selected_sources',[]):
                    sid=by.get(alias)
                    if sid and sid not in cs[cid]['official_reference_sources']:
                        extras[cid,sid]=dict(case_id=cid,source_id=sid,label=None,alternative_evidence=[],note='Review full original source before deciding direct/related_history/unrelated.')
            else:
                answers.append(dict(case_id=cid,task=task,response_sha256=digest(output),request_sha256=obj['request_sha256'],
                    official_reference_match=None,complete_answer=None,evidence_semantic_valid=None,core_evidence_valid=None,
                    note='',reviewer='',context=dict(question=cs[cid]['question'],reference=cs[cid]['reference_answer_for_evaluation_only'],
                        ambiguous=cs[cid]['answer_ambiguity'],request_file='requests/'+task+'/'+cid+'.json',
                        output=output,mechanical=mechanical(task,cid,output))))
    write_new(Path(args.out),dict(run_id=meta['run_id'],model=meta['model'],answer_reviews=answers,selection_extra_labels=list(extras.values()),
        instruction='Fill semantic booleans after reading original evidence; ambiguous cases keep complete_answer null. Keep hashes. Copy completed file to this run/reviews.json. Never copy baseline ratings onto a new response.'))
    print(compact(dict(answer_reviews=len(answers),extra_source_labels=len(extras),output=args.out)))


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='cmd',required=True)
    sub.add_parser('verify');sub.add_parser('replay')
    p=sub.add_parser('score');p.add_argument('--run',required=True);p.add_argument('--out')
    p=sub.add_parser('report');p.add_argument('--runs',default='gpt-6-luna,gpt-6.1-sol');p.add_argument('--out',required=True)
    for command in ['run','ingest']:
        p=sub.add_parser(command);p.add_argument('--run-id',required=True);p.add_argument('--model',required=True)
        p.add_argument('--effort',default='low');p.add_argument('--tasks',default='all');p.add_argument('--cases',default='all')
        if command=='run':
            p.add_argument('--backend',choices=['codex','chat'],default='codex');p.add_argument('--base-url',default='https://api.openai.com/v1')
            p.add_argument('--key-env',default='SMM_API_KEY');p.add_argument('--response-format',choices=['json_schema','json_object'],default='json_schema')
        else:p.add_argument('--file',required=True)
    p=sub.add_parser('export');p.add_argument('--tasks',default='all');p.add_argument('--cases',default='all');p.add_argument('--out',required=True)
    p=sub.add_parser('review-template');p.add_argument('--run',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('seal-run');p.add_argument('--run',required=True)
    args=parser.parse_args()
    if args.cmd=='verify':print(compact(verify()))
    elif args.cmd=='replay':
        verify();print(compact({m:score_run(m)['summary']for m in experiment()['models_imported']}))
    elif args.cmd=='score':
        verify();value=score_run(args.run)
        if args.out:write_new(Path(args.out),value)
        print(compact(value['summary']))
    elif args.cmd=='report':
        verify();out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('x')as f:f.write(report_html([score_run(v)for v in args.runs.split(',')]))
        print(str(out))
    elif args.cmd=='run':run(args)
    elif args.cmd=='export':export_requests(args)
    elif args.cmd=='ingest':ingest(args)
    elif args.cmd=='review-template':review_template(args)
    elif args.cmd=='seal-run':
        verify();folder=run_path(args.run)
        if folder.parent.name!='runs':raise ValueError('Imported baselines are already frozen')
        scores=score_run(args.run)
        if not scores['full_suite']or not all(s['review_complete']for s in scores['summary'].values()):raise ValueError('Cannot seal an incomplete or unreviewed full-suite run')
        from harness import file_hash
        write_new(folder/'run-manifest.json',dict(files={str(p.relative_to(folder)):file_hash(p)for p in folder.rglob('*')if p.is_file()and p.name!='run-manifest.json'}))
        print('sealed '+args.run)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(type(exc).__name__+': '+str(exc),file=sys.stderr);sys.exit(1)
