"""Verify the sealed file list for SMM-SF-LUNA001 without model calls."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MANIFEST = HERE / 'artifact-manifest.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest['id'] == 'SMM-SF-LUNA001'
    expected = manifest['files']
    assert len(expected) == len(set(expected))
    for name, digest in expected.items():
        path = ROOT / name
        assert path.is_file() and not path.is_symlink(), name
        assert sha(path) == digest, name
    local = {p.relative_to(ROOT).as_posix() for p in HERE.rglob('*')
             if p.is_file() and p != MANIFEST}
    assert local == {name for name in expected if name.startswith('experiments/smm-sufficiency-luna-001/')}
    print(json.dumps(dict(passed=True, sealed_files=len(expected), local_experiment_files=len(local))))


if __name__ == '__main__':
    main()
