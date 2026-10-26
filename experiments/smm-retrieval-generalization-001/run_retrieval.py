"""Execute the unchanged source BM25 / max-chunk MiniLM retrieval methods.

Build encodes each unique source chunk once, reuses exact existing vectors when
supplied, and saves all document/query vectors for index-free numerical replay.
No LLM, credentials, HTTP gateway, summaries, question rewriting or score fusion.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sqlite3
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'implementation'))
from next_memory.smm_control_index import SMMControlIndex
from next_memory.source_match_presentation import MiniLMQueryEncoder
from next_memory.vector_recall_probe import chunks_for_source


def read(p): return json.loads(p.read_text())
def sha(b): return hashlib.sha256(b).hexdigest()
def textsha(t): return sha(t.encode())
def write(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f: f.write(json.dumps(x, ensure_ascii=False, indent=2) + '\n')


def guard():
    p = read(HERE / 'protocol.json')
    for rel, h in p['frozen_files'].items(): assert sha((HERE / rel).read_bytes()) == h, rel
    return p


def batched_encode(encoder, texts):
    windows = []; bounds = []
    for text in texts:
        enc = encoder.tokenizer.encode(text, add_special_tokens=False)
        start = len(windows)
        if len(enc.ids) <= 224: windows.append(text or ' ')
        else:
            begin = 0
            while begin < len(enc.ids):
                end = min(begin + 224, len(enc.ids))
                a = 0 if begin == 0 else enc.offsets[begin][0]
                b = len(text) if end == len(enc.ids) else enc.offsets[end][0]
                windows.append(text[a:b])
                if end == len(enc.ids): break
                begin = end - 32
        bounds.append((start, len(windows)))
    raw = np.stack(list(encoder.model.embed(windows, batch_size=32)))
    values = []
    for a, b in bounds:
        v = raw[a:b].mean(axis=0); v /= np.linalg.norm(v)
        values.append(v.astype(np.float32))
    return np.stack(values)


def build(args):
    guard(); assert not (HERE / 'vectors/build.json').exists()
    start = time.perf_counter()
    local = HERE / 'local-results'; local.mkdir(exist_ok=True)
    cache = sqlite3.connect(local / 'chunk-cache.sqlite')
    cache.execute('create table if not exists v(hash text primary key, text text, vector blob, origin text)')
    imported = 0; files = []
    if args.seed_index_dir:
        for p in sorted(Path(args.seed_index_dir).glob('*.sqlite')):
            db = sqlite3.connect('file:' + str(p.resolve()) + '?mode=ro', uri=True)
            with cache:
                for raw, blob in db.execute('select chunk_json,vector from chunk_meta'):
                    text = json.loads(raw)['text']; v = np.frombuffer(blob, dtype='<f4')
                    assert v.shape == (384,) and np.isfinite(v).all() and abs(float(np.linalg.norm(v)) - 1) < 1e-5
                    cursor = cache.execute('insert or ignore into v values(?,?,?,?)', (textsha(text), text, blob, str(p)))
                    imported += cursor.rowcount
            db.close(); files.append(dict(file=p.name, sha256=sha(p.read_bytes())))
    t = time.perf_counter(); encoder = MiniLMQueryEncoder(Path(args.model_cache)); load_seconds = time.perf_counter() - t
    sources = {p.stem: read(p) for p in sorted((HERE / 'data/sources').glob('*.json'))}
    passages = []; lookup = {}; missing = []; examples = []
    for sid, r in sources.items():
        assert textsha(r['text']) == r['source_sha256']
        for c in chunks_for_source(r, r['structure']['parts'], encoder.tokenizer, tokens=256, overlap=48):
            h = textsha(c['text'])
            passages.append(dict(source_id=sid, id=c['id'], start=c['start'], end=c['end'], text_sha256=h))
            if h in lookup: continue
            lookup[h] = len(lookup)
            old = cache.execute('select text,vector from v where hash=?', (h,)).fetchone()
            if old:
                assert old[0] == c['text']
                if len(examples) < 8: examples.append(c['text'])
            else: missing.append((h, c['text']))
    examples += [t for h, t in missing[:max(0, 8 - len(examples))]]
    batch = batched_encode(encoder, examples)
    original = np.stack([encoder.encode(t) for t in examples])
    delta = float(np.max(np.abs(batch - original)))
    assert delta < 1e-6, delta
    print(json.dumps(dict(sources=len(sources), passages=len(passages), unique_chunks=len(lookup), cache_imports=imported,
                          missing=len(missing), batching_max_abs_difference=delta)), flush=True)
    receipts = []; encoded = 0
    for begin in range(0, len(missing), 32):
        todo = missing[begin:begin + 32]; t = time.perf_counter()
        values = batched_encode(encoder, [text for h, text in todo])
        with cache:
            for (h, text), v in zip(todo, values):
                cache.execute('insert into v values(?,?,?,?)', (h, text, v.tobytes(), 'new-same-model-batch'))
        receipts.append(dict(begin=begin, inputs=[h for h, text in todo], seconds=time.perf_counter() - t))
        encoded += len(todo)
        if begin % 320 == 0: print(json.dumps(dict(encoded=encoded, total=len(missing), elapsed=round(time.perf_counter() - start, 1))), flush=True)
    matrix = np.stack([np.frombuffer(cache.execute('select vector from v where hash=?', (h,)).fetchone()[0], dtype='<f4') for h in lookup])
    assert np.isfinite(matrix).all() and np.allclose(np.linalg.norm(matrix, axis=1), 1, atol=1e-5)
    folder = HERE / 'vectors'; folder.mkdir(exist_ok=True)
    np.save(folder / 'documents.npy', matrix)
    write(folder / 'passages.json', passages)
    write(folder / 'document-keys.json', list(lookup))
    query_start = time.perf_counter(); cases = read(HERE / 'data/cases.json'); qs = []; timings = []
    for c in cases:
        t = time.perf_counter(); qs.append(encoder.encode(c['question'].replace('\n', ' ')))
        timings.append(dict(case_id=c['id'], seconds=time.perf_counter() - t))
    np.save(folder / 'queries.npy', np.stack(qs).astype(np.float32))
    write(folder / 'query-keys.json', [c['id'] for c in cases])
    assets = {str(p.relative_to(Path(args.model_cache))): sha(p.read_bytes())
              for p in Path(args.model_cache).glob('models--Qdrant--all-MiniLM-L6-v2-onnx/snapshots/*/*') if p.is_file()}
    write(folder / 'build.json', dict(passed=True, total_seconds=time.perf_counter() - start, model_load_seconds=load_seconds,
          model='sentence-transformers/all-MiniLM-L6-v2', assets=assets,
          package_versions={k: importlib.metadata.version(k) for k in ['numpy', 'fastembed', 'onnxruntime', 'tokenizers']},
          old_index_files=files, imported_unique_vectors=imported, cache_reused_unique_chunks=len(lookup) - len(missing),
          new_unique_document_encodes=len(missing), new_query_encodes=len(cases), generative_calls=0,
          batching_max_abs_difference=delta, batching_checked_inputs=len(examples), receipts=receipts,
          query_encode_seconds=time.perf_counter() - query_start, query_timings=timings,
          files={p.name: sha(p.read_bytes()) for p in folder.iterdir() if p.is_file()}))
    cache.close()
    print(json.dumps(dict(built=True, sources=len(sources), unique_document_vectors=len(lookup), new_encodes=len(missing), seconds=time.perf_counter() - start)), flush=True)


def rank(args):
    guard(); build_info = read(HERE / 'vectors/build.json')
    for rel, h in build_info['files'].items(): assert sha((HERE / 'vectors' / rel).read_bytes()) == h
    passages = read(HERE / 'vectors/passages.json'); document_keys = read(HERE / 'vectors/document-keys.json')
    matrix = np.load(HERE / 'vectors/documents.npy', mmap_mode='r')
    queries = np.load(HERE / 'vectors/queries.npy', mmap_mode='r')
    cases = read(HERE / 'data/cases.json'); query_keys = read(HERE / 'vectors/query-keys.json')
    assert query_keys == [c['id'] for c in cases]
    doc = dict(zip(document_keys, matrix)); qvectors = {textsha(c['question'].replace('\n', ' ')): queries[i] for i, c in enumerate(cases)}
    # Same raw input can be encoded both as source and query; this encoder has
    # no query/document prefixes and the same normalization in both roles.
    def lookup(text):
        h = textsha(text)
        if h in doc: return doc[h]
        return qvectors[textsha(text.replace('\n', ' '))]
    class OfflineIndex(SMMControlIndex):
        def embed(self, texts): return np.asarray([lookup(t) for t in texts], dtype=np.float32)
    tokenizer = args.tokenizer
    if not tokenizer:
        tokenizer = str(next((HERE / 'local-results').glob('tokenizer.json')))
    ix = OfflineIndex(HERE / 'local-results/index', tokenizer)
    sources = {p.stem: read(p) for p in (HERE / 'data/sources').glob('*.json')}
    folder = HERE / ('replayed-rankings' if args.replay else 'rankings'); folder.mkdir(exist_ok=False)
    groups = {}
    try:
        for c in cases:
            ns = c['cohort'] + '_' + c['family'].replace('-', '_')
            if ns not in groups:
                t = time.perf_counter()
                db = ix.db(ns)
                if not db.execute('select count(*) from source_meta').fetchone()[0]:
                    for sid in c['source_ids']:
                        r = sources[sid]; ix.ingest(ns, {k: r[k] for k in ['id', 'text', 'received_at', 'source_sha256']}, r['structure'])
                actual = {sid for sid, in db.execute('select id from source_meta')}
                assert actual == set(c['source_ids'])
                groups[ns] = dict(index_seconds=time.perf_counter() - t)
            t = time.perf_counter(); ix.corpus(ns); setup = time.perf_counter() - t
            t = time.perf_counter(); out = ix.search(ns, c['question'], c['known_at']); elapsed = time.perf_counter() - t
            result = dict(case_id=c['id'], cohort=c['cohort'], family=c['family'],
                          source_ids=c['source_ids'], query=c['question'], clock=c['known_at'], native=out['native'],
                          first_corpus_load_seconds=setup, cached_query_search_seconds=elapsed)
            if args.replay:
                first = read(HERE / 'rankings' / (c['id'] + '.json'))
                assert result['native'] == first['native'], c['id']
            write(folder / (c['id'] + '.json'), result)
            print(json.dumps(dict(ranked=c['id'], replay=args.replay)), flush=True)
            # Bound cached source matrices to one family; close unused databases
            # once all its queries have completed, preserving index files.
        write(folder / 'complete.json', dict(cases=len(cases), groups=groups, generative_calls=0,
             new_embedding_calls=0, files={p.name: sha(p.read_bytes()) for p in folder.glob('*.json')}))
    finally: ix.close()


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=['build', 'rank'])
    p.add_argument('--model-cache'); p.add_argument('--seed-index-dir'); p.add_argument('--tokenizer'); p.add_argument('--replay', action='store_true')
    a = p.parse_args()
    if a.mode == 'build':
        assert a.model_cache
        build(a)
    else: rank(a)


if __name__ == '__main__': main()
