"""Fixed first-attempt high-effort comparison; no retries or answer repair."""
import argparse
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.dont_write_bytecode=True
import harness as h
from codex_transport import CodexServer
from http_transport import ChatTransport
from deepseek_high_transport import DeepSeekTransport

SPECS={
 'gpt-6-luna':dict(run_id='gpt-6-luna-high-first',low='gpt-6-luna',backend='codex',profile='codex-base-v1'),
 'gpt-6.1-sol':dict(run_id='gpt-6.1-sol-high-first',low='gpt-6.1-sol',backend='codex',profile='codex-base-v1'),
 'glm-5.3-flash':dict(run_id='glm-5.3-flash-high-first',low='glm-5.3-flash-low-first',backend='chat',profile='chat-completions-system-wrapper-v1',base_url='https://open.bigmodel.cn/api/coding/paas/v4'),
 'glm-5.3':dict(run_id='glm-5.3-high-first',low='glm-5.3-low-first',backend='chat',profile='chat-completions-system-wrapper-v1',base_url='https://open.bigmodel.cn/api/coding/paas/v4'),
 'deepseek-flash':dict(run_id='deepseek-flash-high-first',low='deepseek-flash-low-first',backend='deepseek-json-object-adapter',profile='chat-json-object-schema-in-system-v1',base_url='https://api.deepseek.com'),
}

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True,choices=SPECS);p.add_argument('--key-env',default='SMM_HIGH_API_KEY');a=p.parse_args()
    h.verify();phase=Path(__file__).resolve().parent;protocol=h.read(phase/'protocol.json');spec=SPECS[a.model]
    for name,want in protocol['code_sha256'].items():assert h.file_hash(ROOT/name)==want
    folder=ROOT/'runs'/spec['run_id']
    if folder.exists():raise ValueError('Run exists: never overwrite or retry a first attempt')
    meta=dict(experiment_id='SMM-B001',run_id=spec['run_id'],model=a.model,effort='high',backend=spec['backend'],
        transport_profile=spec['profile'],paired_low_run=spec['low'],tasks=protocol['tasks'],case_ids=protocol['case_ids'],
        status='running',intended_calls=75,created_at=time.time(),protocol_sha256=h.file_hash(phase/'protocol.json'),
        temperature='provider default, not pinned',max_tokens='provider default, not pinned',timeout_seconds=90)
    if spec.get('base_url'):meta['base_url']=spec['base_url']
    if a.model=='deepseek-flash':meta.update(response_format='json_object',thinking='enabled')
    elif spec['backend']=='chat':meta.update(response_format='json_schema',thinking='provider default enabled')
    h.write_new(folder/'run.json',meta);count=0;errors=[];stop=False;started=time.time()
    try:
        if spec['backend']=='codex':client=CodexServer(folder,a.model,window_limit=0)
        elif spec['backend']=='chat':client=ChatTransport(a.model,spec['base_url'],a.key_env,'high','json_schema',timeout=90)
        else:client=DeepSeekTransport(a.key_env,timeout=90)
        with client:
            if spec['backend']=='codex':
                info=next((m for m in client.rpc('model/list',dict(includeHidden=False))['data']if m['model']==a.model),None)
                if not info or 'high'not in {v['reasoningEffort']for v in info['supportedReasoningEfforts']}:raise ValueError('Exact model/high unavailable; no substitution')
                h.write_new(folder/'model-availability.json',info)
            for cid in protocol['case_ids']:
                for task in protocol['tasks']:
                    req=h.request(task,cid);q=req['request'];target=folder/'records'/task/(cid+'.json')
                    assert req['request_sha256']==protocol['request_sha256'][task+'/'+cid]
                    h.write_new(target.with_suffix('.started.json'),dict(at=time.time(),request_sha256=req['request_sha256']))
                    receipt=dict(experiment_id='SMM-B001',case_id=cid,task=task,model=a.model,effort='high',backend=spec['backend'],request_sha256=req['request_sha256'],imported=False)
                    tick=time.perf_counter()
                    try:
                        if a.model=='deepseek-flash':
                            output,_=client.infer(q['system'],q['payload'],q['schema']);metrics=dict(client.last_metrics)
                        else:output,metrics=client.infer(q['system'],q['payload'],effort='high',schema=q['schema'])
                        if metrics.get('selected_model')!=a.model:raise ValueError('Requested model not selected')
                        if spec['backend']!='codex'and metrics.get('response_model')!=a.model:raise ValueError('Unexpected provider model echo')
                        receipt.update(output=output,metrics=metrics,error=None,mechanical=h.mechanical(task,cid,output))
                    except Exception as exc:
                        secret=os.environ.get(a.key_env,'');msg=str(exc)
                        if secret:msg=msg.replace(secret,'[REDACTED]')
                        metrics=dict(getattr(client,'last_metrics',{}));metrics.setdefault('seconds',time.perf_counter()-tick)
                        receipt.update(output=None,metrics=metrics,error=dict(type=type(exc).__name__,message=msg))
                        errors.append(dict(case_id=cid,task=task,error=receipt['error']))
                        # Independent HTTP timeout/invalid JSON does not consume another attempt.
                        # Stop service/auth/quota failures; a Codex turn failure stops that server.
                        if spec['backend']=='codex'or not isinstance(exc,(TimeoutError,ValueError)):stop=True
                    if a.model=='deepseek-flash'and client.last_response is not None:
                        rel=Path('raw')/task/(cid+'.json');h.write_new(folder/rel,client.last_response)
                        receipt.update(raw_response=str(rel),raw_response_sha256=h.file_hash(folder/rel))
                    h.write_new(target,receipt);count+=1
                    print(h.compact(dict(model=a.model,case_id=cid,task=task,error=receipt['error'],completed=count)),flush=True)
                    if stop:break
                if stop:break
    except BaseException as exc:
        h.write_new(folder/'completion.json',dict(status='failed_preflight_or_runtime',calls=count,intended_calls=75,errors=errors,error_type=type(exc).__name__,no_retries=True,finished_at=time.time()))
        raise
    h.write_new(folder/'completion.json',dict(status='stopped_service_error'if stop else'completed',calls=count,intended_calls=75,errors=errors,no_retries=True,transport_closed=True,elapsed_seconds=time.time()-started,finished_at=time.time()))
    if stop:raise ValueError('First service failure retained; remaining tasks not requested')

if __name__=='__main__':main()
