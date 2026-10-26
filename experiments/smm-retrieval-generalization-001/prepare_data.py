"""Freeze two new retrieval cohorts before indexing or viewing new ranks."""
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
PROJECT = Path('/Users/boboyang/work/next-app')
SEED = 'smm-new-retrieval-20261026-v1'


def read(p): return json.loads(p.read_text())
def digest(b): return hashlib.sha256(b).hexdigest()
def textsha(s): return digest(s.encode())
def write(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f: f.write(json.dumps(x, ensure_ascii=False, indent=2) + '\n')


def clock(s):
    s = re.sub(r' \([^)]*\)', '', s)
    return dt.datetime.strptime(s, '%Y/%m/%d %H:%M').replace(tzinfo=dt.timezone.utc).isoformat()


def serialize(turns):
    text = ''; spans = []
    for i, t in enumerate(turns):
        text += ('\n\n' if i else '') + t['role'].upper() + ':\n'
        a = len(text); text += t['content']
        spans.append(dict(turn=i, role=t['role'], start=a, end=len(text)))
    return text, spans


def main():
    assert not (HERE / 'protocol.json').exists()
    old_audit = read(PROJECT / 'work/smm-random-retrieval-planning-20261026/prior-question-audit.json')
    used = {x['question_id'] for x in old_audit['excluded_questions']}
    write(HERE / 'provenance/prior-question-audit.json', old_audit)
    write(HERE / 'provenance/legacy-replay.json', read(PROJECT / 'work/smm-random-retrieval-planning-20261026/legacy-replay.json'))
    cases = []; sources = {}; excluded = []

    def add_source(turns, when, provenance, extra_parts=None):
        text, spans = serialize(turns)
        sid = 'c' + textsha(text + '\0' + when)[:24]
        r = dict(id=sid, text=text, received_at=when, source_sha256=textsha(text),
                 structure=dict(source_sha256=textsha(text), parts=spans))
        if extra_parts:
            for p, extra in zip(r['structure']['parts'], extra_parts): p.update(extra)
        if sid in sources:
            assert sources[sid]['text'] == text and sources[sid]['received_at'] == when
        else:
            sources[sid] = dict(**r, provenance=provenance)
        return sid

    raw_path = PROJECT / 'data/external/longmemeval/longmemeval_s_cleaned.json'
    raw = read(raw_path)
    pool = [x for x in raw if x['question_id'] not in used and not x['question_id'].endswith('_abs')]
    pool.sort(key=lambda x: textsha(SEED + '\0' + x['question_id']))
    for x in pool:
        dates = {sid: clock(date) for sid, date in zip(x['haystack_session_ids'], x['haystack_dates'])}
        future = [sid for sid in x['answer_session_ids'] if dates[sid] > clock(x['question_date'])]
        if future:
            excluded.append(dict(question_id=x['question_id'], reason='official reference later than question',
                                 question_clock=clock(x['question_date']), reference_clocks={s: dates[s] for s in future}))
            continue
        ids = []; refs = []; witnesses = []; mapping = {}
        for external, date, session in zip(x['haystack_session_ids'], x['haystack_dates'], x['haystack_sessions']):
            when = clock(date)
            if when > clock(x['question_date']): continue
            sid = add_source([dict(role=t['role'], content=t['content']) for t in session], when,
                             dict(dataset='LongMemEval-cleaned', external_session_id=external))
            ids.append(sid); mapping[external] = sid
            if external in x['answer_session_ids']:
                refs.append(sid)
                for t, span in zip(session, sources[sid]['structure']['parts']):
                    if t.get('has_answer'):
                        witnesses.append(dict(source_id=sid, start=span['start'], end=span['end'], role=span['role'], quote=t['content']))
        assert set(x['answer_session_ids']) <= mapping.keys()
        cases.append(dict(id='L' + str(len(cases) + 1).zfill(3), cohort='longmemeval_new32', family=x['question_id'],
                          question=x['question'], known_at=clock(x['question_date']), timezone='UTC',
                          type=x['question_type'], source_ids=sorted(set(ids)), official_reference_sources=sorted(set(refs)),
                          official_reference_answer_evaluation_only=x['answer'], marked_turns_evaluation_only=witnesses,
                          official_id_mapping=mapping))
    assert len(cases) == 32 and len(excluded) == 37

    loco_base = PROJECT / 'data/external/locomo'
    loco = read(loco_base / 'locomo10.json')
    loco_sources = {}; eligible = []; bad_loco = []
    for s in loco:
        family = s['sample_id']; conv = s['conversation']; ids = []; turns = {}; session_map = {}
        for key in sorted((k for k in conv if re.fullmatch(r'session_\d+', k)), key=lambda k: int(k.split('_')[1])):
            date = dt.datetime.strptime(conv[key + '_date_time'], '%I:%M %p on %d %B, %Y').replace(tzinfo=dt.timezone.utc).isoformat()
            # Preserve both speakers' names without inventing assistant responses.
            messages = [dict(role=t['speaker'], content=t['text']) for t in conv[key]]
            extra = [dict(dialogue_id=t['dia_id']) for t in conv[key]]
            sid = add_source(messages, date, dict(dataset='LoCoMo', sample_id=family, session=key), extra)
            ids.append(sid); session_map[key] = sid
            for t, span in zip(conv[key], sources[sid]['structure']['parts']):
                assert t['dia_id'] not in turns
                turns[t['dia_id']] = dict(source_id=sid, start=span['start'], end=span['end'], role=span['role'], quote=t['text'])
        loco_sources[family] = dict(ids=ids, turns=turns, known_at=max(sources[sid]['received_at'] for sid in ids))
        for i, q in enumerate(s['qa']):
            if q['category'] == 5: continue
            # Exact official evidence IDs only. Invalid/missing annotations are
            # excluded before any ranking, with a complete audit trail.
            evidence = q.get('evidence', [])
            unknown = [eid for eid in evidence if eid not in turns]
            if not evidence or unknown:
                bad_loco.append(dict(sample_id=family, question_index=i, category=q['category'],
                                     reason='missing evidence' if not evidence else 'unresolved exact evidence ID', evidence=evidence))
                continue
            eligible.append(dict(family=family, question_index=i, qa=q))
    eligible.sort(key=lambda x: textsha(SEED + '\0LoCoMo\0' + x['family'] + '\0' + str(x['question_index'])))
    chosen = eligible[:200]
    assert len(chosen) == 200 and len({x['family'] for x in chosen}) == 10
    for i, x in enumerate(chosen, 1):
        family = x['family']; q = x['qa']; d = loco_sources[family]
        witnesses = [dict(d['turns'][eid], dialogue_id=eid) for eid in q['evidence']]
        cases.append(dict(id=f'C{i:03d}', cohort='locomo_random200', family=family,
                          question_index=x['question_index'], question=q['question'], known_at=d['known_at'], timezone='UTC',
                          type=str(q['category']), source_ids=sorted(d['ids']),
                          official_reference_sources=sorted({w['source_id'] for w in witnesses}),
                          official_reference_answer_evaluation_only=q['answer'], marked_turns_evaluation_only=witnesses))
    # Persist only sources belonging to selected questions.
    wanted = {sid for c in cases for sid in c['source_ids']}
    sources = {sid: sources[sid] for sid in sorted(wanted)}
    write(HERE / 'data/cases.json', cases)
    for sid, r in sources.items(): write(HERE / 'data/sources' / (sid + '.json'), r)
    write(HERE / 'provenance/eligibility.json', dict(longmemeval_unmentioned_positives=len(pool),
          longmemeval_pre_rank_time_exclusions=excluded, longmemeval_included=32,
          locomo_eligible_positive_questions=len(eligible), locomo_annotation_exclusions=bad_loco,
          locomo_sampled_question_keys=[dict(sample_id=x['family'], question_index=x['question_index']) for x in chosen],
          note='No exclusions or replacement after retrieval; original labels retained. Category5 is not part of positive-source coverage.'))
    write(HERE / 'provenance/longmemeval.json', dict(read(PROJECT / 'data/external/longmemeval/provenance.json'), local_dataset_sha256=digest(raw_path.read_bytes())))
    write(HERE / 'provenance/locomo.json', read(loco_base / 'provenance.json'))
    for name, source in [('LoCoMo-CC-BY-NC-4.0.txt', loco_base / 'LICENSE.txt'),
                         ('LongMemEval-MIT.txt', PROJECT / 'data/external/longmemeval/official/LICENSE')]:
        dest = HERE / 'licenses' / name; dest.parent.mkdir(exist_ok=True); shutil.copyfile(source, dest)
    implementation = ['smm_control_index.py', 'source_match_presentation.py', 'vector_recall_probe.py', 'conversation_topics.py']
    package = HERE / 'implementation/next_memory'; package.mkdir(parents=True)
    (package / '__init__.py').write_text('')
    for name in implementation: shutil.copyfile(PROJECT / 'src/next_memory' / name, package / name)
    files = {str(p.relative_to(HERE)): digest(p.read_bytes()) for p in HERE.rglob('*') if p.is_file()}
    protocol = dict(id='SMM-RG001', seed=SEED, frozen_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        cohorts=dict(longmemeval_new32='All 32 never-mentioned, positive, time-valid cases remaining in the fixed 500-question dataset, randomized order.',
                     locomo_random200='First200 SHA256(seed + NUL + LoCoMo + NUL + sample_id + NUL + question_index) from eligible official positives; uniform pseudo-random question sample, no replacement.'),
        independence='New to local retrieval experiments, not guaranteed absent from model training. LoCoMo200 share10 histories; do not treat them as200 independent histories. No pooling of cohorts.',
        retrieval='Byte-identical SMMControlIndex and lexical_expression; whole-source SQLiteFTS5 unicode61 BM25; original question OR tokens, no stemming/stopword removal/rewrite; all-MiniLM-L6-v2 max-chunk dot product; original256/48 chunks,224/32 normalized mean encoder,384dim; no AI reranker.',
        time='LongMemEval: all and only original sources at or before question time, no synthetic fillers or gold-guided corpus truncation. LoCoMo: end-of-history retrospective questions, all original dated sessions for that family; clock=latest session time, no fabricated question date. UTC is an explicit timezone convention.',
        unit='One original dated session is one full conversation source. Both LoCoMo speaker names retained as literal headers. Text modality only; no generated observations, summaries, event summaries, captions or image search queries indexed.',
        metrics='For N1..5: all official reference sessions selected / questions; any-reference hit, reference recall and mean candidate count/characters separately. Union takes each route TopN, deduplicated; no score fusion. By type and reference-session count, paired wins/losses, family-level results. Primary labels read by scorer after ranks are frozen.',
        evidence='Official reference conversation/turn annotations only; no new hand-derived necessary-fact atoms. All-reference misses do not necessarily prove no sufficient alternative evidence. LoCoMo exact annotated evidence IDs must resolve before sampling; exclusions logged without inspecting ranks.',
        legacy_control='Before new ranks, original25 questions replayed with exact50 routeTop10 orders and scores; provenance/legacy-replay.json. Original benchmark not changed.',
        engineering='Same-model raw-text content cache, source chunks computed once per unique source. Batch inference may change roundoff only; fixed semantic contract checked against original single-input encoder. No paid/generative calls, selection, answering or query iteration.',
        comparison='Compare old25 only on the same all-official-reference metric; do not compare new official-reference coverage directly with old36 custom evidence atoms. New cohorts and corpus distributions are separate, not a model-only causal comparison.',
        decision='Test whether BM25 Top4 all-reference coverage generalizes. Retain all post-freeze failures; do not tune method, thresholds or sample after scores.',
        frozen_files=files, native_queries_at_freeze=0, new_document_encodes_at_freeze=0, generative_calls_budget=0)
    write(HERE / 'protocol.json', protocol)
    print(json.dumps(dict(frozen=True, cases=len(cases), sources=len(sources), cohorts=dict(collections.Counter(c['cohort'] for c in cases)),
                          source_scale={cohort:[min(len(c['source_ids']) for c in cases if c['cohort']==cohort),max(len(c['source_ids']) for c in cases if c['cohort']==cohort)] for cohort in sorted({c['cohort'] for c in cases})}), ensure_ascii=False), flush=True)


if __name__ == '__main__': main()
