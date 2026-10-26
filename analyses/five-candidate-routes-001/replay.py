"""Replay five frozen retrieval routes against pre-inference dependency labels."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EVALUATION = ROOT / "experiments/smm-sufficiency-luna-001/evaluation.json"
RUNTIME = ROOT / "experiments/smm-sufficiency-luna-001/runtime.json"
METHODS = ("bm25_top5", "vector_top5", "bm25_top10", "vector_top10", "bm25_top5_vector_top5")
COHORTS = ("original25", "longmemeval_new32", "locomo_random200")


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ranking_path(case_id):
    if case_id.startswith("P"):
        return ROOT / f"experiments/smm-baseline-001/data/retrieval/{case_id}.json"
    return ROOT / f"experiments/smm-retrieval-generalization-001/rankings/{case_id}.json"


def coverage(requirements, candidates):
    candidate_set = set(candidates)
    # A requirement is satisfied by any alternative witness; a witness can need
    # more than one source. This is the frozen SF-LUNA001 scoring convention.
    matched = [any(set(witness) <= candidate_set for witness in alternatives)
               for alternatives in requirements]
    return {"matched_units": sum(matched), "total_units": len(matched),
            "at_least_one": any(matched), "all": all(matched)}


def build():
    labels = read(EVALUATION)
    runtime = {item["id"]: item for item in read(RUNTIME)}
    assert len(labels) == len(runtime) == 257
    rows = []
    inputs = {str(EVALUATION.relative_to(ROOT)): digest(EVALUATION),
              str(RUNTIME.relative_to(ROOT)): digest(RUNTIME)}
    ambiguous = defaultdict(int)
    for label in labels:
        case_id = label["id"]
        context = runtime[case_id]
        path = ranking_path(case_id)
        inputs[str(path.relative_to(ROOT))] = digest(path)
        data = read(path)
        native = data["native"]["native"] if case_id.startswith("P") else data["native"]
        bm25 = [item["source_id"] for item in native["bm25"]]
        vector = [item["source_id"] for item in native["vector"]]
        assert len(bm25) == len(set(bm25)) == 10, case_id
        assert len(vector) == len(set(vector)) == 10, case_id
        assert bm25[:5] == context["initial_source_ids"], case_id
        assert set(bm25 + vector) <= set(context["source_ids"]), case_id
        if not label["semantic_evaluable"]:
            ambiguous[context["cohort"]] += 1
            continue
        requirements = label["requirements"]
        assert requirements, case_id
        candidates = {
            "bm25_top5": bm25[:5],
            "vector_top5": vector[:5],
            "bm25_top10": bm25,
            "vector_top10": vector,
            "bm25_top5_vector_top5": list(dict.fromkeys(bm25[:5] + vector[:5])),
        }
        rows.append({"id": case_id, "cohort": context["cohort"],
                     "routes": {name: {"candidate_ids": ids, **coverage(requirements, ids)}
                                for name, ids in candidates.items()}})
    assert len(rows) == 232 and sum(ambiguous.values()) == 25
    summary = {}
    for cohort in (*COHORTS, "total"):
        sample = [row for row in rows if cohort == "total" or row["cohort"] == cohort]
        summary[cohort] = {}
        for name in METHODS:
            route = [row["routes"][name] for row in sample]
            units = sum(item["total_units"] for item in route)
            summary[cohort][name] = {
                "cases": len(sample),
                "at_least_one": sum(item["at_least_one"] for item in route),
                "all": sum(item["all"] for item in route),
                "matched_units": sum(item["matched_units"] for item in route),
                "total_units": units,
                "candidate_total": sum(len(item["candidate_ids"]) for item in route),
                "candidate_min": min(len(item["candidate_ids"]) for item in route),
                "candidate_max": max(len(item["candidate_ids"]) for item in route),
            }
    pairwise = {}
    for cohort in (*COHORTS, "total"):
        sample = [row for row in rows if cohort == "total" or row["cohort"] == cohort]
        pairwise[cohort] = {}
        for name in ("vector_top10", "bm25_top5_vector_top5"):
            gain = [row["id"] for row in sample if row["routes"][name]["all"]
                    and not row["routes"]["bm25_top10"]["all"]]
            loss = [row["id"] for row in sample if row["routes"]["bm25_top10"]["all"]
                    and not row["routes"][name]["all"]]
            pairwise[cohort][name] = {"gain_vs_bm25_top10": gain,
                                      "loss_vs_bm25_top10": loss}
    return {"analysis": "SMM-FCR001", "scope": "Frozen source-witness dependencies, not answer correctness",
            "input_sha256": inputs, "excluded_ambiguous_by_cohort": dict(ambiguous),
            "summary": summary, "pairwise": pairwise, "cases": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build()
    target = HERE / "results.json"
    if args.check:
        assert read(target) == result
    else:
        with target.open("x") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    print(json.dumps({"summary": result["summary"], "excluded": result["excluded_ambiguous_by_cohort"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
