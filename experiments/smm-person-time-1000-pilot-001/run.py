"""No-scope 1000-source person-name and explicit-time BM25 diagnostic."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/smm-bm25-scale-1000-002"
QI = ROOT / "experiments/smm-query-input-001"
PERSON = ROOT / "experiments/smm-person-filter-pilot-001"
sys.path.insert(0, str(PERSON))
from run import load_source, speakers, score

MONTHS = {name.casefold(): i for i, name in enumerate(
    ("January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"), 1)}
DATE = re.compile(
    r"\b(" + "|".join(MONTHS) + r")\s+(?:(\d{1,2})(?:st|nd|rd|th)?[,]?[ ]+)?(20\d\d)\b",
    re.I,
)


def read(path: Path):
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interval_from_question(question: str):
    match = DATE.search(question)
    if not match:
        return None
    year = int(match.group(3))
    month = MONTHS[match.group(1).casefold()]
    if match.group(2):
        day = dt.date(year, month, int(match.group(2)))
        return day, day
    if "beginning" in question.casefold() or "early" in question.casefold():
        return dt.date(year, month, 1), dt.date(year, month, 10)
    return None


def has_name(text: str, people: list[str]) -> bool:
    return any(re.search(r"\b" + re.escape(name) + r"\b", text, re.I) is not None
               for name in people)


def boost_time(rows: list[dict], records: dict, interval) -> list[dict]:
    if interval is None:
        return rows
    start, end = interval
    out = []
    for row in rows:
        timestamp = records[row["source_id"]].get("received_at")
        date = dt.date.fromisoformat(timestamp[:10]) if timestamp else None
        value = row["score"] * (1.25 if date is not None and start <= date <= end else 1.0)
        out.append({"source_id": row["source_id"], "score": value})
    return sorted(out, key=lambda row: (-row["score"], row["source_id"]))


def metrics(rows: list[dict], refs: list[str]) -> dict:
    positions = {row["source_id"]: i for i, row in enumerate(rows, 1)}
    top5 = {row["source_id"] for row in rows[:5]}
    top10 = {row["source_id"] for row in rows[:10]}
    reference_set = set(refs)
    return {
        "candidate_count": len(rows),
        "reference_positions": {sid: positions.get(sid) for sid in refs},
        "top5_any": bool(top5 & reference_set),
        "top5_all": reference_set <= top5,
        "top10_any": bool(top10 & reference_set),
        "top10_all": reference_set <= top10,
        "top5": rows[:5],
        "top10": rows[:10],
    }


def main() -> None:
    verify = sys.argv[1:] == ["--verify"]
    assert verify or not (HERE / "results.json").exists(), "Write-once output; use --verify"
    protocol = read(HERE / "protocol.json")
    assert len(protocol["cases_fixed_before_ranking"]) == 12
    base = read(BASE / "protocol.json")
    plans = {r["id"]: r for r in base["cases"]}
    archived_top10 = {r["id"]: r for r in map(json.loads, (BASE / "top10.jsonl").read_text().splitlines())}
    queries = {}
    for line in (QI / "authored-inputs.tsv").read_text().splitlines():
        cid, query, _ = line.split("\t")
        queries[cid] = query
    cache = {}
    out = {"id": protocol["id"], "protocol_sha256": sha(HERE / "protocol.json"),
           "base_protocol_sha256": sha(BASE / "protocol.json"),
           "authored_queries_sha256": sha(QI / "authored-inputs.tsv"), "cases": []}
    for spec in protocol["cases_fixed_before_ranking"]:
        cid = spec["id"]
        plan = plans[cid]
        baseline = read(BASE / "results" / f"{cid}.json")
        # Both archived lists are used solely to reconstruct the unchanged 1000-ID pool.
        all_ids = plan["original_source_ids"] + plan["distractor_source_ids"]
        assert len(all_ids) == len(set(all_ids)) == 1000
        records = {sid: load_source(sid, base["source_bank"], cache) for sid in all_ids}
        texts = {sid: record["text"] for sid, record in records.items()}
        people = {name.casefold() for name in spec["people"]}
        speaker_ids = {sid for sid in all_ids if speakers(records[sid]) & people}
        mention_ids = {sid for sid in all_ids if has_name(texts[sid], spec["people"])}
        person_ids = [sid for sid in all_ids if sid in speaker_ids or sid in mention_ids]
        interval = interval_from_question(baseline["question"])
        raw_all, _, _ = score.rank(all_ids, texts, baseline["question"])
        assert [r["source_id"] for r in raw_all[:10]] == [r["source_id"] for r in archived_top10[cid]["expanded"]]
        authored_all, _, _ = score.rank(all_ids, texts, queries[cid])
        raw_person, _, _ = score.rank(person_ids, texts, baseline["question"])
        authored_person, _, _ = score.rank(person_ids, texts, queries[cid])
        arms = {
            "raw_all": raw_all,
            "authored_all": authored_all,
            "raw_person": raw_person,
            "authored_person": authored_person,
            "authored_all_time": boost_time(authored_all, records, interval),
            "authored_person_time": boost_time(authored_person, records, interval),
        }
        refs = baseline["official_reference_sources"]  # evaluation only, after ranking
        out["cases"].append({
            "id": cid, "question": baseline["question"], "people": spec["people"],
            "authored_query": queries[cid],
            "explicit_interval": [d.isoformat() for d in interval] if interval else None,
            "source_counts": {"all": len(all_ids), "person": len(person_ids),
                              "speaker": len(speaker_ids), "mentioned": len(mention_ids),
                              "mention_only": len(mention_ids - speaker_ids)},
            "official_refs": refs,
            "reference_retained_by_person": sorted(set(refs) & set(person_ids)),
            "reference_retained_by_speaker": sorted(set(refs) & speaker_ids),
            "reference_retained_by_mention_only": sorted(set(refs) & (mention_ids - speaker_ids)),
            "methods": {name: metrics(rows, refs) for name, rows in arms.items()},
        })
    if verify:
        assert read(HERE / "results.json") == out
        print("verified 12/12 cases; all source SHA and archived raw Top10 bindings passed")
    else:
        with (HERE / "results.json").open("x") as stream:
            json.dump(out, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    for method in protocol["methods"]:
        print(method, "Top5 any", sum(c["methods"][method]["top5_any"] for c in out["cases"]),
              "Top5 all", sum(c["methods"][method]["top5_all"] for c in out["cases"]),
              "Top10 all", sum(c["methods"][method]["top10_all"] for c in out["cases"]))


if __name__ == "__main__":
    main()
