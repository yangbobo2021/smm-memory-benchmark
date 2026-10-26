"""Diagnostic ablation: index user and assistant turns separately at 1000 sources.

This is a post-hoc mechanism check, not part of the frozen primary benchmark.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import statistics

import score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ROLE = re.compile(r"(?:^|\n\n)(USER|ASSISTANT):\n")


def split_roles(record: dict) -> tuple[str, str]:
    raw = record["text"]
    if "structure" in record and record["structure"].get("parts"):
        parts = [(p["role"].upper(), raw[p["start"]:p["end"]]) for p in record["structure"]["parts"]]
    else:
        markers = list(ROLE.finditer(raw))
        assert markers and markers[0].start() == 0
        parts = [(m.group(1), raw[m.end():markers[i+1].start() if i+1 < len(markers) else len(raw)]) for i,m in enumerate(markers)]
    assert parts and all(role in ("USER", "ASSISTANT") for role, _ in parts)
    return "\n\n".join(t for role,t in parts if role == "USER"), "\n\n".join(t for role,t in parts if role == "ASSISTANT")


def main() -> None:
    protocol = json.loads((HERE / "protocol.json").read_text())
    cases = [c for c in protocol["cases"] if c["cohort"] in ("P25", "L32")]
    bank = protocol["source_bank"]
    by_file = {}
    field_texts = {"user": {}, "assistant": {}}
    ratios = []
    for sid in {sid for c in cases for sid in c["original_source_ids"] + c["distractor_source_ids"]}:
        path = bank[sid]["file"]
        assert not path.endswith(".jsonl")
        if path not in by_file:
            data = json.loads((ROOT / path).read_text())
            by_file[path] = {r["id"]: r for r in data["records"]} if "records" in data else {data["id"]: data}
        r = by_file[path][sid]
        u,a = split_roles(r)
        field_texts["user"][sid] = u
        field_texts["assistant"][sid] = a
        ratios.append(len(a) / max(1, len(u) + len(a)))
    output = []
    for case in cases:
        result = json.loads((HERE / "results" / f"{case['id']}.json").read_text())
        refs = result["official_reference_sources"]
        ids = case["original_source_ids"] + case["distractor_source_ids"]
        row = {"id": case["id"], "cohort": case["cohort"], "question": result["question"], "reference_sources": refs,
               "full": {"top5": result["expanded"]["top5"], "top10": result["expanded"]["top10"],
                        "reference_positions": result["expanded"]["reference_positions"]}}
        for role in ("user", "assistant"):
            ranking, _, _ = score.rank(ids, field_texts[role], result["question"])
            measures = score.measures(ranking, refs)
            row[role] = {"top5": measures["top5"], "top10": measures["top10"],
                         "reference_positions": measures["reference_positions"], "top10_ids": [x["source_id"] for x in ranking[:10]]}
        output.append(row)
    summary = {"source_count": len(ratios), "assistant_character_share_median": statistics.median(ratios), "cohorts": {}}
    for cohort in ("P25", "L32"):
        subset = [r for r in output if r["cohort"] == cohort]
        summary["cohorts"][cohort] = {role: {f"top{n}_all": sum(r[role][f"top{n}"]["all"] for r in subset)
                                               for n in (5, 10)} for role in ("full", "user", "assistant")}
        summary["cohorts"][cohort]["full_top5_misses_restored_by_user"] = sum(
            not r["full"]["top5"]["all"] and r["user"]["top5"]["all"] for r in subset)
        summary["cohorts"][cohort]["full_top10_misses_restored_by_user"] = sum(
            not r["full"]["top10"]["all"] and r["user"]["top10"]["all"] for r in subset)
    (HERE / "role-diagnostic.json").write_text(json.dumps({"summary": summary, "cases": output}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
