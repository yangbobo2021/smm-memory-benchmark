"""Seal and verify this experiment's published files without model access."""
import argparse
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
MANIFEST=HERE/'artifact-manifest.json'

def files():
    return {str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(HERE.rglob('*')) if p.is_file() and p!=MANIFEST and '__pycache__' not in p.parts and p.suffix!='.pyc'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--create',action='store_true');args=ap.parse_args()
    actual=files()
    if args.create:
        assert not MANIFEST.exists(), 'Already sealed; review changes explicitly before resealing'
        with MANIFEST.open('x') as f:json.dump({'files':actual},f,indent=2,ensure_ascii=False);f.write('\n')
    else:
        expected=json.loads(MANIFEST.read_text())['files']
        assert actual==expected,{'missing':sorted(set(expected)-set(actual)),
                                 'extra':sorted(set(actual)-set(expected)),
                                 'changed':sorted(k for k in actual.keys()&expected.keys() if actual[k]!=expected[k])}
    print(json.dumps({'verified':True,'files':len(actual),'model_calls':0}))

if __name__=='__main__':main()
