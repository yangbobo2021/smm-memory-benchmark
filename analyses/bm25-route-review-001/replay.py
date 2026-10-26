"""Replay completed lexical and query-input rankings against fixed answer dependencies.

This script scores saved source rankings only. It never calls an encoder, model,
network service, or the unfinished neural arms of SMM-MC001.
"""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LABELS = ROOT / "experiments/smm-sufficiency-luna-001/evaluation.json"
RUNTIME = ROOT / "experiments/smm-sufficiency-luna-001/runtime.json"
QUERY = ROOT / "experiments/smm-query-input-001/rankings"
ROLE = ROOT / "experiments/smm-bm25-role-weight-001/rankings"
LEXICAL = HERE / "lexical-rankings"
LEXICAL_METHODS = ("baseline", "stem", "local_rrf", "coverage_proximity",
                   "bm25_b025", "bm25_k06", "bm25plus", "bm25l")
QUERY_METHODS = ("bm25_raw", "vector_raw", "bm25_rewritten", "vector_rewritten")
COHORTS = ("original25", "longmemeval_new32", "locomo_random200")


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ids(rankings):
    return [item["source_id"] for item in rankings]


def coverage(requirements, candidates):
    source_set = set(candidates)
    matched = [any(set(witness) <= source_set for witness in alternatives)
               for alternatives in requirements]
    return {"candidate_count": len(candidates), "matched_units": sum(matched),
            "total_units": len(matched), "any": any(matched), "all": all(matched)}


def snapshot_check():
    manifest = read(HERE / "source-manifest.json")
    assert len(manifest["ranking_files_sha256"]) == 257
    assert manifest["frozen_protocol_sha256"] == digest(HERE / "frozen-protocol.json")
    assert manifest["lexical_first_summary_sha256"] == digest(HERE / "lexical-first-summary.json")
    for name, expected in manifest["source_code_sha256"].items():
        assert digest(HERE / name) == expected, name
    for name, expected in manifest["ranking_files_sha256"].items():
        assert digest(LEXICAL / name) == expected, name
    assert sorted(path.name for path in LEXICAL.glob("*.json")) == sorted(manifest["ranking_files_sha256"])


def score_rows():
    snapshot_check()
    labels = read(LABELS)
    runtime = {item["id"]: item for item in read(RUNTIME)}
    assert len(labels) == len(runtime) == 257
    inputs = {str(LABELS.relative_to(ROOT)): digest(LABELS),
              str(RUNTIME.relative_to(ROOT)): digest(RUNTIME)}
    rows, ambiguous = [], defaultdict(int)
    for label in labels:
        case_id = label["id"]
        context = runtime[case_id]
        lexical_path = LEXICAL / f"{case_id}.json"
        query_path = QUERY / f"{case_id}.json"
        inputs[str(query_path.relative_to(ROOT))] = digest(query_path)
        lexical = read(lexical_path)["rankings"]
        query = read(query_path)["rankings"]
        assert all(name in lexical for name in LEXICAL_METHODS)
        assert all(name in query for name in QUERY_METHODS)
        assert ids(lexical["baseline"][:10]) == ids(query["bm25_raw"][:10]), case_id
        assert ids(lexical["archived_vector"][:10]) == ids(query["vector_raw"][:10]), case_id
        assert ids(query["bm25_raw"][:5]) == context["initial_source_ids"], case_id
        role = None
        if context["cohort"] != "locomo_random200":
            role_path = ROLE / f"{case_id}.json"
            inputs[str(role_path.relative_to(ROOT))] = digest(role_path)
            role = read(role_path)["rankings"]
            assert ids(role["whole"][:10]) == ids(query["bm25_raw"][:10]), case_id
        if not label["semantic_evaluable"]:
            ambiguous[context["cohort"]] += 1
            continue
        requirements = label["requirements"]
        assert requirements, case_id
        source_universe = set(context["source_ids"])
        routes = {}
        for name in LEXICAL_METHODS:
            ranking = ids(lexical[name])
            assert len(ranking) == len(set(ranking)) and set(ranking) <= source_universe
            for n in (5, 10):
                routes[f"lexical/{name}/top{n}"] = coverage(requirements, ranking[:n])
        for name in QUERY_METHODS:
            ranking = ids(query[name])
            assert len(ranking) == len(set(ranking)) and set(ranking) <= source_universe
            for n in (5, 10):
                routes[f"query/{name}/top{n}"] = coverage(requirements, ranking[:n])
        for name, left, right in (
            ("raw_raw", "bm25_raw", "vector_raw"),
            ("rewritten_rewritten", "bm25_rewritten", "vector_rewritten"),
            ("rewritten_raw", "bm25_rewritten", "vector_raw"),
            ("raw_rewritten", "bm25_raw", "vector_rewritten"),
        ):
            merged = list(dict.fromkeys(ids(query[left][:5]) + ids(query[right][:5])))
            routes[f"query_union/{name}/top5_each"] = coverage(requirements, merged)
        if role is not None:
            for name in ("whole", "split50", "split70"):
                ranking = ids(role[name])
                assert len(ranking) == len(set(ranking)) and set(ranking) <= source_universe
                for n in (5, 10):
                    routes[f"role/{name}/top{n}"] = coverage(requirements, ranking[:n])
        rows.append({"id": case_id, "cohort": context["cohort"], "routes": routes})
    assert len(rows) == 232 and dict(ambiguous) == {
        "original25": 2, "longmemeval_new32": 1, "locomo_random200": 22}
    return rows, dict(ambiguous), inputs


