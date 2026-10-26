"""Replay six fixed combinations on eight diagnostic questions, without model calls."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/smm-bm25-scale-1000-002"
PERSON = ROOT / "experiments/smm-person-filter-pilot-001"
QI = ROOT / "experiments/smm-query-input-001"
sys.path.insert(0, str(PERSON))
from run import load_source, speakers, measure, score


def read(path: Path):
    return json.loads(path.read_text())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    verify = sys.argv[1:] == ["--verify"]
    assert verify or not (HERE / "results.json").exists()
    protocol = read(HERE / "protocol.json")
    spec = {r["id"]: r for r in read(PERSON / "protocol.json")["cases_fixed_before_ranking"]}
    assert protocol["case_ids"] == list(spec)
    base = read(BASE / "protocol.json")
    plans = {r["id"]: r for r in base["cases"]}
    authored = {}
    for line in (QI / "authored-inputs.tsv").read_text().splitlines():
        cid, query, _ = line.split("\t")
        authored[cid] = query
    cache = {}
    out = {"id": protocol["id"],
           "protocol_sha256": sha(HERE / "protocol.json"),
           "base_protocol_sha256": sha(BASE / "protocol.json"),
           "person_protocol_sha256": sha(PERSON / "protocol.json"),
           "authored_inputs_sha256": sha(QI / "authored-inputs.tsv"),
           "cases": []}
    for cid in protocol["case_ids"]:
        plan = plans[cid]
        baseline = read(BASE / "results" / f"{cid}.json")
        people = {p.casefold() for p in spec[cid]["people"]}
        all_ids = plan["original_source_ids"] + plan["distractor_source_ids"]
        originals = set(plan["original_source_ids"])
        records = {sid: load_source(sid, base["source_bank"], cache) for sid in all_ids}
        texts = {sid: r["text"] for sid, r in records.items()}
        speaker_ids = [sid for sid in all_ids if speakers(records[sid]) & people]
        scopes = {"all_1000": all_ids, "speaker_subset": speaker_ids,
                  "original_history": plan["original_source_ids"]}
        rows = {}
        for scope, ids in scopes.items():
            for qname, query in (("raw", baseline["question"]), ("authored", authored[cid])):
                ranking, _, _ = score.rank(ids, texts, query)
                rows[f"{qname}_{scope}"] = measure(ranking, baseline["official_reference_sources"], originals)
        old = read(PERSON / "results.json")
        older = next(x for x in old["cases"] if x["id"] == cid)
        assert rows["raw_all_1000"] == older["methods"]["raw_all_1000"]
        assert rows["raw_speaker_subset"] == older["methods"]["reindex_speaker_subset"]
        archived = read(QI / "rankings" / f"{cid}.json")["rankings"]
        assert [r["source_id"] for r in rows["raw_original_history"]["top5"]] == [r["source_id"] for r in archived["bm25_raw"][:5]]
        assert [r["source_id"] for r in rows["authored_original_history"]["top5"]] == [r["source_id"] for r in archived["bm25_rewritten"][:5]]
        out["cases"].append({"id": cid, "question": baseline["question"], "people": spec[cid]["people"],
                             "authored_query": authored[cid],
                             "scope_counts": {k: len(v) for k, v in scopes.items()},
                             "official_refs": baseline["official_reference_sources"],
                             "methods": rows})
    if verify:
        assert read(HERE / "results.json") == out
        print("verified 8/8 cases; raw and authored small-corpus rankings match archived results")
    else:
        with (HERE / "results.json").open("x") as stream:
            json.dump(out, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    for method in protocol["methods"]:
        print(method, "all", sum(c["methods"][method]["top5_all_official"] for c in out["cases"]),
              "any", sum(c["methods"][method]["top5_any_official"] for c in out["cases"]))


if __name__ == "__main__":
    main()
