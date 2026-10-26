"""Create comparison reports from archived results and explicit semantic reviews."""
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
LABELS=['gpt-6-luna','gpt-6.1-sol','glm-5.3-flash-low-first','glm-5.3-low-first']

def write_text(path,text):
    with path.open('x')as f:f.write(text)

def main():
    verification=verify();scores=[h.score_run(label)for label in LABELS]
    h.write_new(DEST/'verification.json',verification)
    h.write_new(DEST/'comparison.json',dict(experiment_id='SMM-B001',runs=scores))
    diagnostics={};timing={};quality={}
    for s in scores:
        model=s['model'];diagnostics[model]={};timing[model]={};quality[model]={}
        for task in h.TASKS:
            rows=[r for r in s['rows']if r['task']==task]
            times=sorted(r['seconds']for r in rows if isinstance(r.get('seconds'),(int,float)))
            timing[model][task]=dict(successful_latency_samples=len(times),median_seconds=statistics.median(times),
                p95_success_seconds=times[math.ceil(.95*len(times))-1],max_success_seconds=max(times),
                generation_errors=[r['case_id']for r in rows if r['state']=='generation_error'],
                note='Successful requests only; read timeouts are separate. Single observations, provider defaults/cache/transport differ.')
            if task=='candidate_select':continue
            folder=h.run_path(s['run_id']);reviews={r['case_id']:r for r in h.read(folder/'reviews.json')['answer_reviews']if r['task']==task}
            clear=[r for r in rows if not r['ambiguous']]
            content=sum(reviews.get(r['case_id'],{}).get('complete_answer')is True for r in clear)
            diagnostics[model][task]=dict(semantic_content_correct=content,clear_questions=len(clear),
                generated_clear_answers=sum('output'in r for r in clear),
                semantic_wrong_case_ids=[r['case_id']for r in clear if reviews.get(r['case_id'],{}).get('complete_answer')is False],
                format_error_case_ids=[r['case_id']for r in rows if r['state']=='format_error'],
                generation_error_case_ids=[r['case_id']for r in rows if r['state']=='generation_error'],
                note='Diagnostic only: reads actual semantic review even where frozen primary rejects duplicate source IDs. Does not replace the frozen metric.')
            markers=[]
            for r in rows:
                missing=r.get('output',{}).get('missing','')
                if any(v in missing for v in ['</think>','Oops, correction','FINAL-CANONICAL']):
                    markers.append(dict(case_id=r['case_id'],missing_characters=len(missing)))
            quality[model][task]=dict(non_verbatim_quote_case_ids=[r['case_id']for r in rows if r.get('mechanical',{}).get('quote_valid')is False],
                duplicate_source_id_case_ids=[r['case_id']for r in rows if'duplicate selected source'in r.get('mechanical',{}).get('errors',[])],
                missing_field_marker_cases=markers,
                missing_marker_definition='Literal </think>, Oops, correction, or FINAL-CANONICAL in missing. Descriptive diagnostic, not a new scoring rule.')
    h.write_new(DEST/'semantic-content-diagnostic.json',diagnostics)
    h.write_new(DEST/'timing.json',timing);h.write_new(DEST/'output-quality.json',quality)
    lines=['# SMM-B001：GLM-5.3-Flash / GLM-5.3 对比','',
        '日期：2026-10-26。新Key接入成功后执行每模型25题×3任务，共150次正式首次请求；148次获得输出、2次读取超时。另4次接入探测不计成绩。没有重试失败题、语义重抽、重新检索或重新向量化。','',
        '## 固定基线主分数','',
        '本表完全沿用冻结程序：除了答案语义，格式失败和生成失败也不能通过。逐字引用和全部主张支持是另列更严格指标。','',
        '| 模型（low） | 准确上下文完整回答 | 混合Top5筛选 | 混合Top5完整回答 |','| --- | ---: | ---: | ---: |']
    for s in scores:
        vals=[str(s['summary'][t]['primary_correct'])+'/'+str(s['summary'][t]['primary_denominator'])for t in h.TASKS]
        lines.append('| '+s['model']+' | '+' | '.join(vals)+' |')
    lines+=['',
        '回答分母23，P22/P25原有适用歧义仍单列，全部25题和原参考都保留。筛选分母25，以必要信息选齐且没有确认的无关误选为准，不要求把重复历史旁证全部选中。','',
        '**相同分数不等于相同原因。** GLM-5.3的准确上下文20/23中，两题（P01/P03）正文正确但来源编号重复，一题（P06）90秒读取超时；混合回答21/23中，两题（P15/P20）正文正确但编号重复。未修正输出、去重后重算主分，或偷偷改冻结程序。','',
        '## 答案正文诊断（不是替换主分）','',
        '| 模型 | 准确上下文正文正确/23 | 混合候选正文正确/23 |','| --- | ---: | ---: |']
    for s in scores:
        d=diagnostics[s['model']]
        lines.append('| '+s['model']+' | '+str(d['oracle_answer']['semantic_content_correct'])+'/23 | '+str(d['candidate_answer']['semantic_content_correct'])+'/23 |')
    lines+=['',
        'GLM-5.3准确上下文为22/23：22个已生成的明确题答案正文都正确，另一题没有获得输出。其混合候选23/23个正文正确仍不代表格式、所有引用和附加细节都正确。这个诊断只区分故障，不更改原评分。','',
        '## 关键实证','',
        '- Flash混合候选P07答2场，排除了Mike的BBQ；完整USER后文明确把Mike家聚会也列入dinner parties。原文已提供，属于证据使用错误。准确上下文时Flash答3。',
        '- Flash混合P21把毕业先后理解成毕业名次，明知三个人的日期可比较仍拒答，且把July15前两周说成六月初；准确上下文时能答对Emma→Rachel→Alex。',
        '- Flash独立筛选25/25，36/36必要要点，43/43基准源；GLM-5.3为24/25、35/36、41/43，漏P25新7AM来源，另省略P04旧收入只是冗余历史，不算必要漏选。两者所选结果均无观察到无关来源（0/43、0/41），不是全库FPR。',
        '- GLM-5.3在P23两次14天答案都正确，但claims只提供换盆引句，未为送枝条事件给出引句；P21混合的最终顺序正确但Alex附加日期概括不准。不能用核心答案正确替代引证完整。',
        '- Flash的P18 missing字段出现重复自我修正文本及控制样式标记，准确上下文输出该字段长3374字符；GLM-5.3的P12也出现少量自我修正文本。都保留原输出，不能解释为服务端根因已查明。','',
        '## 耗时','',
        '下表为成功请求中位秒数；超时单列，不能当成端到端APP延迟、稳定P95或纯模型速度因果。GLM两模型进程各自串行、进程之间并行，后段只剩一个进程；服务端缓存与排队未控制。','',
        '| 模型 | 准确上下文回答 | 筛选 | 混合候选回答 |','| --- | ---: | ---: | ---: |']
    for s in scores:
        lines.append('| '+s['model']+' | '+' | '.join(f"{timing[s['model']][t]['median_seconds']:.2f}"for t in h.TASKS)+' |')
    lines+=['',
        'GLM-5.3在P06准确上下文、Flash在P25准确上下文各出现一次90秒读取超时；原因未确证，不能归因于题目难、模型思考或服务排队中的某一项。成功延迟分布和错误题分别保存在timing.json。','',
        '## 控制因素与执行例外','',
        '固定SMM-B001的75份输入（system、payload、schema）、原始会话、候选集合、排列和评分，未向模型泄露参考答案/证据要点。两GLM使用同一冻结http_transport.py、Coding端点、low与json_schema；thinking为服务默认enabled（模型仅支持开启），temperature/max_tokens使用服务默认，不伪称固定了所有采样参数。','',
        'OpenAI基线使用Codex订阅包装，GLM使用HTTP包装。任务可见数据保持一致，服务接口、隐藏包装、分词、缓存及默认参数仍有区别；跨供应商成绩是当前调用组合的结果，不能声称只改变了模型权重。模型身份核对依据服务回显，不是独立认证。','',
        '初始runner各在首个超时后停止，初始failed completion原样保留。随后在继续之前登记continuation-amendment.json及Flash补充，只执行尚未请求的59/2个独立任务，保留并校验原16/73条记录hash。未再次请求两个失败输入，总计仍150个唯一正式任务各一次。原协议的停止策略有显式补充，不能说整个调度协议从未变化。','',
        '## 复现与文件','',
        '从本实验根目录执行：','',
        '```bash','python3 bench.py verify',
        'python3 artifacts/glm-comparison-v1/verify_comparison.py',
        'python3 bench.py score --run glm-5.3-flash-low-first',
        'python3 bench.py score --run glm-5.3-low-first',
        'python3 bench.py report --runs gpt-6-luna,gpt-6.1-sol,glm-5.3-flash-low-first,glm-5.3-low-first --out artifacts/new-four-model-report.html','```','',
        '- ../../runs/（即根目录runs/）：每模型75首次结果、开始标记、初始停止记录、继续记录、49个语义复核及封存hash。',
        '- protocol.json、continuation-amendment*.json：推理前协议与后续停止策略补充。',
        '- comparison.json / report.html：四模型详细评分。',
        '- case-results.md：逐题主分、格式/超时状态。',
        '- manual-review-decisions.json：98个已生成答案的逐题语义判定与输入/输出hash；两超时不编造语义判断。',
        '- semantic-content-diagnostic.json、output-quality.json、timing.json：正文、引用/格式及时间分离。',
        '- verify_comparison.py / verification.json：机械完整性核验，不代替独立语义金标。','',
        '25道已讨论过的英文公开正例，每输入一次；没有自然无答案题、跨语言/企业文档覆盖、随机种子重复或独立人类盲评。原生json_schema模式下的附加输出问题尚未与其他模式消融。','',
        '本轮支持继续使用SMM已有候选召回，并把模型答题、筛选和输出契约分开评价。Sol在这批题最稳；Flash筛选完整但有两处混合作答错误；GLM-5.3正文表现较好，同时存在漏选、超时、重复编号及引证缺口。没有证明某个GLM全面优于另一模型，也没有据此修改生产默认。','']
    report='\n'.join(lines);write_text(DEST/'README.md',report)
    page=h.report_html(scores)
    diagnostic_html='<details open><summary>本轮解释：格式失败与正文错误分开</summary><pre>'+html.escape(report)+'</pre></details>'
    write_text(DEST/'report.html',page.replace('</html>',diagnostic_html+'</html>'))
    rows=['# 四模型逐题固定基线结果','',
        '✓通过；✗核心语义未完成；格式=重复来源编号；超时=未得到输出；△=原有歧义题，不进回答主分。即使标为格式/超时，也保留25题。','',
        '| 题号 | 问题 | Luna 准确/筛选/混合 | Sol 准确/筛选/混合 | Flash 准确/筛选/混合 | GLM-5.3 准确/筛选/混合 |',
        '| --- | --- | --- | --- | --- | --- |']
    by={s['model']:{(r['task'],r['case_id']):r for r in s['rows']}for s in scores}
    for cid,c in h.cases().items():
        cells=[]
        for s in scores:
            symbols=[]
            for task in h.TASKS:
                r=by[s['model']][task,cid]
                symbols.append('超时'if r['state']=='generation_error'else'格式'if r['state']=='format_error'else'△'if task!='candidate_select'and r['ambiguous']else'✓'if r['correct']else'✗')
            cells.append('/'.join(symbols))
        rows.append('| '+' | '.join([cid,c['question'].replace('|','/').replace('\n',' ')]+cells)+' |')
    write_text(DEST/'case-results.md','\n'.join(rows)+'\n')
    print(h.compact(dict(reports_created=True,models=4,verification_passed=True,new_model_calls=0)))

if __name__=='__main__':main()
