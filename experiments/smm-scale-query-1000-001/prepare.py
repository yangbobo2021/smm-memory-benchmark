"""Freeze two query-only variants before ranking on the 1000-source corpus."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/smm-bm25-scale-1000-002"
AUTHOR = ROOT / "experiments/smm-query-input-001/runtime.json"
STOP = frozenset("a an and are as at be been being by can could did do does for from had has have how i in into is it its me my of on or our ours she he her his their them they the these this those to was were what when where which who whom why will with would you your yours many much".split())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stopword_query(question: str) -> str:
    words = list(dict.fromkeys(re.findall(r"[^\W_]+", question.casefold(), re.UNICODE)))
    kept = [word for word in words if word not in STOP]
    return " ".join(kept or words)


def main() -> None:
    target = HERE / "protocol.json"
    assert not target.exists()
    base = json.loads((BASE / "protocol.json").read_text())
    authored = {x["id"]: x for x in json.loads(AUTHOR.read_text())}
    assert len(base["cases"]) == len(authored) == 257
    cases = []
    for plan in base["cases"]:
        cid = plan["id"]
        old = json.loads((BASE / "results" / f"{cid}.json").read_text())
        a = authored[cid]
        assert old["question"] == a["question"] and set(plan["original_source_ids"]) == set(a["source_ids"])
        cases.append({"id": cid, "cohort": plan["cohort"], "question": old["question"],
                      "authored_query": a["bm25_input"], "stopword_query": stopword_query(old["question"])})
    protocol = {
        "id": "SMM-SCALE-QUERY-1000-001", "status": "frozen-before-ranking",
        "baseline_protocol_sha256": sha(BASE / "protocol.json"),
        "authored_runtime_sha256": sha(AUTHOR),
        "method": "same 1000 full source texts, SQLite FTS5 unicode61 whole-source BM25; only query text changes",
        "variants": {"raw": "baseline archived original question", "authored": "earlier QI001 author-written keyword input, previously evaluated and not deployable or blind", "stopword": "fixed common-function-word deletion, no stemming, synonyms, labels or corpus-aware tuning"},
        "stopwords": sorted(STOP), "cases": cases,
        "implementation_hashes": {n: sha(HERE / n) for n in ["prepare.py", "run.py"]},
    }
    target.write_text(json.dumps(protocol, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"frozen": len(cases), "sha256": sha(target)}))


if __name__ == "__main__":
    main()
