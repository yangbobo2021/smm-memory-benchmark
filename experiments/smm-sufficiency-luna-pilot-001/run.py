"""Small, isolated GPT-6 Luna high pilot over frozen SF001 first-round inputs."""
import hashlib
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SF = ROOT / 'experiments/smm-sufficiency-001'
BASE = ROOT / 'experiments/smm-baseline-001'
MODEL = 'gpt-6-luna'
EFFORT = 'high'
CASES = ('P01', 'C037', 'L011', 'P07')

sys.path.insert(0, str(SF))
sys.path.insert(0, str(BASE))
from contract import validate  # noqa: E402
from codex_transport import CodexServer  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as out:
        json.dump(obj, out, ensure_ascii=False, indent=2)
        out.write('\n')


def prepare():
    if (HERE / 'protocol.json').exists():
        return
    source_hashes = {}
    for case in CASES:
        source = SF / 'requests/round1' / f'{case}.json'
        original = json.loads(source.read_text())['request']
        assert original['model'] == 'gpt-6.1-sol' and original['effort'] == EFFORT
        copied = dict(original, model=MODEL)
        assert copied['system'] == original['system']
        assert copied['payload'] == original['payload']
        assert copied['schema'] == original['schema']
        source_hashes[case] = sha(source)
        save_new(HERE / 'requests' / f'{case}.json', copied)
    save_new(HERE / 'protocol.json', dict(
        id='SMM-SF-LUNA-PILOT-001', cases=CASES, model=MODEL, effort=EFFORT,
        purpose='Output and transport pilot; not a 257-case accuracy estimate',
        original_request_sha256=source_hashes,
        input='identical SF001 round1 system, payload, output schema; only model changed',
        order=list(CASES), minimum_start_interval_seconds=45,
        application_retries=0, stop_on_service_error=True,
        comparison='SF001 first-round Sol high receipt for the same case',
    ))


def run():
    protocol = json.loads((HERE / 'protocol.json').read_text())
    assert protocol['model'] == MODEL and protocol['effort'] == EFFORT
    assert tuple(protocol['cases']) == CASES
    for case in CASES:
        assert sha(SF / 'requests/round1' / f'{case}.json') == protocol['original_request_sha256'][case]
        original = json.loads((SF / 'requests/round1' / f'{case}.json').read_text())['request']
        copied = json.loads((HERE / 'requests' / f'{case}.json').read_text())
        assert copied == dict(original, model=MODEL)
    with CodexServer(HERE, MODEL, window_limit=1, window_seconds=45) as server:
        models = server.rpc('model/list', {'includeHidden': False})['data']
        model = next(m for m in models if m['model'] == MODEL)
        supported = {x['reasoningEffort'] for x in model['supportedReasoningEfforts']}
        assert EFFORT in supported, supported
        availability = dict(model=MODEL, supported_reasoning_efforts=sorted(supported))
        availability_path = HERE / 'model-availability.json'
        if availability_path.exists():
            assert json.loads(availability_path.read_text()) == availability
        else:
            save_new(availability_path, availability)
        print(json.dumps(dict(model=MODEL, high_supported=True)), flush=True)
        for case in CASES:
            dest = HERE / 'records' / f'{case}.json'
            if dest.exists():
                continue
            req = json.loads((HERE / 'requests' / f'{case}.json').read_text())
            save_new(HERE / 'records' / f'{case}.started.json', dict(case=case, started=time.time(), request_sha256=sha(HERE / 'requests' / f'{case}.json')))
            output = None
            metrics = {}
            validation = None
            error = None
            try:
                output, metrics = server.infer(req['system'], req['payload'], effort=EFFORT, schema=req['schema'])
                assert metrics['selected_model'] == MODEL
                assert metrics['selected_provider'] == 'openai'
                assert metrics['tool_calls'] == 0
                validation = validate(output, req['payload'])
            except Exception as exc:
                error = dict(type=type(exc).__name__, message=str(exc))
            save_new(dest, dict(case=case, model=MODEL, effort=EFFORT, output=output,
                                metrics=metrics, validation=validation, error=error,
                                request_sha256=sha(HERE / 'requests' / f'{case}.json')))
            print(json.dumps(dict(case=case, decision=output.get('decision') if output else None,
                                  seconds=metrics.get('seconds'), error=error), ensure_ascii=False), flush=True)
            if error:
                break


if __name__ == '__main__':
    prepare()
    run()
