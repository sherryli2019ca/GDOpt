"""Would the hand-written consistency checks have been found by an automatic loop that only sees a third of the tasks?

Zero-cost check for the RSI design: for 200 random 3-fold task splits of the airline logs (13 runs, 2600 episodes),
a check counts as "found" on the mining fold if it fires in >= 2 failed episodes there and fail fires >= 3x success
fires; it "transfers" if on the other two folds it fires in >= 1 failed episode with the same 3x ratio.
Run from repo root; writes reports/determinism/rsi_fold_transfer.json.
"""
import json,sys,random
from collections import defaultdict,Counter
from pathlib import Path
sys.path.insert(0,'examples/determinism'); sys.path.insert(0,'src')
import new_rule_audit as N
RUNS=N.RUNS+["deliberate_reasoner_rules_consistency","policy","policy_reasoner","vote"]
recs=[]
for run in RUNS:
    p=Path(f"reports/anchor/airline-{run}/results.json")
    if not p.exists(): continue
    for s in json.load(open(p))["simulations"]:
        ok=((s.get("reward_info") or {}).get("reward") or 0)>=0.999
        recs.append((str(s["task_id"]),ok,set(N.audit(s))))
out={'episodes':len(recs),'rules':{}}
rules=sorted({r for _,_,f in recs for r in f})
for r in rules:
    ft=Counter(t for t,ok,f in recs if r in f and not ok); st=Counter(t for t,ok,f in recs if r in f and ok)
    out["rules"][r]={"fail_eps_by_task":dict(ft),"success_eps":sum(st.values())}
# 3-fold: rule 'discovered' in mining fold if >=2 fail eps there and fail>=3*succ; does it discriminate in held out?
tasks=sorted({t for t,_,_ in recs},key=int)
res=Counter()
for seed in range(200):
    random.Random(seed).shuffle(tasks)
    folds=[set(tasks[i::3]) for i in range(3)]
    for k in range(3):
        mine=folds[k]; held=set(tasks)-mine
        for r in rules:
            fm=sum(1 for t,ok,f in recs if t in mine and r in f and not ok); sm=sum(1 for t,ok,f in recs if t in mine and r in f and ok)
            if fm>=2 and fm>=3*sm:
                res[r,'found']+=1
                fh=sum(1 for t,ok,f in recs if t in held and r in f and not ok); sh=sum(1 for t,ok,f in recs if t in held and r in f and ok)
                if fh>=1: res[r,'heldfires']+=1
                if fh>=1 and fh>=3*sh: res[r,'heldok']+=1
for r in rules:
    out['rules'][r].update({k:round(res[r,k]/600,3) for k in ['found','heldfires','heldok']})
Path('reports/determinism/rsi_fold_transfer.json').write_text(json.dumps(out,indent=1))
print(json.dumps(out,indent=1))
