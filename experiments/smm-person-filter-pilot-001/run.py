"""Eight fixed-case speaker gating pilot over the archived 1000-source corpus."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/smm-bm25-scale-1000-002"
sys.path.insert(0, str(BASE))
import score


def read(path: Path):
    return json.loads(path.read_text())


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load_source(sid: str, bank: dict, cache: dict) -> dict:
    meta = bank[sid]
    path = meta["file"]
    if path not in cache:
        file = ROOT / path
        if file.suffix == ".jsonl":
            cache[path] = {r["source_id"]: r for r in map(json.loads, file.read_text().splitlines())}
        else:
            payload = read(file)
            cache[path] = {r["id"]: r for r in payload["records"]} if "records" in payload else {payload["id"]: payload}
    record = cache[path][sid]
    assert sha(record["text"]) == meta["source_sha256"], sid
    return record


def speakers(record: dict) -> set[str]:
    parts = record.get("structure", {}).get("parts", [])
    return {part["role"].casefold().strip() for part in parts}


def has_mention(text: str, people: list[str]) -> bool:
    return any(re.search(r"\b" + re.escape(name) + r"\b", text, re.I) is not None for name in people)


def measure(rows: list[dict], refs: list[str], original: set[str]) -> dict:
    top5 = rows[:5]
    top10 = rows[:10]
    pos = {r["source_id"]: i for i, r in enumerate(rows, 1)}
    found5 = {r["source_id"] for r in top5}
    found10 = {r["source_id"] for r in top10}
    return {
        "candidate_count": len(rows),
        "reference_positions": {r: pos.get(r) for r in refs},
        "top5_all_official": set(refs) <= found5,
        "top5_any_official": bool(set(refs) & found5),
        "top10_all_official": set(refs) <= found10,
        "top5_original_history_count": sum(r["source_id"] in original for r in top5),
        "top5": [{"source_id": r["source_id"], "score": r["score"],
                  "is_original_history": r["source_id"] in original,
                  "is_official_reference": r["source_id"] in refs} for r in top5],
    }


def main() -> None:
    verify = sys.argv[1:] == ["--verify"]
    assert verify or not (HERE / "results.json").exists(), "Results are write-once; use --verify"
    protocol = read(HERE / "protocol.json")
    base = read(BASE / "protocol.json")
    plans = {c["id"]: c for c in base["cases"]}
    archived_top10 = {row["id"]: row for row in map(json.loads, (BASE / "top10.jsonl").read_text().splitlines())}
    assert len(protocol["cases_fixed_before_ranking"]) == 8
    cache: dict[str, dict] = {}
    output = {"id": protocol["id"],
              "protocol_sha256": hashlib.sha256((HERE / "protocol.json").read_bytes()).hexdigest(),
              "base_protocol_sha256": hashlib.sha256((BASE / "protocol.json").read_bytes()).hexdigest(),
              "cases": []}
    for spec in protocol["cases_fixed_before_ranking"]:
        cid = spec["id"]
        plan = plans[cid]
        baseline = read(BASE / "results" / f"{cid}.json")
        assert plan["cohort"] == "C200"
        ids = plan["original_source_ids"] + plan["distractor_source_ids"]
        assert len(ids) == len(set(ids)) == 1000
        records = {sid: load_source(sid, base["source_bank"], cache) for sid in ids}
        texts = {sid: rec["text"] for sid, rec in records.items()}
        original = set(plan["original_source_ids"])
        refs = baseline["official_reference_sources"]
        people = [name.casefold() for name in spec["people"]]
        raw, _, _ = score.rank(ids, texts, baseline["question"])
        assert [r["source_id"] for r in raw[:10]] == [r["source_id"] for r in archived_top10[cid]["expanded"]], cid
        speaker_ids = {sid for sid in ids if speakers(records[sid]) & set(people)}
        mention_ids = {sid for sid in ids if has_mention(texts[sid], spec["people"])}
        speaker_gate = [r for r in raw if r["source_id"] in speaker_ids]
        mention_gate = [r for r in raw if r["source_id"] in mention_ids]
        reindexed, _, _ = score.rank([sid for sid in ids if sid in speaker_ids], texts, baseline["question"])
        case = {"id": cid, "question": baseline["question"], "query_people": spec["people"],
                "reason": spec["reason"], "source_count": len(ids),
                "speaker_subset_count": len(speaker_ids), "name_mention_subset_count": len(mention_ids),
                "speaker_subset_original_history_count": len(speaker_ids & original),
                "speaker_subset_retained_official_refs": sorted(speaker_ids & set(refs)),
                "mention_subset_retained_official_refs": sorted(mention_ids & set(refs)),
                "official_refs": refs,
                "methods": {
                    "raw_all_1000": measure(raw, refs, original),
                    "filter_existing_1000_rank_by_speaker": measure(speaker_gate, refs, original),
                    "reindex_speaker_subset": measure(reindexed, refs, original),
                    "filter_existing_1000_rank_by_name_mention": measure(mention_gate, refs, original),
                }}
        output["cases"].append(case)
    if verify:
        assert read(HERE / "results.json") == output, "Pilot numeric replay changed"
        print("verified 8/8 cases; all original source hashes and archived raw Top10 matched")
    else:
        with (HERE / "results.json").open("x") as file:
            json.dump(output, file, ensure_ascii=False, indent=2)
            file.write("\n")
    for method in protocol["methods"]:
        all5 = sum(c["methods"][method]["top5_all_official"] for c in output["cases"])
        any5 = sum(c["methods"][method]["top5_any_official"] for c in output["cases"])
        print(method, "top5_all", all5, "top5_any", any5)


if __name__ == "__main__":
    main()
