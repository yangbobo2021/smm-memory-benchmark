import copy
import io
import json
import os
import shutil
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import harness as h
from http_transport import ChatTransport


class EvaluationContracts(unittest.TestCase):
    def temp_case(self,cid,task,output):
        tmp=tempfile.TemporaryDirectory();root=Path(tmp.name)
        for relative in ['experiment.json','data/cases.json','data/corpora/'+cid+'.json','requests/'+task+'/'+cid+'.json']:
            p=root/relative;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(h.ROOT/relative,p)
        folder=root/'runs'/'synthetic-test'
        h.write_new(folder/'run.json',dict(run_id='synthetic-test',model='synthetic-test',effort='low',backend='test-only',tasks=[task],case_ids=[cid]))
        req=h.request(task,cid)
        h.write_new(folder/'records'/task/(cid+'.json'),dict(case_id=cid,task=task,model='synthetic-test',request_sha256=req['request_sha256'],output=output,error=None,metrics={}))
        return tmp,root,folder,req

    def test_correct_source_ids_do_not_auto_grade_answer(self):
        req=h.request('oracle_answer','P06')
        output=dict(status='answer',answer='3 days',claims=[],selected_sources=req['request']['payload']['known_sources'],missing='')
        tmp,root,folder,_=self.temp_case('P06','oracle_answer',output)
        with tmp,patch.object(h,'ROOT',root):
            score=h.score_run('synthetic-test')
            self.assertIsNone(score['summary']['oracle_answer']['primary_correct'])
            self.assertFalse(score['summary']['oracle_answer']['review_complete'])

    def test_changed_response_cannot_reuse_review(self):
        output=dict(status='answer',answer='Wrong answer',claims=[],selected_sources=[],missing='')
        tmp,root,folder,req=self.temp_case('P06','oracle_answer',output)
        with tmp,patch.object(h,'ROOT',root):
            h.write_new(folder/'reviews.json',dict(answer_reviews=[dict(case_id='P06',task='oracle_answer',
                request_sha256=req['request_sha256'],response_sha256='not-the-response-hash',
                complete_answer=True,official_reference_match=True,evidence_semantic_valid=True)]))
            with self.assertRaisesRegex(ValueError,'Review does not match'):h.score_run('synthetic-test')

    def test_unknown_source_is_pending_not_automatically_false(self):
        cid='P06';req=h.request('candidate_select',cid);c=h.cases()[cid];refs=set(c['official_reference_sources'])
        relevant=[e['source_id']for e in req['ledger']if e['original_source_id']in refs]
        extra=next(e for e in req['ledger']if e['original_source_id']not in refs)
        output=dict(selected_sources=relevant+[extra['source_id']])
        score=h.selection_score(cid,output,{})
        self.assertIsNone(score['selection_correct']);self.assertEqual(score['unrelated_count'],0)
        labeled={(cid,extra['original_source_id']):dict(case_id=cid,source_id=extra['original_source_id'],label='unrelated')}
        score=h.selection_score(cid,output,labeled)
        self.assertFalse(score['selection_correct']);self.assertEqual(score['unrelated_count'],1)

    def test_latest_only_can_pass_without_all_old_reference_sources(self):
        cid='P04';req=h.request('candidate_select',cid);c=h.cases()[cid]
        latest=c['requirements'][0]['witnesses'][0]['source_id']
        alias=next(e['source_id']for e in req['ledger']if e['original_source_id']==latest)
        score=h.selection_score(cid,dict(selected_sources=[alias]),{})
        self.assertTrue(score['selection_correct']);self.assertFalse(score['all_baseline_sources_selected'])

    def test_quote_copy_error_is_separate_from_answer_semantics(self):
        record=h.read(h.ROOT/'baselines/gpt-6-luna/records/candidate_answer/P13.json')
        check=h.mechanical('candidate_answer','P13',record['output'])
        self.assertTrue(check['schema_valid']);self.assertFalse(check['quote_valid'])
        grade=h.score_run('gpt-6-luna')
        row=next(r for r in grade['rows']if r['task']=='candidate_answer'and r['case_id']=='P13')
        self.assertTrue(row['correct'])

    def test_all_six_imported_primary_scores_recompute(self):
        expected={'gpt-6-luna':(21,22,19),'gpt-6.1-sol':(23,25,23)}
        for model,counts in expected.items():
            score=h.score_run(model)
            self.assertEqual(tuple(score['summary'][t]['primary_correct']for t in h.TASKS),counts)

    def test_illegal_selected_id_rejected(self):
        errors=h.mechanical('candidate_select','P06',dict(selected_sources=['not-a-candidate']))
        self.assertFalse(errors['schema_valid'])


class HttpAdapterContract(unittest.TestCase):
    def test_fixed_json_request_and_no_key_in_metrics(self):
        capture={}
        def respond(request,timeout):
            capture['body']=json.loads(request.data);capture['authorization']=request.headers['Authorization']
            return io.BytesIO(json.dumps(dict(model='synthetic-revision',choices=[dict(finish_reason='stop',message=dict(content='{"selected_sources": []}'))],usage={})).encode())
        with patch.dict(os.environ,{'SMM_TEST_KEY':'synthetic-only-token'}),patch('urllib.request.urlopen',side_effect=respond)as call:
            with ChatTransport('synthetic-model','https://example.invalid/v1','SMM_TEST_KEY',effort='omit')as client:
                output,metrics=client.infer('Return JSON',dict(question='synthetic'),schema=dict(type='object'))
            self.assertEqual(call.call_count,1);self.assertEqual(capture['body']['n'],1)
            self.assertNotIn('reasoning_effort',capture['body'])
            self.assertEqual(capture['body']['response_format']['type'],'json_schema')
            self.assertEqual(output,dict(selected_sources=[]))
            self.assertNotIn('synthetic-only-token',json.dumps(metrics))

    def test_http_error_has_no_retry_or_raw_body(self):
        with patch.dict(os.environ,{'SMM_TEST_KEY':'synthetic-only-token'}),patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('https://example.invalid',400,'error',{},None))as call:
            with ChatTransport('synthetic','https://example.invalid/v1','SMM_TEST_KEY')as client:
                with self.assertRaisesRegex(RuntimeError,'HTTP 400'):client.infer('Return JSON',{},schema={})
            self.assertEqual(call.call_count,1)


if __name__=='__main__':unittest.main()
