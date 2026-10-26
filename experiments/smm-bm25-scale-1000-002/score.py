"""Replay the frozen original BM25 on original and 1000-source candidate pools."""
from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = ROOT / "experiments/smm-baseline-001"
GENERAL = ROOT / "experiments/smm-retrieval-generalization-001"
sys.path.insert(0, str(GENERAL / "implementation"))
from next_memory.conversation_topics import lexical_expression


def read(path: Path):
    return json.loads(path.read_text())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_new(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")


def rank(ids: list[str], texts: dict[str, str], question: str) -> tuple[list[dict], float, float]:
    started = time.perf_counter()
    db = sqlite3.connect(":memory:")
    try:
        db.execute("create virtual table f using fts5(text, tokenize='unicode61')")
        db.executemany("insert into f(rowid,text) values(?,?)", [(i + 1, texts[sid]) for i, sid in enumerate(ids)])
        built = time.perf_counter() - started
        expr = lexical_expression(question)
        queried = time.perf_counter()
        rows = [] if not expr else [(ids[rowid - 1], -float(score)) for rowid, score in db.execute(
            "select rowid,bm25(f) from f where f match ?", (expr,))]
        rows.sort(key=lambda pair: (-pair[1], pair[0]))
        query_seconds = time.perf_counter() - queried
        return [{"source_id": sid, "score": score} for sid, score in rows], built, query_seconds
    finally:
        db.close()


def measures(rows: list[dict], refs: list[str]):
    positions = {row["source_id"]: i + 1 for i, row in enumerate(rows)}
    out = {"reference_positions": {sid: positions.get(sid) for sid in refs}, "top10": rows[:10], "match_count": len(rows)}
    for n in [1, 3, 5, 10]:
        found = {row["source_id"] for row in rows[:n]}
        out[f"top{n}"] = {"all": all(sid in found for sid in refs),
                           "any": any(sid in found for sid in refs),
                           "reference_count": sum(sid in found for sid in refs)}
    return out


def main() -> None:
    protocol = read(HERE / "protocol.json")
    assert protocol["id"] == "SMM-BM25-SCALE-1000-002"
    for name, digest in protocol["input_hashes"].items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    for name, digest in protocol["implementation_hashes"].items():
        assert sha((HERE / name).read_bytes()) == digest, name
    assert len(protocol["cases"]) == 257
    old = {c["id"]: c for c in read(PARENT / "data/cases.json")}
    new = {c["id"]: c for c in read(GENERAL / "data/cases.json")}
    cache: dict[str, dict] = {}
    texts: dict[str, str] = {}
    for sid, record in protocol["source_bank"].items():
        path = record["file"]
        if path not in cache:
            if path.endswith(".jsonl"):
                cache[path] = {r["source_id"]: r for r in (json.loads(line) for line in (ROOT / path).read_text().splitlines())}
            else:
                data = read(ROOT / path)
                cache[path] = {r["id"]: r for r in data["records"]} if "records" in data else {data["id"]: data}
        source = cache[path][sid]
        assert sha(source["text"].encode()) == record["source_sha256"]
        texts[sid] = source["text"]
    assert len(texts) == 3675
    records = []
    for plan in protocol["cases"]:
        cid = plan["id"]
        result_path = HERE / "results" / (cid + ".json")
        if result_path.exists():
            result = read(result_path)
            assert result["id"] == cid and result["protocol_sha256"] == sha((HERE / "protocol.json").read_bytes())
            records.append(result)
            continue
        c = old[cid] if cid in old else new[cid]
        original = plan["original_source_ids"]
        expanded = original + plan["distractor_source_ids"]
        assert len(expanded) == len(set(expanded)) == 1000
        refs = c["official_reference_sources"]
        assert refs and set(refs) <= set(original)
        baseline, baseline_build, baseline_query = rank(original, texts, c["question"])
        archived_path = (PARENT / "data/retrieval" / (cid + ".json")) if cid in old else (GENERAL / "rankings" / (cid + ".json"))
        archived = read(archived_path)
        prior = archived["native"]["native"]["bm25"] if cid in old else archived["native"]["bm25"]
        assert [r["source_id"] for r in baseline[:10]] == [r["source_id"] for r in prior[:10]], cid
        increased, expanded_build, expanded_query = rank(expanded, texts, c["question"])
        result = {
            "id": cid, "cohort": plan["cohort"], "question": c["question"],
            "original_count": len(original), "expanded_count": 1000,
            "official_reference_sources": refs,
            "protocol_sha256": sha((HERE / "protocol.json").read_bytes()),
            "original": measures(baseline, refs), "expanded": measures(increased, refs),
            "seconds": {"original_build": baseline_build, "original_query": baseline_query,
                        "expanded_build": expanded_build, "expanded_query": expanded_query},
        }
        write_new(result_path, result)
        records.append(result)
        print(json.dumps({"ranked": cid, "done": len(records), "total": 257}), flush=True)
    if not (HERE / "summary.json").exists():
        summary = {"id": protocol["id"], "protocol_sha256": sha((HERE / "protocol.json").read_bytes()),
                   "case_count": len(records), "by_cohort": {}, "latency_seconds": {}}
        for cohort in ["P25", "L32", "C200", "all257"]:
            arr = records if cohort == "all257" else [x for x in records if x["cohort"] == cohort]
            d = {"questions": len(arr), "original_source_count_range": [min(x["original_count"] for x in arr), max(x["original_count"] for x in arr)],
                 "reference_count_distribution": dict(sorted(collections.Counter(len(x["official_reference_sources"]) for x in arr).items()))}
            for mode in ["original", "expanded"]:
                d[mode] = {}
                for n in [1, 3, 5, 10]:
                    d[mode][f"top{n}"] = {
                        "all": sum(x[mode][f"top{n}"]["all"] for x in arr),
                        "any": sum(x[mode][f"top{n}"]["any"] for x in arr),
                        "reference_hits": sum(x[mode][f"top{n}"]["reference_count"] for x in arr),
                        "reference_total": sum(len(x["official_reference_sources"]) for x in arr),
                    }
            for n in [5, 10]:
                d[f"top{n}_paired"] = {
                    "both": sum(x["original"][f"top{n}"]["all"] and x["expanded"][f"top{n}"]["all"] for x in arr),
                    "original_only": sum(x["original"][f"top{n}"]["all"] and not x["expanded"][f"top{n}"]["all"] for x in arr),
                    "expanded_only": sum(not x["original"][f"top{n}"]["all"] and x["expanded"][f"top{n}"]["all"] for x in arr),
                    "neither": sum(not x["original"][f"top{n}"]["all"] and not x["expanded"][f"top{n}"]["all"] for x in arr),
                }
            summary["by_cohort"][cohort] = d
        for key in ["original_build", "original_query", "expanded_build", "expanded_query"]:
            values = [x["seconds"][key] for x in records]
            summary["latency_seconds"][key] = {"median": statistics.median(values), "p95": sorted(values)[int(.95 * (len(values) - 1))]}
        write_new(HERE / "summary.json", summary)
    print(json.dumps({"complete": len(records), "summary": str(HERE / 'summary.json')}))


if __name__ == "__main__":
    main()
