"""Replay from a relocated directory with original data/network/process access denied."""
import argparse
import builtins
import collections
import contextlib
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import socket
import sqlite3
import statistics
import subprocess
import sys
import tempfile

import numpy as np

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--write', action='store_true'); args = parser.parse_args()
    contract = json.loads((HERE / 'scoring-contract.json').read_text())
    assert hashlib.sha256((HERE / 'score.py').read_bytes()).hexdigest() == contract['scorer_sha256']
    assert hashlib.sha256((HERE / 'protocol.json').read_bytes()).hexdigest() == contract['protocol_sha256']
    original = Path('/Users/boboyang/work/next-app')
    denied = [original, HERE.parents[1]]
    runtime = dict(numpy=np.__version__, python=sys.version.split()[0])
    with tempfile.TemporaryDirectory(prefix='smm-rg001-portable-') as temp:
        target = Path(temp) / 'study'
        shutil.copytree(HERE, target, ignore=shutil.ignore_patterns('local-results', '__pycache__', '*.pyc'))
        old = builtins.open, io.open, os.open, socket.socket, subprocess.Popen, sys.argv
        def check(file):
            if isinstance(file, int): return
            path = Path(file).resolve()
            if any(path.is_relative_to(base) for base in denied): raise PermissionError('Original project data read blocked')
        def guarded(opener):
            def wrapper(file, *a, **k):
                check(file); return opener(file, *a, **k)
            return wrapper
        def blocked(*a, **k): raise PermissionError('Offline replay forbids network/process operations')
        capture = io.StringIO(); blocked_checks = []
        try:
            builtins.open = guarded(old[0]); io.open = guarded(old[1]); os.open = guarded(old[2])
            socket.socket = blocked; subprocess.Popen = blocked
            for label, action in [('original_data', lambda: builtins.open(original / 'AGENTS.md')),
                                  ('network', lambda: socket.socket()), ('process', lambda: subprocess.Popen(['true']))]:
                try: action()
                except PermissionError: blocked_checks.append(label)
                else: raise AssertionError('Guard did not reject ' + label)
            sys.argv = [str(target / 'score.py'), '--check', '--verify']
            with contextlib.redirect_stdout(capture): runpy.run_path(str(target / 'score.py'), run_name='__main__')
        finally:
            builtins.open, io.open, os.open, socket.socket, subprocess.Popen, sys.argv = old
        proof = dict(passed=True, relocated=True, guards_actually_rejected=blocked_checks,
                     runtime_preloaded_before_guards=runtime, result=json.loads(capture.getvalue().strip()),
                     new_embeddings=0, generative_calls=0,
                     semantic_answer_labels_independently_audited=False,
                     note='This proves artifact/data/numerical replay portability with NumPy already installed, not universal semantic reference correctness.')
    if args.write:
        with (HERE / 'verification.json').open('x') as f: f.write(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(proof))


if __name__ == '__main__': main()
