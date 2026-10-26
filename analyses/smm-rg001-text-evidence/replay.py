"""Post-hoc sensitivity using the modality flags recorded before new retrieval."""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUNDLE = HERE.parents[1] / 'experiments/smm-retrieval-generalization-001'


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--check', action='store_true'); args = parser.parse_args()
    result = json.loads((BUNDLE / 'results.json').read_text())
    flags = json.loads((BUNDLE / 'provenance/modality-audit.json').read_text())
    image = {c['case_id'] for c in flags['cases_with_image_metadata_in_annotated_turns']}
    groups = {}
    for label in ['no_image_metadata', 'has_image_metadata']:
        cases = [c for c in result['cases'] if c['cohort'] == 'locomo_random200'
                 and ((c['case_id'] in image) == (label == 'has_image_metadata'))]
        rows = []
        for n in range(1, 6):
            rows.append(dict(n=n, all_reference={k: sum(c['cells'][k][n - 1]['all_reference'] for c in cases)
                                                for k in ['bm25', 'vector', 'union']}))
        groups[label] = dict(cases=len(cases), case_ids=[c['case_id'] for c in cases], rows=rows)
    output = dict(parent='SMM-RG001', design='Post-hoc subgroup analysis, no new retrieval or embeddings; fixed original scores unchanged.',
                  distinction='No image metadata in annotated turns is a conservative diagnostic flag, not a semantic proof that every question in the other group needs images.',
                  input_hashes={name: hashlib.sha256((BUNDLE / name).read_bytes()).hexdigest()
                                for name in ['results.json', 'provenance/modality-audit.json']},
                  groups=groups, generative_calls=0, embedding_calls=0)
    content = json.dumps(output, indent=2) + '\n'; path = HERE / 'results.json'
    if args.check: assert path.read_bytes() == content.encode()
    else:
        with path.open('x') as f: f.write(content)
    print(json.dumps(dict(passed=True, questions=sum(v['cases'] for v in groups.values()), groups={k:v['cases'] for k,v in groups.items()}, new_calls=0)))


if __name__ == '__main__': main()
