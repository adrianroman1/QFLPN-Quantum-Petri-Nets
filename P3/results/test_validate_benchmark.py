from __future__ import annotations
import csv, importlib.util
from pathlib import Path
import pytest

P=Path(__file__).with_name("validate_benchmark.py")
S=importlib.util.spec_from_file_location("validator_v2",P); V=importlib.util.module_from_spec(S); S.loader.exec_module(V)

def row():
    return dict(timestamp="2026-10-22T10:00:00Z",run_id="ci-123",benchmark_id="QFLPN-100",dimension="100",non_zero_count="200",parallelism="2",threshold="4096",warmup_iterations="5",measured_iterations="10",sequential_mean_ms="20",sequential_median_ms="19",sequential_stddev_ms="2",parallel_mean_ms="10",parallel_median_ms="9",parallel_stddev_ms="1",speedup="2",sequential_throughput_states_per_s="5000",parallel_throughput_states_per_s="10000",sequential_expected_error="0",parallel_expected_error="0",max_absolute_error="0",setup_time_ms="1",cpu="test-cpu",max_jvm_memory_bytes="4000000000",free_jvm_heap_bytes="500000000",java_version="21",operating_system="Linux",notes="test")
def save(p, rows):
    with p.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=V.HEADER); w.writeheader(); w.writerows(rows)
def test_accepts_valid_v2_row(tmp_path):
    p=tmp_path/"v2.csv"; save(p,[row()]); out=V.validate(p); assert out["validation"]=="PASS" and out["records"]==1
@pytest.mark.parametrize(("field","value"),[("speedup","3"),("sequential_expected_error","1e-5"),("parallel_stddev_ms","nan"),("run_id","")])
def test_rejects_corrupt_data(tmp_path,field,value):
    p=tmp_path/"bad.csv"; r=row(); r[field]=value; save(p,[r])
    with pytest.raises(V.ValidationError): V.validate(p)
def test_refuses_legacy_schema(tmp_path):
    p=tmp_path/"legacy.csv"; p.write_text("timestamp,dimension\nnow,1\n",encoding="utf-8")
    with pytest.raises(V.ValidationError,match="header mismatch"): V.validate(p)
