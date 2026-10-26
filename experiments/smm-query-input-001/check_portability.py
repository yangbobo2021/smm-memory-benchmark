"""Copy the repository, then replay with original reads/network/processes denied."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

BOOTSTRAP = r'''
import argparse, collections, csv, hashlib, importlib.metadata, io, json, math, os
from pathlib import Path
import re, runpy, socket, sqlite3, statistics, subprocess, sys, time
import numpy as np
# Load NumPy's lazy support before denying its original installed package root.
f=io.BytesIO();np.save(f,np.array([1.0]));f.seek(0);np.load(f);np.linalg.norm(np.array([1.0]))
forbidden=json.loads(sys.argv[2]);probe_file=sys.argv[3];blocked={}
def audit(event,args):
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        path=os.path.realpath(os.fsdecode(args[0]))
        if any(path==p or path.startswith(p+os.sep) for p in forbidden):raise PermissionError('original root denied')
    if event in ('socket.connect','subprocess.Popen','os.system','os.posix_spawn'):
        raise PermissionError('network/subprocess denied')
sys.addaudithook(audit)
for name,call in [
    ('original_read',lambda:open(probe_file,'rb')),
    ('network',lambda:socket.socket().connect(('127.0.0.1',9))),
    ('subprocess',lambda:subprocess.run(['/usr/bin/true']))]:
    try:call()
    except PermissionError:blocked[name]=True
    else:raise AssertionError(name+' was not denied')
sys.argv=[sys.argv[1],'verify'];runpy.run_path(sys.argv[0],run_name='__main__')
print(json.dumps({'offline_replay_passed':True,'actual_denial_probes':blocked}))
'''


def main():
    with tempfile.TemporaryDirectory(prefix='smm-qi001-offline-') as tmp:
        copied = Path(tmp) / 'repository'
        shutil.copytree(ROOT, copied, copy_function=os.link,
                        ignore=shutil.ignore_patterns('.git', '__pycache__', 'smm-method-comparison-001'))
        script = copied / 'experiments/smm-query-input-001/lab.py'
        forbidden = [str(ROOT), '/Users/boboyang/work/next-app']
        proc = subprocess.run([sys.executable, '-B', '-c', BOOTSTRAP, str(script),
                               json.dumps(forbidden), str(ROOT / 'README.md')],
                              cwd=copied, capture_output=True, text=True,
                              env=dict(os.environ, OPENBLAS_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1'))
        result = dict(passed=proc.returncode == 0, returncode=proc.returncode,
                      stdout=proc.stdout, stderr=proc.stderr,
                      scope='whole-repository read-only ranking/scoring replay; no new encoding',
                      old_partial_method_experiment_excluded=True)
        with (HERE / 'portability.json').open('x') as f:
            json.dump(result, f, ensure_ascii=False, indent=2); f.write('\n')
        assert result['passed'], result
        print(json.dumps(dict(passed=True, actual_denial_probes=3)))


if __name__ == '__main__': main()
