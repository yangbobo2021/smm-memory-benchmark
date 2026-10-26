"""Post-hoc fixed RRF diagnostic over raw and frozen alternate query rankings."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/"experiments/smm-bm25-scale-1000-002"
sys.path.insert(0,str(BASE))
import score

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rrf(a,b,k):
    values={}
    for ranking in (a,b):
        for rank,row in enumerate(ranking,1):
            sid=row["source_id"]
            values[sid]=values.get(sid,0)+1/(k+rank)
    return [{"source_id":sid,"score":v} for sid,v in sorted(values.items(),key=lambda z:(-z[1],z[0]))]

def main():
    protocol_path=HERE/"fusion-protocol.json"
    if not protocol_path.exists():
        p={"id":"SMM-SCALE-QUERY-RRF-DIAGNOSTIC-001","status":"post-hoc, frozen before fused rankings",
           "query_protocol_sha256":sha(HERE/"protocol.json"),"base_protocol_sha256":sha(BASE/"protocol.json"),
           "code_sha256":sha(HERE/"fuse.py"),"k":60,
           "arms":["raw+authored","raw+stopword"],
           "note":"Authored input was previously human-written with benchmark familiarity; this is not a deployable or blind result."}
        protocol_path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n")
    protocol=load(protocol_path)
    assert sha(HERE/"fuse.py")==protocol["code_sha256"]
    assert sha(HERE/"protocol.json")==protocol["query_protocol_sha256"]
    assert sha(BASE/"protocol.json")==protocol["base_protocol_sha256"]
    queries={x["id"]:x for x in load(HERE/"protocol.json")["cases"]}
    base=load(BASE/"protocol.json")
    files={};texts={}
    for sid,meta in base["source_bank"].items():
        name=meta["file"]
        if name not in files:
            path=ROOT/name
            if name.endswith(".jsonl"):files[name]={x["source_id"]:x for x in (json.loads(line) for line in path.read_text().splitlines())}
            else:
                d=load(path);files[name]={x["id"]:x for x in d["records"]} if "records" in d else {d["id"]:d}
        text=files[name][sid]["text"]
        assert hashlib.sha256(text.encode()).hexdigest()==meta["source_sha256"]
        texts[sid]=text
    cases=[]
    for plan in base["cases"]:
        cid=plan["id"]
        path=HERE/"fusion-results"/f"{cid}.json"
        if path.exists():result=load(path);assert result["protocol_sha256"]==sha(protocol_path);cases.append(result);continue
        old=load(BASE/"results"/f"{cid}.json")
        q=queries[cid]
        ids=plan["original_source_ids"]+plan["distractor_source_ids"]
        refs=old["official_reference_sources"]
        ranks={"raw":score.rank(ids,texts,old["question"])[0]}
        assert score.measures(ranks["raw"],refs)["reference_positions"]==old["expanded"]["reference_positions"]
        for name in ("authored","stopword"):ranks[name]=score.rank(ids,texts,q[name+"_query"])[0]
        result={"id":cid,"cohort":plan["cohort"],"protocol_sha256":sha(protocol_path),"raw":{"top5":old["expanded"]["top5"],"top10":old["expanded"]["top10"]}}
        for name in ("authored","stopword"):
            fusion=rrf(ranks["raw"],ranks[name],protocol["k"])
            m=score.measures(fusion,refs)
            result["raw+"+name]={"top5":m["top5"],"top10":m["top10"],"reference_positions":m["reference_positions"],"top10_ids":[x["source_id"] for x in fusion[:10]]}
        path.parent.mkdir(exist_ok=True)
        with path.open("x") as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write("\n")
        cases.append(result)
        print(json.dumps({"done":len(cases),"id":cid}),flush=True)
    summary={"id":protocol["id"],"protocol_sha256":sha(protocol_path),"by_cohort":{}}
    for cohort in ("P25","L32","C200","all257"):
        arr=cases if cohort=="all257" else [x for x in cases if x["cohort"]==cohort]
        summary["by_cohort"][cohort]={"questions":len(arr)}
        for arm in ("raw","raw+authored","raw+stopword"):
            summary["by_cohort"][cohort][arm]={f"top{n}":{"all":sum(x[arm][f"top{n}"]["all"] for x in arr),"any":sum(x[arm][f"top{n}"]["any"] for x in arr)} for n in (5,10)}
    target=HERE/"fusion-summary.json"
    assert not target.exists()
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"complete":len(cases)}))

if __name__=="__main__":main()
