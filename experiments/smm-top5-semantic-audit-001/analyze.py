"""Recompute source provenance counts for the frozen 1000-conversation BM25 run.

Semantic judgments are in REPORT.md and deliberately not inferred by this code.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1] / "smm-bm25-scale-1000-002"


def main() -> None:
    protocol = json.loads((BASE / "protocol.json").read_text())
    plans = {case["id"]: case for case in protocol["cases"]}
    rankings = {
        row["id"]: row
        for row in map(json.loads, (BASE / "top10.jsonl").read_text().splitlines())
    }
    groups: dict[str, dict[str, object]] = defaultdict(
        lambda: {
            "questions": 0,
            "top5_all_official": 0,
            "top5_any_official": 0,
            "top5_no_official": 0,
            "fail_all_official": 0,
            "fail_all_top5_all_original": 0,
            "fail_all_top5_no_original": 0,
            "no_official_top5_no_original": 0,
            "no_official_ids": [],
        }
    )
    for case_id, plan in sorted(plans.items()):
        group = case_id[0]
        record = json.loads((BASE / "results" / f"{case_id}.json").read_text())
        top5 = rankings[case_id]["expanded"][:5]
        assert len(top5) == 5
        original = set(plan["original_source_ids"])
        refs = set(record["official_reference_sources"])
        assert refs <= original
        source_ids = [row["source_id"] for row in top5]
        assert len(set(source_ids)) == 5
        n_original = sum(source_id in original for source_id in source_ids)
        n_ref = sum(source_id in refs for source_id in source_ids)
        all_official = refs <= set(source_ids)
        any_official = n_ref > 0
        assert all_official == record["expanded"]["top5"]["all"]
        assert any_official == record["expanded"]["top5"]["any"]
        group_record = groups[group]
        group_record["questions"] += 1
        group_record["top5_all_official"] += int(all_official)
        group_record["top5_any_official"] += int(any_official)
        group_record["top5_no_official"] += int(not any_official)
        group_record["fail_all_official"] += int(not all_official)
        if not all_official:
            group_record["fail_all_top5_all_original"] += int(n_original == 5)
            group_record["fail_all_top5_no_original"] += int(n_original == 0)
        if not any_official:
            group_record["no_official_top5_no_original"] += int(n_original == 0)
            group_record["no_official_ids"].append(case_id)
    print(json.dumps(groups, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
