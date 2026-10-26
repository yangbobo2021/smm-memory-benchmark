"""Explicit post-timeout continuation: first attempts ONLY, never retry an existing record."""
import argparse
import os
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from harness import TASKS,compact,mechanical,read,request,run_path,verify,write_new
from http_transport import ChatTransport

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--key-env',required=True)
    args=p.parse_args();verify();folder=run_path(args.run);meta=read(folder/'run.json')
    assert meta['backend']=='chat'and meta['effort']=='low'
    assert read(folder/'completion.json')['status']=='failed'
    assert (ROOT/'artifacts/glm-comparison-v1/continuation-amendment.json').exists()
    original={}
    for path in(folder/'records').glob('*/*.json'):
        if not path.name.endswith('.started.json'):original[str(path.relative_to(folder))]=__import__('hashlib').sha256(path.read_bytes()).hexdigest()
    pending=[]
    for cid in meta['case_ids']:
        for task in meta['tasks']:
            target=folder/'records'/task/(cid+'.json')
            if target.exists():continue
            if target.with_suffix('.started.json').exists():raise ValueError('Previously started without a result: cannot safely retry')
            pending.append((cid,task,target))
    write_new(folder/'continuation-start.json',dict(original_completion=read(folder/'completion.json'),
        original_record_hashes=original,pending_pairs=[dict(case_id=c,task=t)for c,t,_ in pending],
        no_retries=True,started_at=time.time()))
    count=0;errors=[];stop=False
    with ChatTransport(meta['model'],meta['base_url'],args.key_env,meta['effort'],meta['response_format'])as transport:
        for cid,task,target in pending:
            obj=request(task,cid)
            write_new(target.with_suffix('.started.json'),dict(at=time.time(),request_sha256=obj['request_sha256'],continuation=True))
            receipt=dict(experiment_id='SMM-B001',case_id=cid,task=task,model=meta['model'],effort=meta['effort'],
                backend='chat',request_sha256=obj['request_sha256'],imported=False,continuation=True)
            try:
                output,metrics=transport.infer(obj['request']['system'],obj['request']['payload'],effort=meta['effort'],schema=obj['request']['schema'])
                receipt.update(output=output,metrics=metrics,error=None,mechanical=mechanical(task,cid,output))
            except Exception as exc:
                secret=os.environ.get(args.key_env,'');message=str(exc);raw_text=getattr(exc,'doc',None)
                if secret:
                    message=message.replace(secret,'[REDACTED]')
                    if raw_text:raw_text=raw_text.replace(secret,'[REDACTED]')
                receipt.update(output=None,raw_output_text=raw_text,metrics={},error=dict(type=type(exc).__name__,message=message))
                errors.append(dict(case_id=cid,task=task,error=receipt['error']))
                # A single task timeout is retained; quota/auth/other transport failures stop spending.
                if not isinstance(exc,TimeoutError):stop=True
            write_new(target,receipt);count+=1
            print(compact(dict(case_id=cid,task=task,error=receipt['error'],continuation_completed=count)),flush=True)
            if stop:break
    for rel,value in original.items():assert __import__('hashlib').sha256((folder/rel).read_bytes()).hexdigest()==value
    write_new(folder/'continuation-completion.json',dict(status='stopped'if stop else'completed',
        attempted=count,pending_before=len(pending),errors=errors,original_records_unchanged=True,
        no_retries=True,finished_at=time.time()))

if __name__=='__main__':main()
