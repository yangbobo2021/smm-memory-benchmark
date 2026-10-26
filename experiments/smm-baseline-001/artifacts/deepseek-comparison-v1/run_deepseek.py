"""Run 75 frozen SMM-B001 tasks once with an explicitly disclosed JSON adapter."""
import argparse
import os
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.dont_write_bytecode=True
import harness as h
from deepseek_transport import BASE_URL,MODEL,PROFILE,DeepSeekTransport

def main():
    p=argparse.ArgumentParser();p.add_argument('--key-env',required=True);args=p.parse_args()
    h.verify();phase=Path(__file__).resolve().parent;protocol=h.read(phase/'protocol.json')
    assert h.file_hash(phase/'deepseek_transport.py')==protocol['transport_sha256']
    assert h.file_hash(Path(__file__))==protocol['runner_sha256']
    label=protocol['run_id'];folder=ROOT/'runs'/label
    if folder.exists():raise ValueError('Run exists; cannot overwrite or retry first outputs')
    h.write_new(folder/'run.json',dict(experiment_id='SMM-B001',run_id=label,model=MODEL,effort='low',
        backend='deepseek-json-object-adapter',transport_profile=PROFILE,base_url=BASE_URL,
        response_format='json_object',thinking='enabled',temperature='provider default, not pinned',
        max_tokens='provider default, not pinned',tasks=list(h.TASKS),case_ids=h.experiment()['case_ids'],
        status='running',intended_calls=75,created_at=time.time(),protocol_sha256=h.file_hash(phase/'protocol.json')))
    count=0;stop=False;errors=[]
    with DeepSeekTransport(args.key_env)as client:
        for cid in protocol['case_ids']:
            for task in protocol['tasks']:
                obj=h.request(task,cid);target=folder/'records'/task/(cid+'.json')
                h.write_new(target.with_suffix('.started.json'),dict(at=time.time(),request_sha256=obj['request_sha256']))
                receipt=dict(experiment_id='SMM-B001',case_id=cid,task=task,model=MODEL,effort='low',
                    backend='deepseek-json-object-adapter',request_sha256=obj['request_sha256'],imported=False)
                try:
                    output,_=client.infer(obj['request']['system'],obj['request']['payload'],obj['request']['schema'])
                    receipt.update(output=output,metrics=dict(client.last_metrics),error=None,mechanical=h.mechanical(task,cid,output))
                except Exception as exc:
                    secret=os.environ.get(args.key_env,'');message=str(exc)
                    if secret:message=message.replace(secret,'[REDACTED]')
                    receipt.update(output=None,metrics=dict(client.last_metrics),error=dict(type=type(exc).__name__,message=message))
                    errors.append(dict(case_id=cid,task=task,error=receipt['error']))
                    # Keep first task failures; stop spending on service/auth/quota failures.
                    if not isinstance(exc,(TimeoutError,ValueError)):stop=True
                raw=client.last_response
                if raw is not None:
                    rel=Path('raw')/task/(cid+'.json')
                    h.write_new(folder/rel,raw);receipt.update(raw_response=str(rel),raw_response_sha256=h.file_hash(folder/rel))
                h.write_new(target,receipt);count+=1
                print(h.compact(dict(case_id=cid,task=task,error=receipt['error'],completed=count)),flush=True)
                if stop:break
            if stop:break
    h.write_new(folder/'completion.json',dict(status='stopped_service_error'if stop else'completed',
        calls=count,intended_calls=75,errors=errors,no_retries=True,finished_at=time.time()))
    if stop:raise ValueError('Service failure retained; remaining tasks were not requested')

if __name__=='__main__':main()
