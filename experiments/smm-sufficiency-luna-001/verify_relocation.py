"""Copy this repository and replay frozen scores with original reads/net/processes denied."""
import builtins
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import runpy
import shutil
import socket
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REL = Path('experiments/smm-sufficiency-luna-001')


def main():
    original_cwd = Path.cwd()
    original_argv = sys.argv[:]
    original_path = sys.path[:]
    original_open = builtins.open
    original_io_open = io.open
    original_os_open = os.open
    original_socket = socket.socket
    original_connect = socket.create_connection
    original_popen = subprocess.Popen
    original_system = os.system
    original_os_popen = os.popen
    original_spawn = getattr(os, 'posix_spawn', None)
    blocked = dict(original_reads=0, network=0, subprocess=0)

    with tempfile.TemporaryDirectory(prefix='smm-luna-relocate-') as temp:
        copied = Path(temp) / 'repository'
        shutil.copytree(ROOT, copied, ignore=shutil.ignore_patterns('.git', '__pycache__', '.DS_Store'))
        file_count = sum(p.is_file() for p in copied.rglob('*'))

        def deny_original(path):
            if isinstance(path, (str, bytes, os.PathLike)):
                absolute = Path(os.fsdecode(path)).absolute()
                if absolute == ROOT or ROOT in absolute.parents:
                    blocked['original_reads'] += 1
                    raise AssertionError('replay attempted to read the original repository')

        def safe_open(file, *args, **kwargs):
            deny_original(file)
            return original_open(file, *args, **kwargs)

        def safe_io_open(file, *args, **kwargs):
            deny_original(file)
            return original_io_open(file, *args, **kwargs)

        def safe_os_open(file, *args, **kwargs):
            deny_original(file)
            return original_os_open(file, *args, **kwargs)

        def no_network(*args, **kwargs):
            blocked['network'] += 1
            raise AssertionError('replay attempted network access')

        def no_process(*args, **kwargs):
            blocked['subprocess'] += 1
            raise AssertionError('replay attempted to start a subprocess')

        try:
            os.chdir(copied)
            sys.path.insert(0, str(copied / REL))
            sys.argv = [str(copied / REL / 'score.py'), '--verify', '--check']
            builtins.open = safe_open
            io.open = safe_io_open
            os.open = safe_os_open
            socket.socket = no_network
            socket.create_connection = no_network
            subprocess.Popen = no_process
            os.system = no_process
            os.popen = no_process
            if original_spawn is not None:
                os.posix_spawn = no_process
            captured = io.StringIO()
            with redirect_stdout(captured):
                runpy.run_path(str(copied / REL / 'score.py'), run_name='__main__')
            replay_summary = json.loads(captured.getvalue())
            assert replay_summary['completed'] == 257 and replay_summary['pending'] == 0
        finally:
            builtins.open = original_open
            io.open = original_io_open
            os.open = original_os_open
            socket.socket = original_socket
            socket.create_connection = original_connect
            subprocess.Popen = original_popen
            os.system = original_system
            os.popen = original_os_popen
            if original_spawn is not None:
                os.posix_spawn = original_spawn
            os.chdir(original_cwd)
            sys.argv = original_argv
            sys.path[:] = original_path

        assert blocked == {'original_reads': 0, 'network': 0, 'subprocess': 0}
        print(json.dumps(dict(status='passed', relocated_files=file_count,
                              replay='score.py --verify --check', cases=replay_summary['completed'],
                              blocked_attempts=blocked), indent=2))


if __name__ == '__main__':
    main()
