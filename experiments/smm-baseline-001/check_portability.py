#!/usr/bin/env python3
"""Copy this bundle outside the project, then test offline with forbidden-path guards."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
GUARD=r'''
import os,runpy,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve()
forbidden=[Path(p).resolve()for p in __import__('json').loads(sys.argv[2])]
script=sys.argv[3];args=sys.argv[4:]
def audit(event,values):
    if event=='open' and isinstance(values[0],(str,bytes,os.PathLike)):
        p=Path(os.fsdecode(values[0])).resolve()
        if any(p==f or f in p.parents for f in forbidden):
            raise PermissionError('Original-project read blocked')
    if event in ['socket.connect','socket.getaddrinfo','subprocess.Popen','os.system']:
        raise PermissionError('Network/subprocess forbidden in offline portability check')
sys.addaudithook(audit)
sys.path.insert(0,str(root));sys.dont_write_bytecode=True
os.chdir(root)
sys.argv=[script]+args
runpy.run_path(str(root/script),run_name='__main__')
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--forbid-root',action='append',default=[])
    p.add_argument('--out',required=True)
    args=p.parse_args()
    forbidden=[str(ROOT)]+[str(Path(v).resolve())for v in args.forbid_root]
    outcomes=[]
    with tempfile.TemporaryDirectory(prefix='smm-b001-portability-')as temp:
        copy=Path(temp)/'bundle'
        shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('artifacts','runs','__pycache__','*.pyc'))
        env={'PATH':os.environ.get('PATH',''),'HOME':temp,'LANG':'en_US.UTF-8','LC_ALL':'en_US.UTF-8'}
        def call(label,script,arguments,expected=0):
            command=[sys.executable,'-I','-B','-c',GUARD,str(copy),json.dumps(forbidden),script,*arguments]
            done=subprocess.run(command,cwd=temp,env=env,capture_output=True,text=True,timeout=60)
            if done.returncode!=expected:
                raise RuntimeError(label+' failed: '+done.stderr[-4000:]+done.stdout[-1000:])
            outcomes.append(dict(check=label,passed=True,exit_code=done.returncode,
                output_sha256=hashlib.sha256((done.stdout+done.stderr).encode()).hexdigest()))
            return done
        verify=call('relocated-verify','bench.py',['verify'])
        v=json.loads(verify.stdout)
        replay=call('relocated-offline-score-replay','bench.py',['replay'])
        call('relocated-unit-tests','tests/test_harness.py',[])
        call('export-without-evaluation-labels','bench.py',['export','--cases','P06','--out','requests-export.jsonl'])
        exported=[json.loads(s)for s in(copy/'requests-export.jsonl').read_text().splitlines()]
        assert len(exported)==3 and all(set(r)=={'experiment_id','case_id','task','request_sha256','request'}for r in exported)
        rows=[]
        for row in exported:
            receipt=json.loads((copy/'baselines/gpt-6-luna/records'/row['task']/'P06.json').read_text())
            rows.append(dict(case_id=row['case_id'],task=row['task'],request_sha256=row['request_sha256'],
                output=receipt['output'],metrics={'fixture_only':True}))
        (copy/'synthetic-fixture.jsonl').write_text('\n'.join(json.dumps(r)for r in rows)+'\n')
        ingest=['ingest','--file','synthetic-fixture.jsonl','--cases','P06','--model','synthetic-contract-only','--run-id','synthetic-contract-only']
        call('external-import-contract-no-inference','bench.py',ingest)
        call('first-output-cannot-be-overwritten','bench.py',ingest,expected=1)
        call('new-run-review-template','bench.py',['review-template','--run','synthetic-contract-only','--out','review-template.json'])
        scored=call('new-answer-not-auto-graded','bench.py',['score','--run','synthetic-contract-only'])
        scores=json.loads(scored.stdout)
        assert scores['oracle_answer']['primary_correct']is None and scores['candidate_answer']['primary_correct']is None
        call('portable-report','bench.py',['report','--out','report.html'])
        # Show that the hash guard catches a real file alteration, without touching the bundle.
        altered=copy/'requests/candidate_answer/P06.json'
        altered.write_text(altered.read_text()+'\n')
        call('frozen-input-tamper-rejected','bench.py',['verify'],expected=1)
        result=dict(experiment_id='SMM-B001',passed=True,python=sys.version.split()[0],
            copied_outside_original_project=True,original_project_paths_forbidden=forbidden,
            network_and_subprocess_blocked_inside_each_test=True,no_site_packages=True,new_model_calls=0,
            frozen_files=v['frozen_files'],integrity_checks=v['checks'],checks=outcomes,
            replay=json.loads(replay.stdout),
            scope='Relocated offline replay, import, review, scoring and tamper detection; no live model or provider validation.')
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x')as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(dict(passed=True,checks=len(outcomes),new_model_calls=0,output=str(out)),ensure_ascii=False))


if __name__=='__main__':main()
