"""Mechanical amendment: official M repeats identical sessions; dedupe bodies."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def body(turns):return "\n\n".join(str(t["role"]).upper()+":\n"+str(t["content"]) for t in turns)

def main():
    target=HERE/"protocol-v2.json"
    assert not target.exists()
    old=load(HERE/"protocol.json")
    assert old["id"]=="SMM-OFFICIAL-M-500-001"
    assert sha(HERE/"score_m-v1.py")==old["code_hashes"]["score_m.py"]
    assert not (HERE/"results").exists() or not list((HERE/"results").glob("*.json"))
    duplicates={"cases_with_repeated_id":0,"extra_id_occurrences":0,
                "cases_with_different_ids_same_body":0,"extra_body_occurrences_after_id_dedupe":0,
                "repeated_id_different_body":0,"answer_body_collisions":0}
    for cid in old["cases"]:
        x=load(HERE/"cases"/f"{cid}.json")
        ids=x["haystack_session_ids"]
        texts=[body(t) for t in x["haystack_sessions"]]
        hashes=[hashlib.sha256(t.encode()).hexdigest() for t in texts]
        assert len(ids)==len(texts)==len(x["haystack_dates"])
        id_to_hash={}
        for sid,h in zip(ids,hashes):
            if sid in id_to_hash and id_to_hash[sid]!=h:duplicates["repeated_id_different_body"]+=1
            id_to_hash[sid]=h
        extra_id=len(ids)-len(set(ids))
        extra_body=len(set(ids))-len(set(hashes))
        if extra_id:duplicates["cases_with_repeated_id"]+=1
        if extra_body:duplicates["cases_with_different_ids_same_body"]+=1
        duplicates["extra_id_occurrences"]+=extra_id
        duplicates["extra_body_occurrences_after_id_dedupe"]+=extra_body
        h_to_ids={}
        for sid,h in zip(ids,hashes):h_to_ids.setdefault(h,set()).add(sid)
        for group in h_to_ids.values():
            if len(group)>1 and group.intersection(x["answer_session_ids"]):duplicates["answer_body_collisions"]+=1
    assert duplicates["repeated_id_different_body"]==0
    protocol={"id":"SMM-OFFICIAL-M-500-002","status":"frozen-before-first-ranking; mechanical repair of rejected v1",
              "supersedes_sha256":sha(HERE/"protocol.json"),"failure_receipt":"score.log",
              "reason":"The official M file repeats exact full sessions: duplicate external IDs and, sometimes, same body under different IDs. V1 wrongly assumed IDs unique and stopped before any result.",
              "selection":"Preserve first occurrence of each distinct serialized full body, input order, without consulting query or references. Map all answer IDs through the resulting body alias.",
              "duplicate_audit":duplicates,
              "input_hashes":old["input_hashes"],"cases":old["cases"],
              "code_hashes":{n:sha(HERE/n) for n in ("prepare_m_v2.py","score_m.py")},
              "method":old["method"],"metric":old["metric"],"upstream":old["upstream"],"revision":old["revision"],
              "raw_sha256":old["raw_sha256"]}
    target.write_text(json.dumps(protocol,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"frozen":len(old["cases"]),"duplicates":duplicates,"sha256":sha(target)}))

if __name__=="__main__":main()
