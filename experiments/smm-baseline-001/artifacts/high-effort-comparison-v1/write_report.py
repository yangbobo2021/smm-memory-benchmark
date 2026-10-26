"""Offline paired low/high scores, semantic diagnostics, timings, and case changes."""
import html
import math
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(Path(__file__).resolve().parent))
import harness as h
from verify_high import verify

def text_new(path,s):
    with path.open('x')as f:f.write(s)

def main():
    phase=Path(__file__).resolve().parent;p=h.read(phase/'protocol.json');proof=verify();h.write_new(phase/'verification.json',proof)
    pairs=[];latency={};content={};changes={};usage={}
    lines=['# SMM-B001：五模型 Low / High 固定对照','',
        '冻结25题×3任务，每模型75个high首次逻辑调用，共375。重用相同完整原文、候选、问题、时钟、schema和评分；无新检索、编码、压缩或模型裁判。只改每个模型对应接口的low→high；旧结果不覆盖。','',
        '## 冻结主分（Low → High）','',
        'P22/P25时间适用歧义单列，回答主分母23；筛选主分母25，以必要信息齐全且无确认无关误选为准。格式/生成失败不能通过主分；status=partial本身不决定对错。','',
        '| 模型 | 准确上下文回答 /23 | 混合Top5筛选 /25 | 混合Top5回答 /23 |','| --- | ---: | ---: | ---: |']
    for model,spec in p['models'].items():
        low=h.score_run(spec['low']);high=h.score_run(spec['run_id']);pairs.append(dict(model=model,low=low,high=high))
        lines.append('| '+model+' | '+' | '.join(f"{low['summary'][t]['primary_correct']} → {high['summary'][t]['primary_correct']}"for t in h.TASKS)+' |')
        latency[model]={};content[model]={};changes[model]={};usage[model]={}
        for label,s in [('low',low),('high',high)]:
            folder=h.run_path(s['run_id']);reviews={(v['task'],v['case_id']):v for v in h.read(folder/'reviews.json')['answer_reviews']}
            latency[model][label]={};content[model][label]={};usage[model][label]={}
            for task in h.TASKS:
                rows=[r for r in s['rows']if r['task']==task];times=sorted(r['seconds']for r in rows if isinstance(r.get('seconds'),(int,float)))
                attempted=[h.read(folder/'records'/task/(r['case_id']+'.json'))for r in rows if r['recorded']]
                durations=[r.get('metrics',{}).get('seconds')for r in attempted];durations=[v for v in durations if isinstance(v,(int,float))]
                latency[model][label][task]=dict(returned_samples=len(times),median_returned_seconds=statistics.median(times)if times else None,
                    p95_returned_seconds=times[math.ceil(.95*len(times))-1]if times else None,max_returned_seconds=max(times)if times else None,
                    generation_errors=[r['case_id']for r in rows if r['state']=='generation_error'],
                    available_attempt_duration_samples=len(durations),median_available_attempt_duration=statistics.median(durations)if durations else None,
                    note='Returned latency excludes no-output failures; available attempt durations are supplementary and may be absent in old failed receipts.')
                totals={}
                for r in attempted:
                    for k,v in r.get('metrics',{}).get('usage',{}).items():
                        if isinstance(v,(int,float))and not isinstance(v,bool):totals[k]=totals.get(k,0)+v
                usage[model][label][task]=dict(provider_reported_usage_sums=totals,scope='Available receipt usage only; different supplier accounting and caches; no billing total or equal compute claim.')
                if task!='candidate_select':
                    clear=[r for r in rows if not r['ambiguous']]
                    content[model][label][task]=dict(semantic_content_correct=sum(reviews.get((task,r['case_id']),{}).get('complete_answer')is True for r in clear),denominator=len(clear),
                        semantic_wrong=[r['case_id']for r in clear if reviews.get((task,r['case_id']),{}).get('complete_answer')is False],
                        format_errors=[r['case_id']for r in rows if r['state']=='format_error'],generation_errors=[r['case_id']for r in rows if r['state']=='generation_error'],
                        strict_supported_correct=s['summary'][task]['strict_supported_correct'],exact_quote_valid=s['summary'][task]['exact_quote_valid'])
        for task in h.TASKS:
            a={r['case_id']:r for r in low['rows']if r['task']==task};b={r['case_id']:r for r in high['rows']if r['task']==task}
            ids=[cid for cid in a if task=='candidate_select'or not a[cid]['ambiguous']]
            changes[model][task]=dict(high_only_pass=[cid for cid in ids if b[cid]['correct']is True and a[cid]['correct']is not True],
                low_only_pass=[cid for cid in ids if a[cid]['correct']is True and b[cid]['correct']is not True],
                both_pass=[cid for cid in ids if a[cid]['correct']is True and b[cid]['correct']is True],
                both_fail=[cid for cid in ids if a[cid]['correct']is not True and b[cid]['correct']is not True])
    lines+=['','## High 执行完整性','',
        '| 模型 | 首次逻辑调用 | 返回输出 | 无输出失败 |','| --- | ---: | ---: | ---: |']
    for result in proof['models']:
        lines.append('| '+result['model']+' | '+str(result['calls'])+' | '+str(result['generated'])+' | '+str(len(result['errors']))+' |')
    lines+=['','每对任务仅一个首次应用层调用；失败保留，不补跑取更优分数。HTTP读取超时按预先冻结协议只继续后续未尝试任务。','',
        '## 正文正确与格式/生成失败分开','',
        '| 模型 | 准确上下文正文 /23（Low→High） | 混合候选正文 /23（Low→High） |','| --- | ---: | ---: |']
    for pair in pairs:
        m=pair['model'];lines.append('| '+m+' | '+' | '.join(str(content[m]['low'][t]['semantic_content_correct'])+' → '+str(content[m]['high'][t]['semantic_content_correct'])for t in ['oracle_answer','candidate_answer'])+' |')
    lines+=['','正文表仅诊断，不修补首输出或替代冻结主分。分母仍含23道明确题，无输出不会记正文正确；不将无输出称为事实答错。逐字引文、所有附加主张支持、必要核心依据支持另见diagnostics.json和reviews。输出引用的ID正确不代表引文支持答案。','',
        '## 返回耗时中位数（秒，Low → High）','',
        '| 模型 | 准确上下文回答 | 筛选 | 混合候选回答 |','| --- | ---: | ---: | ---: |']
    for pair in pairs:
        m=pair['model'];lines.append('| '+m+' | '+' | '.join(f"{latency[m]['low'][t]['median_returned_seconds']:.2f} → {latency[m]['high'][t]['median_returned_seconds']:.2f}"for t in h.TASKS)+' |')
    lines+=['','成功返回的首输出均计入耗时，即使格式或正文错误；无输出失败单列timing.json，不把超时当0秒或混成事实答错。此为服务函数观测，非APP端到端、非独立P95估计。','',
        '## 逐题主分变化','']
    for pair in pairs:
        m=pair['model'];lines.append('- '+m+'：'+'；'.join(t+' 改善['+','.join(changes[m][t]['high_only_pass'])+']，退步['+','.join(changes[m][t]['low_only_pass'])+']'for t in h.TASKS))
    observations=phase/'observations.md'
    if observations.exists():lines+=['',observations.read_text()]
    lines+=['','## 比较边界与复现','',
        '每题每档一次，本轮与旧low不是同一时间随机交错重复；运行调度与缓存不同，供应商模型别名亦可能更新。逐题变化是观察结果，不能把全部差异归因思考档位，不能由25道已知英文正例推通用排名。没有自然无答案或企业文档泛化验证。','',
        '保留各自low接口：GPT走原Codex订阅封装，GLM走原Coding Chat/native json_schema，DeepSeek走原json_object加相同schema格式附录（其原生json_schema不可用）。只改各自effort，不把不同供应商high当成相同计算预算。GPT原transport原样保留，其底层网络行为由Codex运行时管理；本测试无应用层重试/语义重抽，不把逻辑函数调用数冒充可观测全部底层HTTP请求数。','',
        '75个HTTP DeepSeek high实际wire hashes、原输入hash、代码hash在推理前冻结；375任务的首次记录、启动标记、错误/用量、实际生成答案语义复核与旧low原结果全部可追溯。凭证和隐藏思考正文不保存。研究助手逐题复核，非外部独立人类盲评；没有使用额外模型裁判。','',
        '在实验根目录使用Python>=3.11；以下离线命令不调用模型：','',
        '```bash','python3 -B artifacts/high-effort-comparison-v1/verify_high.py',
        'python3 -B bench.py score --run gpt-6-luna-high-first',
        'python3 -B bench.py report --runs gpt-6-luna,gpt-6-luna-high-first,gpt-6.1-sol,gpt-6.1-sol-high-first,glm-5.3-flash-low-first,glm-5.3-flash-high-first,glm-5.3-low-first,glm-5.3-high-first,deepseek-flash-low-first,deepseek-flash-high-first --out artifacts/new-low-high-report.html','```','',
        '新模型或新档位需新protocol/run-id，不覆盖旧首结果。未修改SMM生产默认。','']
    report='\n'.join(lines);text_new(phase/'README.md',report)
    h.write_new(phase/'comparison.json',dict(pairs=pairs,paired_primary_changes=changes));h.write_new(phase/'diagnostics.json',content)
    h.write_new(phase/'timing.json',latency);h.write_new(phase/'usage.json',usage)
    page=h.report_html([s for pair in pairs for s in[pair['low'],pair['high']]])
    page=page.replace('</html>','<details open><summary>Low/High 配对与边界</summary><pre>'+html.escape(report)+'</pre></details></html>')
    text_new(phase/'report.html',page)
    grid=['# 五模型 Low / High 逐题主分','',
        '每格依次为准确上下文回答/筛选/混合候选回答；每项Low→High。✓通过，✗正文/必要信息不足，格式=契约失败，失败=无输出，△=歧义单列。','',
        '| 题号 | 问题 | '+' | '.join(pair['model']for pair in pairs)+' |','| --- | --- | '+' | '.join('---'for _ in pairs)+' |']
    def symbol(row):
        return '失败'if row['state']=='generation_error'else'格式'if row['state']=='format_error'else'△'if row['task']!='candidate_select'and row['ambiguous']else'✓'if row.get('correct')else'✗'
    for cid,c in h.cases().items():
        cells=[]
        for pair in pairs:
            sides=[{(r['task'],r['case_id']):r for r in pair[k]['rows']}for k in ['low','high']]
            cells.append(' / '.join(symbol(sides[0][t,cid])+'→'+symbol(sides[1][t,cid])for t in h.TASKS))
        grid.append('| '+' | '.join([cid,c['question'].replace('|','/').replace('\n',' ')]+cells)+' |')
    text_new(phase/'case-results.md','\n'.join(grid)+'\n')
    print(h.compact(dict(report_created=True,verification_passed=True,formal_calls=proof['formal_calls'],new_model_calls_for_reporting=0)))

if __name__=='__main__':main()
