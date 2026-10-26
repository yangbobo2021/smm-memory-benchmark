"""Evaluate unchanged BM25 on official M histories for the existing 57 questions."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import statistics
import sys

HERE=Path(__file__).resolve().parent
REPO=Path("/Users/boboyang/work/smm-memory-benchmark")
BASE=REPO/"experiments/smm-bm25-scale-1000-002"
sys.path.insert(0,str(BASE))
import score

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def body(turns):return "\n\n".join(str(turn["role"]).upper()+":\n"+str(turn["content"]) for turn in turns)

def main():
    protocol=load(HERE/"protocol.json")
    assert protocol["id"]=="SMM-OFFICIAL-M-500-001"
    for name,digest in protocol["code_hashes"].items():assert sha(HERE/name)==digest
    for name,digest in protocol["input_hashes"].items():
        path=(BASE/"protocol.json") if name=="base_protocol.json" else (HERE/name)
        assert sha(path)==digest,name
    base=load(BASE/"protocol.json")
    plans={c["id"]:c for c in base["cases"]}
    old_cases={c["id"]:c for c in load(REPO/"experiments/smm-baseline-001/data/cases.json")}
    new_cases={c["id"]:c for c in load(REPO/"experiments/smm-retrieval-generalization-001/data/cases.json")}
    source_files={};source_texts={}
    for sid,meta in base["source_bank"].items():
        name=meta["file"]
        if name.endswith(".jsonl"):continue
        if name not in source_files:
            d=load(REPO/name)
            source_files[name]={x["id"]:x for x in d["records"]} if "records" in d else {d["id"]:d}
        source_texts[sid]=source_files[name][sid]["text"]
    results=[]
    for cid in protocol["cases"]:
        path=HERE/"results"/f"{cid}.json"
        if path.exists():
            x=load(path);assert x["protocol_sha256"]==sha(HERE/"protocol.json");results.append(x);continue
        item=load(HERE/"cases"/f"{cid}.json")
        c=old_cases[cid] if cid in old_cases else new_cases[cid]
        assert item["question"]==c["question"]
        ids=item["haystack_session_ids"]
        dates=item["haystack_dates"]
        assert len(ids)==len(dates)==len(item["haystack_sessions"])==len(set(ids))
        texts={sid:body(turns) for sid,turns in zip(ids,item["haystack_sessions"])}
        refs=item["answer_session_ids"]
        assert refs and len(refs)==len(set(refs)) and set(refs)<=set(ids)
        ranking,build_s,query_s=score.rank(ids,texts,item["question"])
        m=score.measures(ranking,refs)
        s_ids=plans[cid]["original_source_ids"]
        s_hashes={hashlib.sha256(source_texts[sid].encode()).hexdigest() for sid in s_ids}
        s_ref_hashes={hashlib.sha256(source_texts[sid].encode()).hexdigest() for sid in c["official_reference_sources"]}
        m_ref_hashes={hashlib.sha256(texts[sid].encode()).hexdigest() for sid in refs}
        old=load(BASE/"results"/f"{cid}.json")
        result={"id":cid,"cohort":plans[cid]["cohort"],"type":c["type"],"protocol_sha256":sha(HERE/"protocol.json"),
                "question":item["question"],"official_question_id":item["question_id"],
                "official_m_count":len(ids),"official_m_ref_count":len(refs),
                "ref_text_hashes_equal_to_s":m_ref_hashes==s_ref_hashes,
                "m_ref_hashes_in_s":len(m_ref_hashes&s_ref_hashes),"s_ref_hashes_in_m":len(s_ref_hashes&m_ref_hashes),
                "m_s_body_overlap":sum(hashlib.sha256(t.encode()).hexdigest() in s_hashes for t in texts.values()),
                "original_s":{"count":len(s_ids),"top5":old["original"]["top5"],"top10":old["original"]["top10"]},
                "mixed1000":{"count":1000,"top5":old["expanded"]["top5"],"top10":old["expanded"]["top10"]},
                "official_m":{"top5":m["top5"],"top10":m["top10"],"reference_positions":m["reference_positions"],
                              "top10_ids":[x["source_id"] for x in ranking[:10]],"build_seconds":build_s,"query_seconds":query_s}}
        path.parent.mkdir(exist_ok=True)
        with path.open("x") as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write("\n")
        results.append(result)
        print(json.dumps({"done":len(results),"id":cid}),flush=True)
    summary={"id":protocol["id"],"protocol_sha256":sha(HERE/"protocol.json"),"cohorts":{}}
    for cohort in ("P25","L32","all57"):
        arr=results if cohort=="all57" else [x for x in results if x["cohort"]==cohort]
        d={"questions":len(arr),"m_count_min":min(x["official_m_count"] for x in arr),"m_count_max":max(x["official_m_count"] for x in arr),
           "m_count_median":statistics.median(x["official_m_count"] for x in arr),
           "equal_reference_texts":sum(x["ref_text_hashes_equal_to_s"] for x in arr),
           "m_s_overlap_median":statistics.median(x["m_s_body_overlap"] for x in arr)}
        for variant in ("original_s","official_m","mixed1000"):
            d[variant]={f"top{n}":{"all":sum(x[variant][f"top{n}"]["all"] for x in arr),
                                  "any":sum(x[variant][f"top{n}"]["any"] for x in arr)} for n in (5,10)}
        summary["cohorts"][cohort]=d
    target=HERE/"summary.json";assert not target.exists()
    target.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"complete":len(results),"summary":str(target)}))

if __name__=="__main__":main()
