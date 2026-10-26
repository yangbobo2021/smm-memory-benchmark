"""Post-run audit of physical attempts and pilot reuse; no inference calls."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_429(record):
    return bool(record['error']) and '429 Too Many Requests' in record['error']['message']


def audit():
    runtime = read(HERE / 'runtime.json')
    pilot = read(HERE / 'pilot-reuse-receipts.json')
    assert len(runtime) == 257 and len({c['id'] for c in runtime}) == 257
    assert set(pilot) == {'P01', 'P07', 'L011', 'C037'}
    counts = dict(cases=257, round1=0, round2=0, reused_pilot=0,
                  new_logical_calls=0, physical_attempts=0, first_429s=0,
                  successful_429_retries=0, terminal_429s=0, other_errors=0)
    seen_attempts = set()
    for case in runtime:
        cid = case['id']
        first = read(HERE / 'records/round1' / f'{cid}.json')
        stages = ['round1']
        if first['error'] is None and first['output']['decision'] == 'insufficient':
            followup = read(HERE / 'followups' / f'{cid}.json')
            if followup['returned']:
                stages.append('round2')
        for stage in stages:
            record = first if stage == 'round1' else read(HERE / 'records/round2' / f'{cid}.json')
            request = read(HERE / 'requests' / stage / f'{cid}.json')
            assert (record['id'], record['stage'], record['model'], record['effort']) == (
                cid, stage, 'gpt-6-luna', 'high')
            assert record['request_sha256'] == request['request_sha256']
            counts[stage] += 1
            if 'reused_from' in record:
                assert stage == 'round1' and cid in pilot
                source = ROOT / record['reused_from']
                assert sha(source) == record['pilot_record_sha256'] == pilot[cid]['pilot_record_sha256']
                assert record['request_sha256'] == pilot[cid]['new_request_sha256']
                source_request = ROOT / f'experiments/smm-sufficiency-luna-pilot-001/requests/{cid}.json'
                assert sha(source_request) == record['original_pilot_request_file_sha256']
                original = read(source)
                for key in ('output', 'metrics', 'error', 'validation'):
                    assert record[key] == original[key]
                counts['reused_pilot'] += 1
                continue
            refs = record['attempt_receipts']
            assert refs in ([f'{cid}-01.json'], [f'{cid}-01.json', f'{cid}-02.json'])
            attempts = []
            for number, name in enumerate(refs, 1):
                path = HERE / 'attempts' / stage / name
                started = read(path.with_name(name[:-5] + '.started.json'))
                attempt = read(path)
                assert (attempt['id'], attempt['stage'], attempt['number'], attempt['model'], attempt['effort']) == (
                    cid, stage, number, 'gpt-6-luna', 'high')
                assert started['request_sha256'] == attempt['request_sha256'] == record['request_sha256']
                assert started['number'] == number
                if attempt['error'] is None:
                    metrics = attempt['metrics']
                    assert metrics['selected_model'] == 'gpt-6-luna'
                    assert metrics['selected_provider'] == 'openai'
                    assert metrics['tool_calls'] == 0 and metrics['ephemeral'] is True
                seen_attempts.add(path)
                attempts.append((started, attempt))
            assert len(attempts) == len(refs)
            if len(attempts) == 2:
                assert is_429(attempts[0][1])
                assert attempts[1][0]['started'] - attempts[0][0]['started'] >= 30
                counts['first_429s'] += 1
                if attempts[1][1]['error'] is None:
                    counts['successful_429_retries'] += 1
            final = attempts[-1][1]
            for key in ('output', 'metrics', 'error', 'validation'):
                assert record[key] == final[key]
            if record['error']:
                if is_429(record):
                    assert len(attempts) == 2
                    counts['terminal_429s'] += 1
                else:
                    counts['other_errors'] += 1
            counts['new_logical_calls'] += 1
            counts['physical_attempts'] += len(attempts)
    actual_attempts = {p for stage in ('round1', 'round2')
                       for p in (HERE / 'attempts' / stage).glob('*.json')
                       if not p.name.endswith('.started.json')}
    assert actual_attempts == seen_attempts
    assert counts['round1'] == 257
    assert counts['new_logical_calls'] + counts['reused_pilot'] == counts['round1'] + counts['round2']
    return counts


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2))
