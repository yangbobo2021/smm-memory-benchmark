"""Apply the frozen mixed-1000 dual-view ordering to recorded official-M rankings."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=HERE/'dual-probe';out.mkdir(exist_ok=True)
    protocol={'id':'SMM-M-DUAL-001','status':'post-hoc M analysis; identical ordering previously frozen in SMM-DUAL-VIEW-1000-001',
      'mixed1000_protocol_sha256':sha(Path('/Users/boboyang/work/smm-memory-benchmark/experiments/smm-dual-view-1000-001/protocol.json')),
      'transfer_protocol_sha256':sha(HERE/'transfer-probe/protocol.json'),
      'ordering':'whole Top5 then USER-only Top5, deduplicated, then remaining whole rank until 10 sources',
      'primary_metric':'all official reference source IDs in selected ten; not answer correctness',
      'caveat':'M had already been inspected before this combination was proposed; not blind independent validation'}
    pp=out/'protocol.json'
    if pp.exists():assert load(pp)==protocol
    else:pp.write_text(json.dumps(protocol,indent=2)+'\n')
    rows=[]
    for f in sorted((HERE/'transfer-probe/results').glob('*.json')):
        x=load(f);v=x['variants'];refs=v['raw-whole']['reference_positions']
        selected=list(dict.fromkeys(v['raw-whole']['top10_ids'][:5]+v['raw-user-only']['top10_ids'][:5]+v['raw-whole']['top10_ids']))[:10]
        assert len(selected)==10
        found=sum(sid in selected for sid in refs)
        rows.append({'id':x['id'],'cohort':x['cohort'],'type':x['type'],'selected_ids':selected,
          'reference_count':len(refs),'reference_hits':found,'all':found==len(refs),'any':found>0,
          'raw_top10_all':v['raw-whole']['top10']['all']})
    summary={'protocol_sha256':sha(pp),'questions':len(rows),'cohorts':{}}
    for c in ['P25','L32','all57']:
        a=rows if c=='all57' else [x for x in rows if x['cohort']==c]
        summary['cohorts'][c]={'questions':len(a),'raw_top10_all':sum(x['raw_top10_all'] for x in a),
           'dual10_all':sum(x['all'] for x in a),'dual10_any':sum(x['any'] for x in a),
           'gains':[x['id'] for x in a if x['all'] and not x['raw_top10_all']],
           'losses':[x['id'] for x in a if x['raw_top10_all'] and not x['all']]}
    target=out/'results.json';assert not target.exists();target.write_text(json.dumps(rows,indent=2)+'\n')
    target=out/'summary.json';assert not target.exists();target.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))
if __name__=='__main__':main()
