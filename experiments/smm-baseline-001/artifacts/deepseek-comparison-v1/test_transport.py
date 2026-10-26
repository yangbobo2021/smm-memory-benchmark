import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch
from deepseek_transport import DeepSeekTransport,wire_body

class AdapterContract(unittest.TestCase):
    def test_schema_only_changes_format_contract_payload_stays_exact(self):
        payload={'question':'synthetic','observed_evidence':[]}
        schema={'type':'object','properties':{'selected_sources':{'type':'array'}}}
        body=wire_body('Select evidence',payload,schema)
        self.assertEqual(json.loads(body['messages'][1]['content']),payload)
        self.assertIn(json.dumps(schema,separators=(',',':')),body['messages'][0]['content'])
        self.assertEqual(body['response_format'],{'type':'json_object'})
        self.assertEqual(body['reasoning_effort'],'low')

    def test_one_request_metrics_and_no_reasoning_saved(self):
        raw=dict(id='synthetic',model='deepseek-flash',choices=[dict(finish_reason='stop',message=dict(
            content='{"ok":true}',reasoning_content='SYNTHETIC-REASONING-NOT-FOR-RETENTION'))],usage={})
        with patch.dict(os.environ,{'SMM_TEST_ONLY_KEY':'synthetic-test-secret'}),patch('urllib.request.urlopen',return_value=io.BytesIO(json.dumps(raw).encode()))as call:
            with DeepSeekTransport('SMM_TEST_ONLY_KEY')as client:
                output,metrics=client.infer('JSON',{},dict(type='object'))
                self.assertEqual(output,{'ok':True});self.assertIn('seconds',metrics)
                self.assertNotIn('SYNTHETIC-REASONING',json.dumps(client.last_response))
            self.assertEqual(call.call_count,1)

    def test_quota_error_does_not_retry(self):
        with patch.dict(os.environ,{'SMM_TEST_ONLY_KEY':'synthetic-test-secret'}),patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('https://api.deepseek.com',429,'quota',{},None))as call:
            with DeepSeekTransport('SMM_TEST_ONLY_KEY')as client:
                with self.assertRaisesRegex(RuntimeError,'HTTP 429'):client.infer('JSON',{},dict(type='object'))
            self.assertEqual(call.call_count,1)

if __name__=='__main__':unittest.main()