def aggregate(rows):
    out = {}
    for cohort in (*COHORTS, "total"):
        sample = [row for row in rows if cohort == "total" or row["cohort"] == cohort]
        names = sorted({key for row in sample for key in row["routes"]})
        out[cohort] = {}
        for name in names:
            items = [row["routes"][name] for row in sample if name in row["routes"]]
            out[cohort][name] = {
                "cases": len(items), "any": sum(item["any"] for item in items),
                "all": sum(item["all"] for item in items),
                "matched_units": sum(item["matched_units"] for item in items),
                "total_units": sum(item["total_units"] for item in items),
                "candidate_total": sum(item["candidate_count"] for item in items),
            }
    return out


def paired(rows, old, new):
    return {
        "gain": [row["id"] for row in rows if not row["routes"][old]["all"]
                 and row["routes"][new]["all"]],
        "loss": [row["id"] for row in rows if row["routes"][old]["all"]
                 and not row["routes"][new]["all"]],
    }


def build():
    rows, ambiguous, inputs = score_rows()
    comparisons = {}
    for n in (5, 10):
        comparisons[f"bm25_rewrite_top{n}"] = paired(
            rows, f"query/bm25_raw/top{n}", f"query/bm25_rewritten/top{n}")
    comparisons["union_both_rewritten"] = paired(
        rows, "query_union/raw_raw/top5_each", "query_union/rewritten_rewritten/top5_each")
    comparisons["rewritten_top5_to_top10"] = paired(
        rows, "query/bm25_rewritten/top5", "query/bm25_rewritten/top10")
    return {"id": "SMM-BR001", "scope": "Frozen source-witness coverage; not answer accuracy",
            "input_sha256": inputs, "ambiguous_excluded": ambiguous,
            "summary": aggregate(rows), "paired": comparisons, "cases": rows}


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
    print(json.dumps({"cases": len(result["cases"]),
                      "ambiguous_excluded": result["ambiguous_excluded"],
                      "query_comparison": {k: result["summary"]["total"][k]
                                           for k in ("query/bm25_raw/top5",
                                                     "query/bm25_rewritten/top5",
                                                     "query/bm25_raw/top10",
                                                     "query/bm25_rewritten/top10")}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
