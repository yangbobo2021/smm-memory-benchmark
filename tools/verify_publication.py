"""Offline checks for the exact published snapshot and input/output catalog."""
import hashlib
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1];BUNDLE=ROOT/'experiments/smm-baseline-001'
sys.path.insert(0,str(BUNDLE));sys.path.insert(0,str(BUNDLE/'artifacts/high-effort-comparison-v1'));sys.dont_write_bytecode=True
import harness as h
from verify_high import verify

PATTERNS={
 'api-key':r'\bsk-[A-Za-z0-9_-]{16,}',
 'github-token':r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})',
 'private-key':r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',
 'jwt':r'\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{15,}',
 'glm-key':r'\b[a-f0-9]{32}\.[A-Za-z0-9]{12,}\b',
}

def verify_publication():
    if not __debug__:raise ValueError('Run without -O')
    snapshot=h.read(ROOT/'publication/benchmark-files.json')['files']
    actual={str(p.relative_to(BUNDLE))for p in BUNDLE.rglob('*')if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc'and p.name!='.DS_Store'}
    assert actual==set(snapshot),'Published benchmark membership changed'
    for rel,want in snapshot.items():assert h.file_hash(BUNDLE/rel)==want,rel
    proof=verify();rows=[json.loads(s)for s in(ROOT/'docs/traces.jsonl').read_text().splitlines()if s]
    seen=set();errors=0
    for row in rows:
        key=row['run_id'],row['case_id'],row['task'];assert key not in seen;seen.add(key)
        req=h.read(ROOT/row['request_file']);r=h.read(ROOT/row['record_file'])
        assert h.digest(req['request'])==r['request_sha256']==row['request_sha256']
        assert h.file_hash(ROOT/row['record_file'])==row['record_sha256']
        out=r.get('output');assert row['output_sha256']==(h.digest(out)if out is not None else None)
        assert r.get('error')==row['error'];errors+=bool(r.get('error'))
        assert (ROOT/row['review_file']).is_file()
        if row['raw_receipt_file']:assert (ROOT/row['raw_receipt_file']).is_file()
    assert len(seen)==750 and errors==4
    assert len(list((ROOT/'docs/cases').glob('P??.md')))==25
    for p in(ROOT/'docs').rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
            if '://'not in target and not target.startswith('#'):assert (p.parent/target.split('#')[0]).resolve().exists(),(p,target)
    scanned=0;hits=[]
    for p in ROOT.rglob('*'):
        rel=p.relative_to(ROOT)
        if not p.is_file()or any(v in rel.parts for v in ['.git','__pycache__']):continue
        scanned+=1;s=p.read_text(errors='replace')
        for label,pattern in PATTERNS.items():
            if re.search(pattern,s):hits.append(dict(file=str(rel),pattern=label))
        assert not p.is_symlink(),'No symlinks in publication'
    assert not hits,dict(secret_pattern_locations_only=hits)
    return dict(passed=True,benchmark_files=len(snapshot),benchmark_integrity_checks=proof['checks'],logical_records=len(rows),generated=750-errors,timeout_records=errors,case_pages=25,files_scanned=scanned,secret_pattern_hits=0,new_model_calls=0)

if __name__=='__main__':print(h.compact(verify_publication()))
