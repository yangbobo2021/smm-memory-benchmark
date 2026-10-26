"""Rank full sources using their strongest USER turn or USER/ASSISTANT exchange."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/smm-bm25-scale-1000-002"
sys.path.insert(0, str(BASE))
import score

MARKER = re.compile(r"(?:^|\n\n)(USER|ASSISTANT):\n")

def load(path): return json.loads(path.read_text())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def turns(record):
    raw = record["text"]
    if "structure" in record and record["structure"].get("parts"):
        parts = [(x["role"].upper(), raw[x["start"]:x["end"]]) for x in record["structure"]["parts"]]
    else:
        markers = list(MARKER.finditer(raw))
        assert markers and markers[0].start() == 0
        parts = [(m.group(1), raw[m.end():markers[i+1].start() if i+1 < len(markers) else len(raw)]) for i,m in enumerate(markers)]
    assert parts and all(r in ("USER", "ASSISTANT") for r,_ in parts)
    return parts

def unit_texts(parts, variant):
    if variant == "best_user_turn": return [text for role,text in parts if role == "USER"]
    units = []
    for role,text in parts:
        if role == "USER": units.append(text)
        elif units: units[-1] += "\n\n" + text
    return units

def rank_units(ids, parts_by_id, question, variant):
    start = time.perf_counter()
    db = sqlite3.connect(":memory:")
    try:
        db.execute("create virtual table t using fts5(body, tokenize='unicode61')")
        source_for_row = []
        rows = []
        for sid in ids:
            for body in unit_texts(parts_by_id[sid], variant):
                source_for_row.append(sid)
                rows.append((len(source_for_row), body))
        db.executemany("insert into t(rowid,body) values (?,?)", rows)
        build_s = time.perf_counter() - start
        expr = score.lexical_expression(question)
        qstart = time.perf_counter()
        best = {}
        if expr:
            for rowid, value in db.execute("select rowid,bm25(t) from t where t match ?", (expr,)):
                sid = source_for_row[rowid-1]
                candidate = -float(value)
                if candidate > best.get(sid, float("-inf")): best[sid] = candidate
        ranked = sorted(best.items(), key=lambda pair:(-pair[1],pair[0]))
        query_s = time.perf_counter() - qstart
        return [{"source_id":sid,"score":value} for sid,value in ranked], len(rows), build_s, query_s
    finally: db.close()

def rrf(full, user, constant=60):
    scores = {}
    for ranking in (full,user):
        for i,row in enumerate(ranking,1):
            sid = row["source_id"]
            scores[sid] = scores.get(sid,0) + 1/(constant+i)
    return [{"source_id":sid,"score":v} for sid,v in sorted(scores.items(), key=lambda pair:(-pair[1],pair[0]))]

def main():
    protocol = load(HERE / "protocol.json")
    assert protocol["id"] == "SMM-TURN-INDEX-1000-001" and sha(BASE / "protocol.json") == protocol["base_protocol_sha256"]
    for name,digest in protocol["implementation_hashes"].items(): assert sha(HERE / name) == digest
    base = load(BASE / "protocol.json")
    plans = {x["id"]:x for x in base["cases"]}
    needed = {sid for c in protocol["cases"] for sid in plans[c["id"]]["original_source_ids"]+plans[c["id"]]["distractor_source_ids"]}
    by_file = {}
    parts_by_id = {}
    text_by_id = {}
    for sid in needed:
        meta = base["source_bank"][sid]
        name = meta["file"]
        assert not name.endswith(".jsonl")
        if name not in by_file:
            data = load(ROOT / name)
            by_file[name] = {x["id"]:x for x in data["records"]} if "records" in data else {data["id"]:data}
        record = by_file[name][sid]
        assert hashlib.sha256(record["text"].encode()).hexdigest() == meta["source_sha256"]
        parts_by_id[sid] = turns(record)
        text_by_id[sid] = record["text"]
    results=[]
    for case in protocol["cases"]:
        cid=case["id"]
        path=HERE / "results" / f"{cid}.json"
        if path.exists():
            result=load(path)
            assert result["protocol_sha256"]==sha(HERE / "protocol.json")
            results.append(result);continue
        plan=plans[cid]
        ids=plan["original_source_ids"]+plan["distractor_source_ids"]
        old=load(BASE / "results" / f"{cid}.json")
        refs=old["official_reference_sources"]
        full,_,_=score.rank(ids,text_by_id,old["question"])
        assert score.measures(full,refs)["reference_positions"]==old["expanded"]["reference_positions"]
        result={"id":cid,"cohort":case["cohort"],"protocol_sha256":sha(HERE / "protocol.json"),"refs":refs,
                "full": {"top5": old["expanded"]["top5"], "top10": old["expanded"]["top10"],
                         "reference_positions": old["expanded"]["reference_positions"]}}
        user=[]
        for variant in ("best_user_turn", "best_exchange"):
            ranking,units,build_s,query_s=rank_units(ids,parts_by_id,old["question"],variant)
            m=score.measures(ranking,refs)
            result[variant]={"top5":m["top5"],"top10":m["top10"],"reference_positions":m["reference_positions"],
                             "top10_ids":[x["source_id"] for x in ranking[:10]],"units":units,"build_seconds":build_s,"query_seconds":query_s}
            if variant=="best_user_turn":user=ranking
        fused=rrf(full,user,protocol["rrf_constant"])
        m=score.measures(fused,refs)
        result["rrf_full_user"]={"top5":m["top5"],"top10":m["top10"],"reference_positions":m["reference_positions"],
                                 "top10_ids":[x["source_id"] for x in fused[:10]]}
        path.parent.mkdir(exist_ok=True)
        with path.open("x") as file:json.dump(result,file,ensure_ascii=False,indent=2);file.write("\n")
        results.append(result)
        print(json.dumps({"done":len(results),"id":cid}),flush=True)
    summary={"id":protocol["id"],"protocol_sha256":sha(HERE / "protocol.json"),"by_cohort":{}}
    for cohort in ("P25","L32","all57"):
        subset=results if cohort=="all57" else [r for r in results if r["cohort"]==cohort]
        d={"questions":len(subset)}
        for variant in ("full","best_user_turn","best_exchange","rrf_full_user"):
            d[variant]={f"top{n}":{"all":sum(r[variant][f"top{n}"]["all"] for r in subset),
                                  "any":sum(r[variant][f"top{n}"]["any"] for r in subset),
                                  "reference_hits":sum(r[variant][f"top{n}"]["reference_count"] for r in subset)} for n in (5,10)}
            if variant!="full":d[variant]["paired_top5"]={"gains":[r["id"] for r in subset if not r["full"]["top5"]["all"] and r[variant]["top5"]["all"]],
                                                           "losses":[r["id"] for r in subset if r["full"]["top5"]["all"] and not r[variant]["top5"]["all"]]}
        summary["by_cohort"][cohort]=d
    target=HERE / "summary.json"
    assert not target.exists()
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"complete":len(results),"summary":str(target)}))

if __name__ == "__main__":main()
