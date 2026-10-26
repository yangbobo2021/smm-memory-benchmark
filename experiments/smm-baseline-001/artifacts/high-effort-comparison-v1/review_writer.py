"""Append explicit researcher decisions, bound to each actual new output."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import harness as h
from run_high import SPECS
PATH=Path(__file__).resolve().parent/'review-decisions.jsonl'

def put(model,cid,task,note,*,complete=True,official=True,evidence=True,core=True):
    prior=[h.read(p)for p in []]  # No baseline review labels are loaded.
    if PATH.exists():
        import json
        prior=[json.loads(line)for line in PATH.read_text().splitlines()if line]
    assert not any((r['model'],r['case_id'],r['task'])==(model,cid,task)for r in prior),'Decision already recorded'
    r=h.read(ROOT/'runs'/SPECS[model]['run_id']/'records'/task/(cid+'.json'));assert r.get('output')is not None
    assert type(official)is bool
    if h.cases()[cid]['answer_ambiguity']:
        assert complete is None and (evidence is None or type(evidence)is bool)and(core is None or type(core)is bool)
    else:assert type(complete)is bool and type(evidence)is bool and type(core)is bool
    row=dict(model=model,case_id=cid,task=task,request_sha256=r['request_sha256'],response_sha256=h.digest(r['output']),
        official_reference_match=official,complete_answer=complete,evidence_semantic_valid=evidence,core_evidence_valid=core,
        note=note,reviewer='parent research assistant; individually read actual new response and original evidence; not independent external human blind labels')
    with PATH.open('a')as f:f.write(h.compact(row)+'\n')
