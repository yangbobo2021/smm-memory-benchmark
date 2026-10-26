"""Emit complete Top10 rank traces without changing the frozen score protocol."""
from __future__ import annotations

import json
from pathlib import Path

import score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main() -> None:
    protocol = json.loads((HERE / "protocol.json").read_text())
    by_file = {}
    texts = {}
    for sid, meta in protocol["source_bank"].items():
        name = meta["file"]
        if name not in by_file:
            path = ROOT / name
            if name.endswith(".jsonl"):
                by_file[name] = {x["source_id"]: x for x in (json.loads(line) for line in path.read_text().splitlines())}
            else:
                data = json.loads(path.read_text())
                by_file[name] = {x["id"]: x for x in data["records"]} if "records" in data else {data["id"]: data}
        texts[sid] = by_file[name][sid]["text"]
    output = HERE / "top10.jsonl"
    assert not output.exists()
    with output.open("x") as file:
        for case in protocol["cases"]:
            cid = case["id"]
            result = json.loads((HERE / "results" / f"{cid}.json").read_text())
            original = case["original_source_ids"]
            expanded = original + case["distractor_source_ids"]
            a = score.rank(original, texts, result["question"])[0][:10]
            b = score.rank(expanded, texts, result["question"])[0][:10]
            file.write(json.dumps({"id": cid, "original": a, "expanded": b}, ensure_ascii=False) + "\n")
    print(json.dumps({"cases": len(protocol["cases"]), "output": str(output)}))


if __name__ == "__main__":
    main()
