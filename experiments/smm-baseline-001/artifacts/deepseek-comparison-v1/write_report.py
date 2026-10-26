"""Build an offline five-model comparison from first outputs and reviewed labels."""
import html
import math
import statistics
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import harness as h
from verify_comparison import verify

DEST=Path(__file__).resolve().parent
LABELS=['gpt-6-luna','gpt-6.1-sol','glm-5.3-flash-low-first','glm-5.3-low-first','deepseek-flash-low-first']

def write_text(path,value):
    with path.open('x')as f:f.write(value)

def main():
    proof=verify();scores=[h.score_run(label)for label in LABELS]
    h.write_new(DEST/'verification.json',proof)
    h.write_new(DEST/'comparison.json',dict(experiment_id='SMM-B001',runs=scores))
    content={};timing={};failures={}
    for s in scores:
        content[s['model']]={};timing[s['model']]={};failures[s['model']]={}
        reviews=h.read(h.run_path(s['run_id'])/'reviews.json')['answer_reviews']
        for task in h.TASKS:
            rows=[r for r in s['rows']if r['task']==task]
            times=sorted(r['seconds']for r in rows if isinstance(r.get('seconds'),(int,float)))
            timing[s['model']][task]=dict(returned_latency_samples=len(times),median_seconds=statistics.median(times),
                p95_returned_seconds=times[math.ceil(.95*len(times))-1],max_returned_seconds=max(times),
                generation_errors=[r['case_id']for r in rows if r['state']=='generation_error'])
            failures[s['model']][task]=[dict(case_id=r['case_id'],state=r['state'],
                format_errors=r.get('mechanical',{}).get('errors',[]),note=(r.get('review')or{}).get('note',''))
                for r in rows if not r.get('correct')and not(task!='candidate_select'and r['ambiguous'])]
            if task!='candidate_select':
                rr={r['case_id']:r for r in reviews if r['task']==task}
                clear=[r for r in rows if not r['ambiguous']]
                content[s['model']][task]=dict(semantic_content_correct=sum(rr.get(r['case_id'],{}).get('complete_answer')is True for r in clear),
                    clear_questions=len(clear),generated_clear_answers=sum('output'in r for r in clear),
                    semantic_wrong_case_ids=[r['case_id']for r in clear if rr.get(r['case_id'],{}).get('complete_answer')is False],
                    format_error_case_ids=[r['case_id']for r in rows if r['state']=='format_error'],
                    generation_error_case_ids=[r['case_id']for r in rows if r['state']=='generation_error'],
                    note='Separate semantic-content diagnostic; does not change or repair frozen primary scores.')
    h.write_new(DEST/'semantic-content-diagnostic.json',content);h.write_new(DEST/'timing.json',timing);h.write_new(DEST/'failures.json',failures)
    ds=next(s for s in scores if s['model']=='deepseek-flash');run=h.run_path(ds['run_id']);done=h.read(run/'completion.json')
    rows=['# SMM-B001：DeepSeek Flash 对比','',
        '日期：2026-10-26。模型deepseek-flash，thinking=enabled、reasoning_effort=low。复用25题×3任务，75份固定逻辑请求及原始完整会话；不重检索、不重编码、不提供gold或证据要点。','',
        f"本次正式首次请求{done['calls']}次，其中生成失败{len(done['errors'])}次。另2次最小兼容性探测（json_schema拒绝、json_object成功），不计成绩。没有语义重抽、结果修补或重试已有题。",'',
        '## 固定评分结果','',
        '答题主分沿用冻结程序，格式失败和生成失败不能通过。P22/P25原有时间适用歧义单列，回答主分母23；筛选25题，以必要信息选齐且无确认无关误选为准。','',
        '| 模型 | 准确上下文完整回答 | 混合Top5筛选 | 混合Top5完整回答 |','| --- | ---: | ---: | ---: |']
    for s in scores:
        vals=[str(s['summary'][t]['primary_correct'])+'/'+str(s['summary'][t]['primary_denominator'])for t in h.TASKS]
        rows.append('| '+s['model']+' | '+' | '.join(vals)+' |')
    rows+=['','## 正文与协议失败分开','',
        '| 模型 | 准确上下文正文正确/23 | 混合候选正文正确/23 |','| --- | ---: | ---: |']
    for s in scores:
        d=content[s['model']]
        rows.append('| '+s['model']+' | '+str(d['oracle_answer']['semantic_content_correct'])+'/23 | '+str(d['candidate_answer']['semantic_content_correct'])+'/23 |')
    rows+=['',
        '正文诊断读取实际语义复核，区分内容答错、格式失败和无输出，不替换冻结主分。例如DeepSeek的P02混合回答给出了正确20打和有效来源，但增加type字段，冻结additionalProperties=false将其判为格式失败；没有删字段再冒充原始通过。GLM重复编号和超时的原记录与原分数也不改变。',
        'DeepSeek另有P24准确上下文：26天正确，但把真实提供的received_at时间戳当成原文正文quote，逐字引用检查失败。日期不是捏造，metadata与正文引用的契约仍需区分；没有修补该首输出。','',
        '## DeepSeek逐题复核','']
    for rv in h.read(run/'reviews.json')['answer_reviews']:
        if rv['complete_answer']is False or rv['evidence_semantic_valid']is False:
            rows.append('- '+rv['case_id']+' '+rv['task']+'：'+rv['note'])
    if not any(rv['complete_answer']is False or rv['evidence_semantic_valid']is False for rv in h.read(run/'reviews.json')['answer_reviews']):
        rows.append('本次已生成明确题未发现语义复核失败；仍需分别查看格式、引用逐字性及歧义题，不能由小样本推得通用可靠。')
    rows+=['','## 返回耗时','',
        '单位秒，下表仅成功返回输出的请求中位数（包含可能格式或语义错误的输出）；失败请求单列。非APP端到端时间，非并发/缓存/调度完全受控的纯模型速度比较。','',
        '| 模型 | 准确上下文回答 | 筛选 | 混合候选回答 |','| --- | ---: | ---: | ---: |']
    for s in scores:rows.append('| '+s['model']+' | '+' | '.join(f"{timing[s['model']][t]['median_seconds']:.2f}"for t in h.TASKS)+' |')
    rows+=['',
        '各模型错误题、格式错误、正文错误及返回延迟分布分别见failures.json、semantic-content-diagnostic.json和timing.json。DeepSeek的完整首次输出、服务回显模型名、request ID、system_fingerprint和token用量均保存；隐藏reasoning_content不保存。接口回显不是独立模型身份认证。','',
        '## 必须保留的接口差异','',
        'DeepSeek当前接口拒绝response_format=json_schema（HTTP400：This response_format type is unavailable now）。采用官方支持的json_object，将冻结请求中的同一份JSON Schema统一追加到system的格式约定中；原任务system前缀、user payload和每道题的schema内容保持一致，没有增加解题提示。额外3个离线契约测试验证了payload不变、schema仅用于格式、调用不重试、不留思考文本。','',
        '这保持了逻辑任务和评分，但实际wire prompt与原生schema路径不同。75个实际wire-body hash在推理前冻结，协议/适配器/runner随包保存，可审计与重跑。不能称与GPT Codex或GLM原生schema只有模型权重不同，尤其格式通过率会受服务约束能力影响。','',
        '本轮使用low思考，与此前生产探索中的DeepSeek非思考配置不同；旧非思考成绩没有复用。temperature和max_tokens采用服务默认，low标签不保证不同供应商投入相同计算量。','',
        '官方依据：[JSON输出](https://api-docs.deepseek.com/guides/json_mode/)、[思考参数](https://api-docs.deepseek.com/guides/thinking_mode/)。当前原生schema拒绝以preflight.json实际响应为证。','',
        '## 复现','',
        '在SMM-B001根目录使用Python>=3.11，无第三方Python包依赖：','',
        '```bash','python3 bench.py verify','python3 artifacts/deepseek-comparison-v1/verify_comparison.py',
        'python3 bench.py score --run deepseek-flash-low-first',
        'python3 bench.py report --runs gpt-6-luna,gpt-6.1-sol,glm-5.3-flash-low-first,glm-5.3-low-first,deepseek-flash-low-first --out artifacts/new-five-model-report.html','```','',
        '离线命令不调用模型。新模型重测需新run-id及明确凭证；本次首结果已经封存，runner拒绝覆盖已有run。原75输入、全部原文、参考与评分、适配器、实际wire哈希及原始final JSON均在同一实验目录中。',
        '本次run_deepseek.py是固定本次身份的可审计执行快照，直接重跑会拒绝已有目录；未来新运行应新建protocol/run-id，保持同一内容和接口配置，不在旧目录覆盖结果。','',
        '仍是25道已知公开英文正例，每输入一次，语义标签来自研究助手逐题审阅，不是独立人类盲评；没有自然无答案、跨语言、企业文档或重复采样证明。没有修改SMM生产默认或旧结果。','']
    report='\n'.join(rows);write_text(DEST/'README.md',report)
    page=h.report_html(scores).replace('</html>','<details open><summary>接口与正文/协议诊断说明</summary><pre>'+html.escape(report)+'</pre></details></html>')
    write_text(DEST/'report.html',page)
    grid=['# 五模型逐题结果','',
        '✓通过；✗正文未完整答对；格式=冻结输出契约失败；失败=无可评分输出；△=原有歧义，不进回答主分。','',
        '| 题号 | 问题 | Luna 准确/筛选/混合 | Sol 准确/筛选/混合 | GLM Flash 准确/筛选/混合 | GLM-5.3 准确/筛选/混合 | DeepSeek 准确/筛选/混合 |',
        '| --- | --- | --- | --- | --- | --- | --- |']
    by={s['model']:{(r['task'],r['case_id']):r for r in s['rows']}for s in scores}
    for cid,c in h.cases().items():
        cells=[]
        for s in scores:
            symbols=[]
            for task in h.TASKS:
                r=by[s['model']][task,cid]
                symbols.append('失败'if r['state']=='generation_error'else'格式'if r['state']=='format_error'else'△'if task!='candidate_select'and r['ambiguous']else'✓'if r['correct']else'✗')
            cells.append('/'.join(symbols))
        grid.append('| '+' | '.join([cid,c['question'].replace('|','/').replace('\n',' ')]+cells)+' |')
    write_text(DEST/'case-results.md','\n'.join(grid)+'\n')
    print(h.compact(dict(report_created=True,verification_passed=True,model_calls=0,summary=ds['summary'])))

if __name__=='__main__':main()
