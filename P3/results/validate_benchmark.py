#!/usr/bin/env python3
"""Fail-closed validator for the versioned P3 benchmark V2 CSV."""
from __future__ import annotations
import argparse, csv, json, math, sys
from datetime import datetime
from pathlib import Path

HEADER = ["timestamp","run_id","benchmark_id","dimension","non_zero_count","parallelism","threshold","warmup_iterations","measured_iterations","sequential_mean_ms","sequential_median_ms","sequential_stddev_ms","parallel_mean_ms","parallel_median_ms","parallel_stddev_ms","speedup","sequential_throughput_states_per_s","parallel_throughput_states_per_s","sequential_expected_error","parallel_expected_error","max_absolute_error","setup_time_ms","cpu","max_jvm_memory_bytes","free_jvm_heap_bytes","java_version","operating_system","notes"]
EPSILON=1e-12
class ValidationError(ValueError): pass

def need(ok, msg):
    if not ok: raise ValidationError(msg)
def num(row,key):
    try: v=float(row[key])
    except (ValueError,TypeError,KeyError) as e: raise ValidationError(f"{key} must be numeric") from e
    need(math.isfinite(v),f"{key} must be finite"); return v
def integer(row,key):
    try: return int(row[key])
    except (ValueError,TypeError,KeyError) as e: raise ValidationError(f"{key} must be an integer") from e
def close(a,b,name): need(math.isclose(a,b,rel_tol=1e-8,abs_tol=1e-12),f"{name} mismatch: {a} != {b}")
def validate(path:Path, expected=None):
    need(path.is_file(),f"CSV file does not exist: {path}")
    with path.open(encoding="utf-8",newline="") as f:
        rd=csv.DictReader(f); need(rd.fieldnames==HEADER,"CSV V2 header mismatch"); rows=list(rd)
    need(bool(rows),"CSV contains no benchmark data rows")
    checked=[]
    for ix,r in enumerate(rows,1):
        try:
            need(None not in r and all(v is not None for v in r.values()),"malformed CSV row")
            stamp=r["timestamp"].replace("Z","+00:00")
            dt=datetime.fromisoformat(stamp); need(dt.tzinfo is not None,"timestamp requires timezone")
            need(bool(r["run_id"].strip()),"run_id is empty")
            n=integer(r,"dimension"); nnz=integer(r,"non_zero_count"); p=integer(r,"parallelism"); th=integer(r,"threshold"); w=integer(r,"warmup_iterations"); it=integer(r,"measured_iterations")
            need(n>0 and nnz==2*n and p>0 and th>0 and w>=0 and it>0,"invalid workload/configuration")
            need(r["benchmark_id"]==("QFLPN-12" if n==12 else "QFLPN-1M" if n==1000000 else "QFLPN-30M" if n==30000000 else f"QFLPN-{n}"),"benchmark_id mismatch")
            sm=num(r,"sequential_mean_ms"); sd=num(r,"sequential_median_ms"); ss=num(r,"sequential_stddev_ms")
            pm=num(r,"parallel_mean_ms"); pd=num(r,"parallel_median_ms"); ps=num(r,"parallel_stddev_ms")
            speed=num(r,"speedup"); st=num(r,"sequential_throughput_states_per_s"); pt=num(r,"parallel_throughput_states_per_s")
            se=num(r,"sequential_expected_error"); pe=num(r,"parallel_expected_error"); diff=num(r,"max_absolute_error")
            setup=num(r,"setup_time_ms"); maxheap=integer(r,"max_jvm_memory_bytes"); freeheap=integer(r,"free_jvm_heap_bytes")
            need(min(sm,sd,pm,pd,speed)>0,"times and speedup must be positive")
            need(min(ss,ps,se,pe,diff,setup)>=0,"error, dispersion and setup must be nonnegative")
            need(maxheap>0 and 0<=freeheap<=maxheap,"invalid JVM heap values")
            need(max(se,pe,diff)<=EPSILON,"numerical error exceeds 1e-12")
            for key in ("cpu","java_version","operating_system","notes"): need(bool(r[key].strip()),f"{key} is empty")
            close(speed,sm/pm,"speedup"); close(st,n/(sm/1000),"sequential throughput"); close(pt,n/(pm/1000),"parallel throughput")
            if expected:
                for key,val in expected.items(): need(int(r[key])==val,f"{key} expected {val}, got {r[key]}")
            checked.append({"row":ix,"run_id":r["run_id"],"dimension":n,"nnz":nnz,"speedup":speed,"sequential_mean_ms":sm,"parallel_mean_ms":pm,"max_error":max(se,pe,diff)})
        except (ValidationError,ValueError) as e: raise ValidationError(f"row {ix}: {e}") from e
    return {"schema":"qflpn-benchmark-v2","validation":"PASS","records":len(checked),"all_records_valid":True,"latest_record":checked[-1]}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--csv",type=Path,default=Path("benchmarks/benchmark_results_v2.csv")); ap.add_argument("--report-json",type=Path); ap.add_argument("--expected-n",type=int); ap.add_argument("--warmup",type=int); ap.add_argument("--iterations",type=int); ap.add_argument("--threshold",type=int); ap.add_argument("--parallelism",type=int); a=ap.parse_args()
    expected={k:v for k,v in {"dimension":a.expected_n,"warmup_iterations":a.warmup,"measured_iterations":a.iterations,"threshold":a.threshold,"parallelism":a.parallelism}.items() if v is not None}
    try:
        result=validate(a.csv,expected); out=json.dumps(result,indent=2,allow_nan=False)
        if a.report_json: a.report_json.parent.mkdir(parents=True,exist_ok=True); a.report_json.write_text(out+"\n",encoding="utf-8")
        print(out); return 0
    except (ValidationError,OSError) as e: print(json.dumps({"validation":"FAIL","error":str(e)},indent=2),file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
