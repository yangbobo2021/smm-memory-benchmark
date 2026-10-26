"""Freeze turn-index diagnostic before running 57 LongMemEval cases."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/smm-bm25-scale-1000-002"

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    target = HERE / "protocol.json"
    assert not target.exists()
    base = json.loads((BASE / "protocol.json").read_text())
    cases = [{"id": c["id"], "cohort": c["cohort"]} for c in base["cases"] if c["cohort"] in ("P25", "L32")]
    assert len(cases) == 57
    p = {"id": "SMM-TURN-INDEX-1000-001", "status": "frozen-before-ranking",
         "base_protocol_sha256": sha(BASE / "protocol.json"),
         "unit": "pre-existing USER turn or one USER+following ASSISTANT exchange; no generated summaries/facts",
         "variants": ["best_user_turn", "best_exchange", "rrf_full_user"],
         "rrf_constant": 60,
         "pool": "same frozen 1000 full sources per question", "question": "unchanged original question",
         "metric": "all and any official reference source IDs in Top5/Top10; not answer accuracy",
         "cases": cases, "implementation_hashes": {n: sha(HERE / n) for n in ("prepare.py", "run.py")}}
    target.write_text(json.dumps(p, indent=2) + "\n")
    print(json.dumps({"frozen": len(cases), "sha256": sha(target)}))

if __name__ == "__main__": main()
