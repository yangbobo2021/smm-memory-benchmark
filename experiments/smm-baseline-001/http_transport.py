"""Explicit OpenAI-compatible Chat Completions adapter; no SDK or retries."""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


class ChatTransport:
    def __init__(self,model,base_url,key_env,effort='low',response_format='json_schema',timeout=90):
        parsed=urllib.parse.urlsplit(base_url)
        if parsed.scheme not in ['http','https']or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Use a base URL without credentials, query, or fragment')
        self.model=model;self.url=base_url.rstrip('/')+'/chat/completions';self.effort=effort
        self.key=os.environ.get(key_env)
        if not self.key:raise ValueError('Missing API key environment variable: '+key_env)
        self.response_format=response_format;self.timeout=timeout

    def infer(self,system,payload,effort='low',schema=None):
        # Same visible task/data, but the HTTP envelope is a DISTINCT profile.
        # Never claim this exactly recreates Codex's hidden runtime wrapper.
        message_system=system+'\n只根据提供的数据作判断。不得调用工具、访问文件或网络。\n这是检索选择的独立函数调用。输出指定JSON，不执行其他任务。'
        body=dict(model=self.model,messages=[dict(role='system',content=message_system),
            dict(role='user',content=json.dumps(payload,ensure_ascii=False,separators=(',',':')))],n=1,stream=False)
        if self.effort!='omit':body['reasoning_effort']=self.effort
        if self.response_format=='json_schema':body['response_format']=dict(type='json_schema',json_schema=dict(name='smm_b001',strict=True,schema=schema))
        else:body['response_format']=dict(type='json_object')
        request=urllib.request.Request(self.url,data=json.dumps(body,ensure_ascii=False).encode(),
            headers={'Content-Type':'application/json','Authorization':'Bearer '+self.key})
        started=time.perf_counter()
        try:
            with urllib.request.urlopen(request,timeout=self.timeout)as response:raw=json.load(response)
        except urllib.error.HTTPError as exc:raise RuntimeError('Chat Completions HTTP '+str(exc.code)+'; no automatic retry/fallback')from None
        except urllib.error.URLError:raise RuntimeError('Chat Completions connection failed; no automatic retry')from None
        choice=raw['choices'][0];message=choice['message']
        if message.get('tool_calls')or message.get('function_call'):raise ValueError('Unexpected tool call')
        if choice.get('finish_reason')!='stop':raise ValueError('Response not complete: '+str(choice.get('finish_reason')))
        if message.get('refusal'):raise ValueError('Model returned refusal')
        text=message.get('content')
        if not isinstance(text,str):raise ValueError('No textual JSON response')
        output=json.loads(text)  # Do not repair fences, retry, or accept a second sample.
        return output,dict(seconds=time.perf_counter()-started,selected_model=self.model,
            response_model=raw.get('model'),model_identity='provider echo only; not an attestation',
            transport_profile='chat-completions-system-wrapper-v1',tool_calls=0,usage=raw.get('usage',{}))

    def close(self):self.key=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
