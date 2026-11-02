import json, math, random
from collections import defaultdict
A="reports/anchor/airline-"
def load(r):
    d=defaultdict(list)
    for s in json.load(open(A+r+"/results.json"))["simulations"]:
        d[str(s["task_id"])].append(((s.get("reward_info") or {}).get("reward") or 0)>=0.999)
    return d
def ph(v,k):
    n=len(v);c=sum(v);return math.comb(c,k)/math.comb(n,k) if c>=k else 0
def m(d,ts,k): return 100*sum(ph(d[t],k) for t in ts)/len(ts)
R={k:load(v) for k,v in dict(base="none",best1="deliberate_reasoner",best2="deliberate_reasoner_rules",new="deliberate_reasoner_rules_consistency").items()}
ts=sorted(R["new"])
R["pooled"]={t:R["best1"][t]+R["best2"][t] for t in ts}
out={}
for k,d in R.items():
    out[k]={f"pass^{j}":round(m(d,ts,j),1) for j in (1,2,3,4)}
    out[k]["flaky"]=round(100*sum(0<sum(d[t])<len(d[t]) for t in ts)/len(ts));out[k]["always_fail"]=round(100*sum(sum(d[t])==0 for t in ts)/len(ts))
    print(k,out[k])
random.seed(0)
for ref in ("base","best1","best2","pooled"):
    for j in (1,4):
        obs=m(R["new"],ts,j)-m(R[ref],ts,j)
        bs=[]
        for _ in range(5000):
            s=[random.choice(ts) for _ in ts]
            bs.append(m(R["new"],s,j)-m(R[ref],s,j))
        bs.sort();p=sum(b>0 for b in bs)/len(bs)
        out[f"new_vs_{ref}_pass^{j}"]=dict(delta=round(obs,1),ci=[round(bs[125],1),round(bs[4875],1)],P=round(p,2))
        print(ref,j,out[f"new_vs_{ref}_pass^{j}"])
    better=sum(sum(R["new"][t])/len(R["new"][t])>sum(R[ref][t])/len(R[ref][t]) for t in ts);worse=sum(sum(R["new"][t])/len(R["new"][t])<sum(R[ref][t])/len(R[ref][t]) for t in ts)
    out[f"new_vs_{ref}_tasks"]=[better,worse];print(ref,"tasks better/worse",better,worse)
json.dump(out,open("reports/rules/e4_compare.json","w"),indent=1)
