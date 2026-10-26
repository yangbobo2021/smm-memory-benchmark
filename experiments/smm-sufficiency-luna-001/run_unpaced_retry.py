"""Continue SF001 without fixed pacing; retain 429 attempts and retry once after 30s."""
import argparse
import fcntl
import json
from pathlib import Path
import sys
import time

import lab

HERE = Path(__file__).resolve().parent
AMENDMENT = HERE / 'execution-amendment-unpaced-retry.json'


def pending():
    out = []
    for c in lab.read(HERE / 'runtime.json'):
        cid = c['id']
        first = HERE / 'records/round1' / f'{cid}.json'
        if not first.exists():
            out.append(cid)
            continue
        record = lab.read(first)
        if record['error'] or record['output']['decision'] == 'sufficient':
            continue
        followup = HERE / 'followups' / f'{cid}.json'
        if not followup.exists():
            out.append(cid)
            continue
        if lab.read(followup)['returned'] and not (HERE / 'records/round2' / f'{cid}.json').exists():
            out.append(cid)
    return out


def is_429(error):
    if error is None:
        return False
    message = error['message']
    return ('429 Too Many Requests' in message or '"httpStatusCode": 429' in message)


def invoke(server, cid, stage, req, sleep=time.sleep):
    folder = HERE / 'records' / stage
    dest = folder / f'{cid}.json'
    if dest.exists():
        return lab.read(dest)
    marker = folder / f'{cid}.started.json'
    assert not marker.exists(), ('unresolved started request; do not silently repeat', stage, cid)
    attempts = HERE / 'attempts' / stage
    assert not any(attempts.glob(f'{cid}-*.json')), ('unresolved attempt; do not silently repeat', stage, cid)
    lab.put(marker, dict(id=cid, stage=stage, request_sha256=req['request_sha256'], started=time.time(),
                         execution_amendment='execution-amendment-unpaced-retry.json'))
    final = None
    for number in (1, 2):
        attempt_path = attempts / f'{cid}-{number:02d}.json'
        start_path = attempts / f'{cid}-{number:02d}.started.json'
        lab.put(start_path, dict(id=cid, stage=stage, number=number,
                                 request_sha256=req['request_sha256'], started=time.time()))
        output = None
        metrics = {}
        error = None
        validation = None
        try:
            b = req['request']
            output, metrics = server.infer(b['system'], b['payload'], effort=lab.EFFORT, schema=b['schema'])
            assert metrics['selected_model'] == lab.MODEL
            assert metrics['selected_provider'] == 'openai'
            assert metrics['tool_calls'] == 0
            validation = lab.validate(output, b['payload'])
        except Exception as exc:
            error = dict(type=type(exc).__name__, message=str(exc))
        attempt = dict(id=cid, stage=stage, number=number, model=lab.MODEL, effort=lab.EFFORT,
                       request_sha256=req['request_sha256'], output=output, metrics=metrics,
                       error=error, validation=validation)
        lab.put(attempt_path, attempt)
        print(json.dumps(dict(id=cid, stage=stage, attempt=number,
                              decision=output.get('decision') if output else None,
                              seconds=metrics.get('seconds'), error=error), ensure_ascii=False), flush=True)
        final = attempt
        if is_429(error) and number == 1:
            sleep(30)
            continue
        break
    assert final is not None
    receipt = dict(id=cid, stage=stage, model=lab.MODEL, effort=lab.EFFORT,
                   request_sha256=req['request_sha256'], output=final['output'],
                   metrics=final['metrics'], error=final['error'], validation=final['validation'],
                   attempt_receipts=[f'{cid}-{n:02d}.json' for n in range(1, final['number'] + 1)])
    lab.put(dest, receipt)
    return receipt


def path(server, c, src):
    cid = c['id']
    first = invoke(server, cid, 'round1', lab.read(HERE / 'requests/round1' / f'{cid}.json'))
    if first['error']:
        return False
    output = first['output']
    if output['decision'] == 'sufficient':
        return True
    target = HERE / 'followups' / f'{cid}.json'
    if target.exists():
        followup = lab.read(target)
    else:
        started = time.perf_counter()
        ranked = lab.search(c['source_ids'], output['next_query'], src, exclude=c['initial_source_ids'])
        seconds = time.perf_counter() - started
        hits = ranked['eligible_ranked'][:5]
        extra = [x['source_id'] for x in hits]
        assert not set(extra) & set(c['initial_source_ids']) and len(extra) == len(set(extra))
        followup = dict(id=cid, query=output['next_query'], origin_response_sha256=lab.digest(output),
                        excluded_source_ids=c['initial_source_ids'], returned=hits,
                        complete_eligible_ranking=ranked['eligible_ranked'],
                        full_corpus_ranking=ranked['all_ranked'],
                        search_with_index_build_seconds=seconds,
                        visible_source_ids=c['initial_source_ids'] + extra)
        lab.put(target, followup)
    if not followup['returned']:
        return True
    request_path = HERE / 'requests/round2' / f'{cid}.json'
    if not request_path.exists():
        lab.put(request_path, lab.request(lab.document_payload(
            c, followup['visible_source_ids'], src, previous=output)))
    second = invoke(server, cid, 'round2', lab.read(request_path))
    return second['error'] is None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    lab.guard()
    amendment = lab.read(AMENDMENT)
    assert amendment['model'] == lab.MODEL and amendment['effort'] == lab.EFFORT
    assert amendment['minimum_start_interval_seconds'] == 0
    assert amendment['retry_wait_seconds'] == 30 and amendment['additional_attempts_after_429'] == 1
    todo = pending()
    if args.dry_run:
        print(json.dumps(dict(pending=len(todo), first=todo[:8], model=lab.MODEL,
                              effort=lab.EFFORT, fixed_interval_seconds=0,
                              retry_429_after_seconds=30)), flush=True)
        return
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    with (work / 'unpaced-controller.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = work / 'controller-state.json'

        def save(status):
            body = dict(status=status, time=time.time(), remaining=len(pending()),
                        minimum_start_interval_seconds=0, retry_429_after_seconds=30,
                        additional_attempts_after_429=1, requested_model=lab.MODEL,
                        effort=lab.EFFORT, workers=1)
            temp = state.with_suffix('.tmp')
            temp.write_text(json.dumps(body, indent=2) + '\n')
            temp.replace(state)

        save('running')
        sys.path.insert(0, str(lab.B))
        from codex_transport import CodexServer
        src = lab.sources()
        runtime = {c['id']: c for c in lab.read(HERE / 'runtime.json')}
        with CodexServer(work, lab.MODEL, window_limit=0) as server:
            models = server.rpc('model/list', {'includeHidden': False})['data']
            model = next(m for m in models if m['model'] == lab.MODEL)
            assert lab.EFFORT in {r['reasoningEffort'] for r in model['supportedReasoningEfforts']}
            for cid in todo:
                if not path(server, runtime[cid], src):
                    save('stopped_after_error')
                    break
                save('running')
        else_state = 'complete' if not pending() else 'stopped_before_completion'
        save(else_state)
        print(json.dumps(dict(run_ended=True, status=else_state, pending=len(pending()))), flush=True)


if __name__ == '__main__':
    main()
