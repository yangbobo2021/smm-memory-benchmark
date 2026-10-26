"""Build navigation from archived receipts without inference or semantic grading."""
import hashlib
import html
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
BUNDLE=ROOT/'experiments/smm-baseline-001'
sys.path.insert(0,str(BUNDLE));sys.dont_write_bytecode=True
import harness as h

def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def link(page,target,label):
    return '['+label+']('+os.path.relpath(target,page.parent)+')'

def cell(value):return html.escape(str(value)).replace('|','&#124;').replace('\n','<br>')

def build():
    models=['gpt-6-luna','gpt-6.1-sol','glm-5.3-flash','glm-5.3','deepseek-flash'];runs=[]
    for model in models:
        for effort in ['low','high']:
            label=model if effort=='low'and model.startswith('gpt-')else model+'-'+effort+'-first'
            folder=h.run_path(label);meta=h.read(folder/'run.json')
            runs.append(dict(run_id=label,model=model,effort=effort,path=str(folder.relative_to(ROOT))))
    rows=[];index=['# Case index / 题目索引','',
        'Every case page links full canonical inputs, original source conversations, all ten model/effort outputs, and separate reviews. These pages are generated navigation, not new inference or new grades.','',
        '| Case | Question |','| --- | --- |']
    for cid,c in h.cases().items():
        page=ROOT/'docs/cases'/(cid+'.md');page.parent.mkdir(parents=True,exist_ok=True)
        lines=['# '+cid+': '+c['question'],'',
            '[All cases](../CASE_INDEX.md) · [Input/output guide](../IO_GUIDE.md)','',
            'Frozen query reference time: `'+c['known_at']+'`. Answer ambiguity: **'+str(c['answer_ambiguity'])+'**.','',
            'Evaluation-only reference (not extra model input): `'+cell(c['reference_answer_for_evaluation_only'])+'`.','',
            link(page,BUNDLE/c['corpus_file'],'Complete public source corpus')+' · '+link(page,BUNDLE/'data/cases.json','Requirements and evaluation metadata'),'']
        for task in h.TASKS:
            inp=BUNDLE/'requests'/task/(cid+'.json')
            lines+=['## '+task,'',link(page,inp,'Complete frozen input: system / payload / schema / audit ledger'),'','Only the nested `request` is the logical model task; the ledger is evaluation mapping. Provider wrappers are documented separately.','',
                '| Model / effort | Actual final answer or selection | Mechanical checks | Seconds | Original record | Review |','| --- | --- | --- | ---: | --- | --- |']
            for run in runs:
                folder=ROOT/run['path'];record=folder/'records'/task/(cid+'.json');r=h.read(record);req=h.read(inp);out=r.get('output')
                assert r['request_sha256']==req['request_sha256']
                raw=r.get('raw_response')or r.get('raw_receipt')
                row=dict(case_id=cid,task=task,model=run['model'],effort=run['effort'],run_id=run['run_id'],
                    request_file=str(inp.relative_to(ROOT)),request_sha256=req['request_sha256'],
                    record_file=str(record.relative_to(ROOT)),record_sha256=h.file_hash(record),
                    output_sha256=h.digest(out)if out is not None else None,error=r.get('error'),
                    review_file=str((folder/'reviews.json').relative_to(ROOT)),
                    raw_receipt_file=str((folder/raw).relative_to(ROOT))if raw else None)
                rows.append(row)
                shown=r['error']if out is None else out.get('selected_sources',[])if task=='candidate_select'else out.get('answer','')
                if out is None:checks='no output'
                else:
                    mechanical=h.mechanical(task,cid,out)
                    checks='format FAIL: '+'; '.join(mechanical['errors'])if mechanical['errors']else'format OK'
                    if mechanical['quote_valid']is not None:checks+='; exact quotes '+('OK'if mechanical['quote_valid']else'FAIL')
                elapsed=r.get('metrics',{}).get('seconds');seconds=f'{elapsed:.3f}'if isinstance(elapsed,(int,float))else 'not recorded'
                lines.append('| '+cell(run['model']+' / '+run['effort'])+' | '+cell(shown)+' | '+cell(checks)+' | '+seconds+' | '+link(page,record,'JSON')+' | '+link(page,folder/'reviews.json','reviews')+' |')
            lines.append('')
        page.write_text('\n'.join(lines)+'\n')
        index.append('| ['+cid+'](cases/'+cid+'.md) | '+cell(c['question'])+' |')
    (ROOT/'docs/CASE_INDEX.md').write_text('\n'.join(index)+'\n')
    dump(ROOT/'docs/run-catalog.json',dict(experiment='SMM-B001',runs=runs))
    (ROOT/'docs/traces.jsonl').write_text('\n'.join(h.compact(r)for r in rows)+'\n')
    assert len(rows)==750
    print(h.compact(dict(cases=25,runs=len(runs),logical_records=len(rows),generated=sum(r['output_sha256']is not None for r in rows))))

if __name__=='__main__':build()
