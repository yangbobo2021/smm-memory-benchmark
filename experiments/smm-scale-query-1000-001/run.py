"""Replay archived BM25 with frozen alternate query text; source texts unchanged."""
from __future__ import annotations
import collections
import hashlib
import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/smm-bm25-scale-1000-002"
import sys
sys.path.insert(0, str(BASE))
import score


def load(path: Path): return json.loads(path.read_text())
def sha(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    protocol = load(HERE / "protocol.json")
    assert protocol["id"] == "SMM-SCALE-QUERY-1000-001"
    assert sha(BASE / "protocol.json") == protocol["baseline_protocol_sha256"]
    assert sha(ROOT / "experiments/smm-query-input-001/runtime.json") == protocol["authored_runtime_sha256"]
    for name, digest in protocol["implementation_hashes"].items(): assert sha(HERE / name) == digest
    base = load(BASE / "protocol.json")
    plans = {x["id"]: x for x in base["cases"]}
    files = {}
    texts = {}
    for sid, meta in base["source_bank"].items():
        name = meta["file"]
        if name not in files:
            path = ROOT / name
            if name.endswith(".jsonl"):
                files[name] = {x["source_id"]: x for x in (json.loads(line) for line in path.read_text().splitlines())}
            else:
                d = load(path)
                files[name] = {x["id"]: x for x in d["records"]} if "records" in d else {d["id"]: d}
        body = files[name][sid]["text"]
        assert hashlib.sha256(body.encode()).hexdigest() == meta["source_sha256"]
        texts[sid] = body
    results = []
    for case in protocol["cases"]:
        cid = case["id"]
        path = HERE / "results" / f"{cid}.json"
        if path.exists():
            result = load(path)
            assert result["protocol_sha256"] == sha(HERE / "protocol.json")
            results.append(result)
            continue
        old = load(BASE / "results" / f"{cid}.json")
        plan = plans[cid]
        ids = plan["original_source_ids"] + plan["distractor_source_ids"]
        assert len(ids) == 1000
        refs = old["official_reference_sources"]
        result = {"id": cid, "cohort": plan["cohort"], "protocol_sha256": sha(HERE / "protocol.json"),
                  "reference_sources": refs, "raw": {"top5": old["expanded"]["top5"], "top10": old["expanded"]["top10"],
                                                  "reference_positions": old["expanded"]["reference_positions"]}}
        for variant in ("authored", "stopword"):
            q = case[variant + "_query"]
            ranking, build, query = score.rank(ids, texts, q)
            measures = score.measures(ranking, refs)
            result[variant] = {"query": q, "top5": measures["top5"], "top10": measures["top10"],
                               "reference_positions": measures["reference_positions"], "top10_ids": [x["source_id"] for x in ranking[:10]],
                               "seconds": {"build": build, "query": query}}
        path.parent.mkdir(exist_ok=True)
        with path.open("x") as file: json.dump(result, file, ensure_ascii=False, indent=2); file.write("\n")
        results.append(result)
        print(json.dumps({"done": len(results), "id": cid}), flush=True)
    summary = {"id": protocol["id"], "protocol_sha256": sha(HERE / "protocol.json"), "by_cohort": {}}
    for cohort in ("P25", "L32", "C200", "all257"):
        subset = results if cohort == "all257" else [r for r in results if r["cohort"] == cohort]
        d = {"questions": len(subset)}
        for variant in ("raw", "authored", "stopword"):
            d[variant] = {f"top{n}": {"all": sum(r[variant][f"top{n}"]["all"] for r in subset),
                                     "any": sum(r[variant][f"top{n}"]["any"] for r in subset),
                                     "reference_hits": sum(r[variant][f"top{n}"]["reference_count"] for r in subset)} for n in (5,10)}
        for variant in ("authored", "stopword"):
            d[variant]["paired_top5"] = {"gains": [r["id"] for r in subset if not r["raw"]["top5"]["all"] and r[variant]["top5"]["all"]],
                                            "losses": [r["id"] for r in subset if r["raw"]["top5"]["all"] and not r[variant]["top5"]["all"]]}
            d[variant]["query_seconds_median"] = statistics.median(r[variant]["seconds"]["query"] for r in subset)
        summary["by_cohort"][cohort] = d
    target = HERE / "summary.json"
    assert not target.exists()
    target.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"complete": len(results), "summary": str(target)}))


if __name__ == "__main__": main()
