"""A small, replayable ID-scope/person-role/time BM25 diagnostic."""
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
GENERAL = ROOT / "experiments/smm-retrieval-generalization-001"
PERSON = ROOT / "experiments/smm-person-filter-pilot-001"
sys.path.insert(0, str(PERSON))
from run import load_source, speakers, measure, score

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


def explicit_interval(question: str):
    match = DATE.search(question)
    if not match:
        return None
    month = MONTHS[match.group(1).casefold()]
    year = int(match.group(3))
    if match.group(2):
        day = int(match.group(2))
        start = dt.date(year, month, day)
        return start, start
    if "beginning" in question.casefold() or "early" in question.casefold():
        return dt.date(year, month, 1), dt.date(year, month, 10)
    return None  # A whole month is too imprecise for this narrow diagnostic.


def has_person(text: str, people: list[str]) -> bool:
    return any(re.search(r"\b" + re.escape(person) + r"\b", text, re.I) is not None
               for person in people)


def date_boost(rows: list[dict], records: dict, interval) -> list[dict]:
    if interval is None:
        return rows
    start, end = interval
    adjusted = []
    for row in rows:
        sid = row["source_id"]
        day = dt.date.fromisoformat(records[sid]["received_at"][:10])
        score_value = row["score"] * (1.25 if start <= day <= end else 1.0)
        adjusted.append({"source_id": sid, "score": score_value})
    return sorted(adjusted, key=lambda row: (-row["score"], row["source_id"]))


def main() -> None:
    verify = sys.argv[1:] == ["--verify"]
    assert verify or not (HERE / "results.json").exists()
    protocol = read(HERE / "protocol.json")
    assert len(protocol["cases_fixed_before_ranking"]) == 12
    base = read(BASE / "protocol.json")
    plans = {case["id"]: case for case in base["cases"]}
    cases = {case["id"]: case for case in read(GENERAL / "data/cases.json")}
    top10 = {row["id"]: row for row in map(json.loads, (BASE / "top10.jsonl").read_text().splitlines())}
    queries = {}
    for line in (QI / "authored-inputs.tsv").read_text().splitlines():
        cid, bm, _ = line.split("\t")
        queries[cid] = bm
    cache = {}
    out = {"id": protocol["id"], "protocol_sha256": sha(HERE / "protocol.json"),
           "base_protocol_sha256": sha(BASE / "protocol.json"),
           "authored_queries_sha256": sha(QI / "authored-inputs.tsv"), "cases": []}
    for spec in protocol["cases_fixed_before_ranking"]:
        cid = spec["id"]
        case = cases[cid]
        plan = plans[cid]
        baseline = read(BASE / "results" / f"{cid}.json")
        all_ids = plan["original_source_ids"] + plan["distractor_source_ids"]
        assert len(set(all_ids)) == len(all_ids) == 1000
        records = {sid: load_source(sid, base["source_bank"], cache) for sid in all_ids}
        texts = {sid: records[sid]["text"] for sid in all_ids}
        known = dt.datetime.fromisoformat(case["known_at"])
        scope_ids = [sid for sid in all_ids if
                     records[sid].get("provenance", {}).get("sample_id") == case["family"] and
                     dt.datetime.fromisoformat(records[sid]["received_at"]) <= known]
        # Check against the separately archived original pool only after constructing scope from provenance/time.
        assert set(scope_ids) == set(plan["original_source_ids"]), cid
        people = {p.casefold() for p in spec["people"]}
        speaker_ids = {sid for sid in scope_ids if speakers(records[sid]) & people}
        mentioned_ids = {sid for sid in scope_ids if has_person(texts[sid], spec["people"])}
        person_ids = [sid for sid in scope_ids if sid in speaker_ids or sid in mentioned_ids]
        assert set(baseline["official_reference_sources"]) <= set(scope_ids)
        raw_all, _, _ = score.rank(all_ids, texts, case["question"])
        assert [r["source_id"] for r in raw_all[:10]] == [r["source_id"] for r in top10[cid]["expanded"]]
        raw_scope, _, _ = score.rank(scope_ids, texts, case["question"])
        authored_scope, _, _ = score.rank(scope_ids, texts, queries[cid])
        raw_person, _, _ = score.rank(person_ids, texts, case["question"])
        authored_person, _, _ = score.rank(person_ids, texts, queries[cid])
        interval = explicit_interval(case["question"])
        boosted_person = date_boost(authored_person, records, interval)
        archived = read(QI / "rankings" / f"{cid}.json")["rankings"]
        assert [r["source_id"] for r in raw_scope[:5]] == [r["source_id"] for r in archived["bm25_raw"][:5]]
        assert [r["source_id"] for r in authored_scope[:5]] == [r["source_id"] for r in archived["bm25_rewritten"][:5]]
        methods = {
            "raw_all_1000": raw_all,
            "raw_scope": raw_scope,
            "authored_scope": authored_scope,
            "raw_scope_person": raw_person,
            "authored_scope_person": authored_person,
            "authored_scope_person_time": boosted_person,
        }
        out["cases"].append({
            "id": cid, "question": case["question"], "scope_id": case["family"],
            "known_at": case["known_at"], "people": spec["people"], "authored_query": queries[cid],
            "explicit_time_interval": [x.isoformat() for x in interval] if interval else None,
            "counts": {"all": len(all_ids), "scope": len(scope_ids), "person": len(person_ids),
                       "speaker": len(speaker_ids), "mentioned": len(mentioned_ids),
                       "mention_only": len(mentioned_ids - speaker_ids)},
            "reference_retention": {
                "scope": sorted(set(baseline["official_reference_sources"]) & set(scope_ids)),
                "person": sorted(set(baseline["official_reference_sources"]) & set(person_ids)),
                "speaker_only": sorted(set(baseline["official_reference_sources"]) & speaker_ids),
                "mention_only": sorted(set(baseline["official_reference_sources"]) & (mentioned_ids - speaker_ids)),
            },
            "official_refs": baseline["official_reference_sources"],
            "methods": {name: measure(rows, baseline["official_reference_sources"], set(scope_ids))
                        for name, rows in methods.items()},
        })
    if verify:
        assert read(HERE / "results.json") == out
        print("verified 12/12 cases, all source hashes, scope bindings, archived raw/rewritten rankings")
    else:
        with (HERE / "results.json").open("x") as stream:
            json.dump(out, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    for method in protocol["methods"]:
        print(method,
              "top5_any", sum(c["methods"][method]["top5_any_official"] for c in out["cases"]),
              "top5_all", sum(c["methods"][method]["top5_all_official"] for c in out["cases"]),
              "top10_all", sum(c["methods"][method]["top10_all_official"] for c in out["cases"]))


if __name__ == "__main__":
    main()
