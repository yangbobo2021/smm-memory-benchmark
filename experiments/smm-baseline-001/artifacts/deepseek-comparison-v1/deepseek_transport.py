"""DeepSeek JSON-object compatibility adapter. No retries; never retain reasoning text."""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request

PROFILE='chat-json-object-schema-in-system-v1'
BASE_URL='https://api.deepseek.com'
MODEL='deepseek-flash'

def wire_body(system,payload,schema):
    wrapper=system+'\n只根据提供的数据作判断。不得调用工具、访问文件或网络。\n这是检索选择的独立函数调用。输出指定JSON，不执行其他任务。'
    wrapper+='\n\nOUTPUT JSON SCHEMA (format contract only; no reference answer):\n'+json.dumps(schema,ensure_ascii=False,separators=(',',':'))
    return dict(model=MODEL,messages=[dict(role='system',content=wrapper),
        dict(role='user',content=json.dumps(payload,ensure_ascii=False,separators=(',',':')))],
        n=1,stream=False,reasoning_effort='low',thinking=dict(type='enabled'),response_format=dict(type='json_object'))

def body_hash(body):return hashlib.sha256(json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

class DeepSeekTransport:
    def __init__(self,key_env,timeout=90):
        self.key=os.environ.get(key_env)
        if not self.key:raise ValueError('Missing explicitly provided API credential')
        self.timeout=timeout;self.last_response=None;self.last_metrics={}

    def infer(self,system,payload,schema):
        body=wire_body(system,payload,schema);self.last_response=None
        self.last_metrics=dict(requested_model=MODEL,transport_profile=PROFILE,wire_body_sha256=body_hash(body),tool_calls=0)
        request=urllib.request.Request(BASE_URL+'/chat/completions',
            data=json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.key})
        started=time.perf_counter()
        try:
            try:
                with urllib.request.urlopen(request,timeout=self.timeout)as response:raw=json.load(response)
            except urllib.error.HTTPError as exc:
                self.last_response=dict(http_status=exc.code)
                raise RuntimeError('DeepSeek HTTP '+str(exc.code)+'; no retry or provider substitution')from None
            choice=raw['choices'][0];message=choice['message']
            # Retain the actual final output and service metadata, never reasoning_content or headers.
            self.last_response=dict(id=raw.get('id'),model=raw.get('model'),created=raw.get('created'),
                system_fingerprint=raw.get('system_fingerprint'),finish_reason=choice.get('finish_reason'),
                final_content=message.get('content'),usage=raw.get('usage',{}),refusal=message.get('refusal'))
            self.last_metrics.update(selected_model=MODEL,response_model=raw.get('model'),usage=raw.get('usage',{}),
                response_id=raw.get('id'),system_fingerprint=raw.get('system_fingerprint'),
                model_identity='provider echo only; not independent attestation')
            if raw.get('model')!=MODEL:raise ValueError('Unexpected response model; no silent substitution')
            if message.get('tool_calls')or message.get('function_call'):raise ValueError('Unexpected tool call')
            if choice.get('finish_reason')!='stop':raise ValueError('Response incomplete: '+str(choice.get('finish_reason')))
            if message.get('refusal'):raise ValueError('Model returned refusal')
            if not isinstance(message.get('content'),str):raise ValueError('No textual JSON response')
            output=json.loads(message['content'])
        finally:
            self.last_metrics['seconds']=time.perf_counter()-started
        return output,dict(self.last_metrics)

    def close(self):self.key=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
