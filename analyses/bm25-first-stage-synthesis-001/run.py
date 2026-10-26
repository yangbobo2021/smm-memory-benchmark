"""Offline P25/L32 replay on the frozen mixed 1000-conversation pools."""
from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/smm-bm25-scale-1000-002"
QI = ROOT / "experiments/smm-query-input-001"
sys.path.insert(0, str(ROOT / "experiments/smm-person-filter-pilot-001"))
import run as person_pilot

spec = importlib.util.spec_from_file_location(
    "person_time_pilot", ROOT / "experiments/smm-person-time-1000-pilot-001/run.py"
)
person_time_pilot = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(person_time_pilot)


def read(path: Path):
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(rows: list[dict], refs: list[str]) -> dict:
    positions = {row["source_id"]: i for i, row in enumerate(rows, 1)}
    targets = set(refs)
    out = {"reference_positions": {sid: positions.get(sid) for sid in refs}}
    for n in (5, 10):
        found = {row["source_id"] for row in rows[:n]}
        out[f"top{n}"] = {
            "any": bool(targets & found),
            "all": targets <= found,
            "reference_hits": len(targets & found),
            "top_source_ids": [row["source_id"] for row in rows[:n]],
        }
    return out


def main() -> None:
    verify = sys.argv[1:] == ["--verify"]
    assert verify or not sys.argv[1:], "Only --verify is supported"
    protocol = read(HERE / "protocol.json")
    for rel, digest in protocol["input_sha256"].items():
        assert sha(ROOT / rel) == digest, rel
    base = read(BASE / "protocol.json")
    archived = {r["id"]: r for r in map(json.loads, (BASE / "top10.jsonl").read_text().splitlines())}
    queries = {}
    for line in (QI / "authored-inputs.tsv").read_text().splitlines():
        cid, query, _ = line.split("\t")
        queries[cid] = query
    cache = {}
    cases = []
    for plan in base["cases"]:
        if plan["cohort"] not in protocol["question_groups"]:
            continue
        cid = plan["id"]
        baseline = read(BASE / "results" / f"{cid}.json")
        ids = plan["original_source_ids"] + plan["distractor_source_ids"]
        assert len(ids) == len(set(ids)) == 1000
        texts = {sid: person_pilot.load_source(sid, base["source_bank"], cache)["text"] for sid in ids}
        raw, _, _ = person_pilot.score.rank(ids, texts, baseline["question"])
        assert [r["source_id"] for r in raw[:10]] == [r["source_id"] for r in archived[cid]["expanded"]], cid
        authored, _, _ = person_pilot.score.rank(ids, texts, queries[cid])
        interval = person_time_pilot.interval_from_question(baseline["question"])
        refs = baseline["official_reference_sources"]
        cases.append({
            "id": cid,
            "cohort": plan["cohort"],
            "question": baseline["question"],
            "previously_authored_keyword_query": queries[cid],
            "official_reference_sources": refs,
            "explicit_month_year_interval": [d.isoformat() for d in interval] if interval else None,
            "methods": {
                "raw_question_bm25": metrics(raw, refs),
                "previously_authored_keyword_bm25": metrics(authored, refs),
            },
        })
    assert collections.Counter(c["cohort"] for c in cases) == {"P25": 25, "L32": 32}
    summary = {}
    for cohort in protocol["question_groups"]:
        group = [c for c in cases if c["cohort"] == cohort]
        summary[cohort] = {}
        for method in protocol["methods"]:
            summary[cohort][method] = {}
            for n in (5, 10):
                summary[cohort][method][f"top{n}"] = {
                    "any": sum(c["methods"][method][f"top{n}"]["any"] for c in group),
                    "all": sum(c["methods"][method][f"top{n}"]["all"] for c in group),
                    "reference_hits": sum(c["methods"][method][f"top{n}"]["reference_hits"] for c in group),
                    "reference_total": sum(len(c["official_reference_sources"]) for c in group),
                }
    result = {
        "id": protocol["id"],
        "protocol_sha256": sha(HERE / "protocol.json"),
        "explicit_month_year_applicable_case_ids": [c["id"] for c in cases if c["explicit_month_year_interval"]],
        "summary": summary,
        "cases": cases,
    }
    output = HERE / "results.json"
    if verify:
        assert read(output) == result
        print("verified 57/57 original source hashes, raw archived Top10, and both query rankings")
    else:
        with output.open("x") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
