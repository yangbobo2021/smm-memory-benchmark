"""Offline checks: the effort ablation must preserve actual task envelopes."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import harness as h
from http_transport import ChatTransport
from deepseek_high_transport import wire_body

def load_low():
    spec=importlib.util.spec_from_file_location('low_ds',ROOT/'artifacts/deepseek-comparison-v1/deepseek_transport.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class Contract(unittest.TestCase):
    def test_all_deepseek_payloads_only_effort_changes(self):
        low=load_low()
        for cid in h.experiment()['case_ids']:
            for task in h.TASKS:
                q=h.request(task,cid)['request'];a=low.wire_body(q['system'],q['payload'],q['schema']);b=wire_body(q['system'],q['payload'],q['schema'])
                self.assertEqual(a.pop('reasoning_effort'),'low');self.assertEqual(b.pop('reasoning_effort'),'high');self.assertEqual(a,b)

    def test_glm_transport_only_effort_changes(self):
        bodies=[]
        class Response:
            def __enter__(self):return self
            def __exit__(self,*a):pass
            def read(self):return json.dumps({'model':'glm-5.3','choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}).encode()
        def fake(req,timeout):bodies.append(json.loads(req.data));self.assertEqual(timeout,90);return Response()
        q=h.request('candidate_answer','P06')['request']
        with patch.dict(os.environ,{'OFFLINE_TEST_KEY':'test-only'}),patch('urllib.request.urlopen',fake):
            for effort in ['low','high']:
                with ChatTransport('glm-5.3','https://open.bigmodel.cn/api/coding/paas/v4','OFFLINE_TEST_KEY',effort)as c:c.infer(q['system'],q['payload'],effort,schema=q['schema'])
        self.assertEqual(bodies[0].pop('reasoning_effort'),'low');self.assertEqual(bodies[1].pop('reasoning_effort'),'high');self.assertEqual(bodies[0],bodies[1])

    def test_deepseek_no_retry_on_service_error(self):
        from deepseek_high_transport import DeepSeekTransport
        import urllib.error
        q=h.request('oracle_answer','P01')['request']
        with patch.dict(os.environ,{'OFFLINE_TEST_KEY':'test-only'}),patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('https://api.deepseek.com',429,'rate',{},None))as call:
            with DeepSeekTransport('OFFLINE_TEST_KEY')as c:
                with self.assertRaises(RuntimeError):c.infer(q['system'],q['payload'],q['schema'])
            self.assertEqual(call.call_count,1)

if __name__=='__main__':unittest.main()
