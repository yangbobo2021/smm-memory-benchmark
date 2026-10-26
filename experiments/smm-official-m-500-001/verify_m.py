"""Offline numerical replay and temporal/source binding for the M comparison."""
from __future__ import annotations
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
REPO=Path("/Users/boboyang/work/smm-memory-benchmark")
sys.path.insert(0,str(REPO/"experiments/smm-bm25-scale-1000-002"))
import score
from score_m import body

def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def when(s):return datetime.strptime(s,"%Y/%m/%d (%a) %H:%M")

def main():
    protocol=load(HERE/"protocol-v2.json")
    assert protocol["id"]=="SMM-OFFICIAL-M-500-002"
    assert len(list((HERE/"results").glob("*.json")))==57
    results=[];future_cases={};future_reference_cases={}
    for cid in protocol["cases"]:
        item=load(HERE/"cases"/f"{cid}.json")
        stored=load(HERE/"results"/f"{cid}.json")
        assert stored["protocol_sha256"]==sha(HERE/"protocol-v2.json")
        ids=item["haystack_session_ids"]
        assert len(ids)==stored["official_m_occurrences"]
        # The upstream M histories contain same-day sessions later than the
        # question. Audit this data defect; preserve the frozen ranking input.
        future=[sid for sid,date in zip(ids,item["haystack_dates"]) if when(date)>when(item["question_date"])]
        if future:
            future_cases[cid]=len(future)
            refs_future=sorted(set(future)&set(item["answer_session_ids"]))
            if refs_future:future_reference_cases[cid]=refs_future
        unique_ids=[];texts={};canonical_by_hash={};canonical_by_id={}
        for sid,turns in zip(ids,item["haystack_sessions"]):
            content=body(turns)
            digest=hashlib.sha256(content.encode()).hexdigest()
            if digest not in canonical_by_hash:
                assert sid not in texts,cid
                canonical_by_hash[digest]=sid
                unique_ids.append(sid)
                texts[sid]=content
            canonical_by_id[sid]=canonical_by_hash[digest]
        assert len(unique_ids)==len(set(unique_ids))==stored["official_m_count"]
        refs=list(dict.fromkeys(canonical_by_id[sid] for sid in item["answer_session_ids"]))
        assert len(refs)==stored["official_m_ref_count"]
        ranking,_,_=score.rank(unique_ids,texts,item["question"])
        replay=score.measures(ranking,refs)
        assert replay["top5"]==stored["official_m"]["top5"],cid
        assert replay["top10"]==stored["official_m"]["top10"],cid
        assert replay["reference_positions"]==stored["official_m"]["reference_positions"],cid
        assert [r["source_id"] for r in ranking[:10]]==stored["official_m"]["top10_ids"],cid
        results.append(stored)
    summary=load(HERE/"summary.json")
    for cohort in ("P25","L32","all57"):
        arr=results if cohort=="all57" else [x for x in results if x["cohort"]==cohort]
        assert summary["cohorts"][cohort]["questions"]==len(arr)
        for variant in ("original_s","official_m","mixed1000"):
            for n in (5,10):
                row=summary["cohorts"][cohort][variant][f"top{n}"]
                assert row["all"]==sum(x[variant][f"top{n}"]["all"] for x in arr)
                assert row["any"]==sum(x[variant][f"top{n}"]["any"] for x in arr)
    print(json.dumps({"verified":57,"numeric_replay":True,
                      "future_session_cases":future_cases,
                      "future_reference_cases":future_reference_cases}))

if __name__=="__main__":main()
