"""Freeze question-blind distractor selection for the 1000-source BM25 test."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = ROOT / "experiments/smm-baseline-001"
GENERAL = ROOT / "experiments/smm-retrieval-generalization-001"
SEED = "smm-bm25-1000-original-queries-20261026-v1"


def read(path: Path):
    return json.loads(path.read_text())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def order(case_id: str, source_id: str) -> str:
    return sha((SEED + "\0" + case_id + "\0" + source_id).encode())


def main() -> None:
    assert not (HERE / "protocol.json").exists()
    old_cases = read(PARENT / "data/cases.json")
    new_cases = read(GENERAL / "data/cases.json")
    sources: dict[str, dict] = {}
    source_files: dict[str, str] = {}
    for case in old_cases:
        relative = "experiments/smm-baseline-001/" + case["corpus_file"]
        for record in read(ROOT / relative)["records"]:
            sid = record["id"]
            if sid in sources:
                assert sources[sid]["text"] == record["text"]
            else:
                sources[sid] = record
                source_files[sid] = relative
    for path in sorted((GENERAL / "data/sources").glob("*.json")):
        record = read(path)
        sid = record["id"]
        assert sid not in sources
        sources[sid] = record
        source_files[sid] = str(path.relative_to(ROOT))
    cc_file = HERE / "data/conversationchronicles-selected728.jsonl"
    cc_relative = str(cc_file.relative_to(ROOT))
    cc_sources = set()
    for line in cc_file.read_text().splitlines():
        row = json.loads(line)
        sid = row["source_id"]
        assert sid not in sources and sid not in cc_sources
        assert len(row["utterances"]) == len(row["speakers"]) >= 15
        assert len(row["text"]) >= 1800
        assert row["text"] == "\n\n".join(f"{speaker.upper()}:\n{turn}" for speaker, turn in zip(row["speakers"], row["utterances"]))
        sources[sid] = {"id": sid, "text": row["text"], "source_sha256": row["source_sha256"],
                        "provenance": {"dataset": "ConversationChronicles", "episode_id": row["episode_id"],
                                       "session_index": row["session_index"]}}
        source_files[sid] = cc_relative
        cc_sources.add(sid)
    assert len(cc_sources) == 728 and len(sources) == 3675
    digest_by_id = {sid: sha(record["text"].encode()) for sid, record in sources.items()}
    assert all(digest_by_id[sid] == record["source_sha256"] for sid, record in sources.items())
    locomo = {sid for sid, record in sources.items() if record.get("provenance", {}).get("dataset") == "LoCoMo"}
    assert len(locomo) == 272
    cases = []
    for case in old_cases + new_cases:
        cid = case["id"]
        if cid.startswith("P"):
            original = [record["id"] for record in read(PARENT / case["corpus_file"])["records"]]
            cohort = "P25"
        else:
            original = case["source_ids"]
            cohort = "L32" if cid.startswith("L") else "C200"
        assert len(original) == len(set(original))
        assert len(original) < 1000
        used = set(original)
        used_hashes = {digest_by_id[sid] for sid in original}
        # C cases use all 272 published LoCoMo sessions, then the same 728
        # length-matched native Conversation Chronicles sessions. P/L use only
        # other archived LongMemEval sessions, preserving their old v1 order.
        groups = [locomo, cc_sources] if cohort == "C200" else [set(sources) - locomo - cc_sources]
        added = []
        for group in groups:
            for sid in sorted(group - used, key=lambda sid: (order(cid, sid), sid)):
                h = digest_by_id[sid]
                if h in used_hashes:
                    continue
                added.append(sid)
                used.add(sid)
                used_hashes.add(h)
                if len(original) + len(added) == 1000:
                    break
            if len(original) + len(added) == 1000:
                break
        assert len(original) + len(added) == 1000, cid
        assert len(used_hashes) == 1000, cid
        cases.append({"id": cid, "cohort": cohort, "original_source_ids": original, "distractor_source_ids": added})
    assert len(cases) == 257
    c_sets = {frozenset(x["original_source_ids"] + x["distractor_source_ids"]) for x in cases if x["cohort"] == "C200"}
    assert c_sets == {frozenset(locomo | cc_sources)}
    bank = {sid: {"source_sha256": digest_by_id[sid], "file": source_files[sid]} for sid in sorted(sources)}
    inputs = [
        "experiments/smm-baseline-001/data/cases.json",
        "experiments/smm-retrieval-generalization-001/data/cases.json",
        "experiments/smm-retrieval-generalization-001/implementation/next_memory/conversation_topics.py",
    ]
    inputs += sorted({row["file"] for row in bank.values()})
    protocol = {
        "id": "SMM-BM25-SCALE-1000-002",
        "seed": SEED,
        "question_count": 257,
        "corpus_size_per_case": 1000,
        "source_unit": "one original full dated session / conversation",
        "method": "exact archived SQLite FTS5 unicode61 whole-source BM25, original question lexical_expression OR terms; no query rewrite, vector, reranker or model call",
        "selection": "Preserve every original source. C200 uses one common 1000-source pool: all 272 published LoCoMo sessions plus 728 original complete Conversation Chronicles test sessions selected in dataset order, with >=15 turns and >=1800 serialized characters, without inspecting questions or labels. P/L add unique-text sessions from the same LongMemEval source bank in question-blind SHA256 order.",
        "conversation_chronicles": {"repository": "jihyoung/ConversationChronicles", "revision": "9639b3552594a612ceafa76238a34f0f6eeaa207", "split": "test", "selection": "first 728 test sessions meeting fixed length thresholds, encountered in raw test.jsonl episode/session order", "license": "CC BY 4.0", "selected_sessions": 728, "episodes_scanned": 2883},
        "date_scope": "lexical candidate-pool stress test: distractors are indexed regardless of their native timestamps; Conversation Chronicles has only relative session intervals. Original histories retain their previously valid cutoff. Not a causal same-user memory benchmark.",
        "primary_label": "all archived official reference source IDs; also report at least one reference and individual-reference coverage. Reference completeness is not answer sufficiency.",
        "input_hashes": {name: sha((ROOT / name).read_bytes()) for name in inputs},
        "implementation_hashes": {name: sha((HERE / name).read_bytes()) for name in ["prepare.py", "score.py"]},
        "source_bank": bank,
        "cases": cases,
    }
    (HERE / "protocol.json").write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"frozen": True, "cases": len(cases), "bank": len(bank), "cohorts": {c: sum(x["cohort"] == c for x in cases) for c in ["P25", "L32", "C200"]}}))


if __name__ == "__main__":
    main()
