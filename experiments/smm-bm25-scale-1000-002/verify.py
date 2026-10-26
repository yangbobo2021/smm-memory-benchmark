"""Offline replay and integrity checks for the frozen 1000-session experiment."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text())


def main() -> None:
    protocol_path = HERE / "protocol.json"
    protocol = load(protocol_path)
    assert protocol["id"] == "SMM-BM25-SCALE-1000-002"
    for name, expected in protocol["input_hashes"].items():
        assert digest(ROOT / name) == expected, name
    for name, expected in protocol["implementation_hashes"].items():
        assert digest(HERE / name) == expected, name
    bank = protocol["source_bank"]
    by_file: dict[str, dict] = {}
    texts: dict[str, str] = {}
    for sid, meta in bank.items():
        path = meta["file"]
        if path not in by_file:
            if path.endswith(".jsonl"):
                by_file[path] = {x["source_id"]: x for x in (json.loads(line) for line in (ROOT / path).read_text().splitlines())}
            else:
                data = load(ROOT / path)
                by_file[path] = {x["id"]: x for x in data["records"]} if "records" in data else {data["id"]: data}
        text = by_file[path][sid]["text"]
        assert hashlib.sha256(text.encode()).hexdigest() == meta["source_sha256"], sid
        texts[sid] = text
    assert len(texts) == 3675
    assert len(list((HERE / "results").glob("*.json"))) == 257
    traces = {x["id"]: x for x in (json.loads(line) for line in (HERE / "top10.jsonl").read_text().splitlines())}
    assert len(traces) == 257
    corpus_sets = set()
    results = []
    checked = 0
    for case in protocol["cases"]:
        cid = case["id"]
        result = load(HERE / "results" / f"{cid}.json")
        assert result["protocol_sha256"] == digest(protocol_path), cid
        ids = case["original_source_ids"] + case["distractor_source_ids"]
        assert len(ids) == len(set(ids)) == 1000, cid
        assert len({bank[sid]["source_sha256"] for sid in ids}) == 1000, cid
        assert set(result["official_reference_sources"]) <= set(case["original_source_ids"]), cid
        if case["cohort"] == "C200":
            corpus_sets.add(frozenset(ids))
        for label, pool in (("original", case["original_source_ids"]), ("expanded", ids)):
            ranked, _, _ = score.rank(pool, texts, result["question"])
            replay = score.measures(ranked, result["official_reference_sources"])
            assert replay == result[label], (cid, label)
            assert ranked[:10] == traces[cid][label], (cid, label, "trace")
        results.append(result)
        checked += 1
    assert len(corpus_sets) == 1
    summary = load(HERE / "summary.json")
    assert summary["case_count"] == checked == 257
    for cohort, count in (("P25", 25), ("L32", 32), ("C200", 200)):
        assert summary["by_cohort"][cohort]["questions"] == count
    for cohort in ("P25", "L32", "C200", "all257"):
        subset = results if cohort == "all257" else [r for r in results if r["cohort"] == cohort]
        for label in ("original", "expanded"):
            for n in (1, 3, 5, 10):
                archived = summary["by_cohort"][cohort][label][f"top{n}"]
                actual = [r[label][f"top{n}"] for r in subset]
                assert archived["all"] == sum(x["all"] for x in actual)
                assert archived["any"] == sum(x["any"] for x in actual)
                assert archived["reference_hits"] == sum(x["reference_count"] for x in actual)
    print(json.dumps({"verified_cases": checked, "unique_source_texts_per_case": 1000,
                      "common_locomo_corpus": True, "numeric_replay": "passed"}))


if __name__ == "__main__":
    main()
