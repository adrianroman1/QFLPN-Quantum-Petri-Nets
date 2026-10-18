"""Generate reproducibility evidence for P1. Run from repository root."""
from __future__ import annotations
import csv, hashlib, json, platform, sys
from pathlib import Path
import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "P1"
OUT = P1 / "reports"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
from P1.code.qflpn_reference import fuzzy_to_angle, reference_state, density_matrix, positive_semidefinite_residual
from P1.code.qflpn_transition_operator import ry, c3x, qflpn_transition_operator, validate_unitarity
from P1.tests.independent_reference import independent_global_operator, independent_density_evolution


def dump(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    dump("environment_report.json", {"python": platform.python_version(), "platform": platform.platform(),
        "numpy": np.__version__, "scipy": scipy.__version__, "status": "OBSERVED_AT_GENERATION"})
    dump("reference_specification_report.json", {"qubits": 4, "dimension": 16,
        "basis_order": "lexicographic computational basis |0000> ... |1111>",
        "dtype": "complex128", "status": "DECLARED_SPECIFICATION"})
    with (OUT / "activation_mapping_results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["mu", "theta_rad", "sin2_theta_over_2", "absolute_error"])
        for mu in [0, .25, .5, .75, 1]:
            theta = fuzzy_to_angle(mu); actual = float(np.sin(theta / 2) ** 2)
            w.writerow([mu, theta, actual, abs(actual-mu)])
    angles = [-2.3, -.1, 0, .7, np.pi]
    ry_errors = [float(np.linalg.norm(ry(t)-np.array([[np.cos(t/2),-np.sin(t/2)],[np.sin(t/2),np.cos(t/2)]]))) for t in angles]
    dump("ry_validation_report.json", {"angles": angles, "frobenius_errors": ry_errors, "max_error": max(ry_errors)})
    state = reference_state([.2, .4, .6, .8])
    dump("state_preparation_report.json", {"dimension": int(state.size), "norm": float(np.linalg.norm(state)),
        "normalization_error": abs(float(np.linalg.norm(state))-1.0)})
    probs = np.abs(state)**2
    with (OUT / "probability_validation.csv").open("w", newline="", encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["basis_index", "basis_label", "probability"])
        for i,p in enumerate(probs): w.writerow([i, format(i,"04b"), float(p)])
    gate = c3x()
    with (OUT / "c3x_truth_table.csv").open("w", newline="", encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["input_basis", "output_basis", "expected_output", "correct"])
        for i in range(16):
            out=int(np.argmax(np.abs(gate[:,i]))); expected=i^1 if (i&14)==14 else i
            w.writerow([format(i,"04b"),format(out,"04b"),format(expected,"04b"),out==expected])
    operator=qflpn_transition_operator()
    dump("global_operator_report.json", {"shape": list(operator.shape), "unitarity_residual": validate_unitarity(operator)})
    rho=density_matrix(state)
    dump("density_validation_report.json", {"trace_real": float(np.trace(rho).real), "trace_imag": float(np.trace(rho).imag),
        "hermiticity_residual": float(np.linalg.norm(rho-rho.conj().T)), "psd_residual": positive_semidefinite_residual(rho)})
    evolved=operator@rho@operator.conj().T
    dump("unitary_evolution_report.json", {"trace_real": float(np.trace(evolved).real), "trace_imag": float(np.trace(evolved).imag),
        "hermiticity_residual": float(np.linalg.norm(evolved-evolved.conj().T)), "psd_residual": positive_semidefinite_residual(evolved)})
    u1=np.kron(ry(.2),np.eye(2)); u2=np.kron(np.eye(2),ry(-.4)); u3=np.kron(np.array([[0,1],[1,0]],complex),np.eye(2))
    composed=u3@u2@u1
    dump("sequential_composition_report.json", {"order": "U3 @ U2 @ U1", "shape": list(composed.shape),
        "unitarity_residual": validate_unitarity(composed)})
    dump("execution_contract_report.json", {"sequence": ["membership validation", "theta encoding", "RY/local operator", "C3X", "density evolution", "probability observation"],
        "status": "NUMERICAL_DEMONSTRATOR_CONTRACT_ONLY", "full_Petri_net_semantics_proven": False})
    bad_values=[]
    for bad in [float("nan"),float("inf"),-float("inf")]:
        for label,fn,arg in [("PSD",positive_semidefinite_residual,np.array([[bad,0],[0,1]],complex)),
                             ("unitarity",validate_unitarity,np.array([[bad,0],[0,1]],complex))]:
            try: fn(arg); rejected=False
            except ValueError: rejected=True
            bad_values.append({"check":label,"input":str(bad),"rejected":rejected})
    dump("robustness_report.json", {"nonfinite_cases": bad_values, "all_rejected": all(x["rejected"] for x in bad_values)})
    independent=independent_global_operator([.85,.90,.45,.70])
    production=qflpn_transition_operator([.85,.90,.45,.70])
    independent_rho=independent_density_evolution(independent,state)
    production_rho=production@rho@production.conj().T
    dump("independent_validation_report.json", {"operator_frobenius_difference": float(np.linalg.norm(independent-production)),
        "evolved_density_frobenius_difference": float(np.linalg.norm(independent_rho-production_rho)),
        "independent_code_imports_production": False})
    # Manifest and hashes cover source, tests, workflow, and reports, excluding self-referential files.
    tracked=[]
    for base in [P1, ROOT/".github"/"workflows"]:
        for path in base.rglob("*"):
            if path.is_file() and path.name not in {"MANIFEST.txt","SHA256SUMS.txt"} and "__pycache__" not in path.parts:
                tracked.append(path)
    rels=sorted(str(p.relative_to(ROOT)) for p in tracked)
    (P1/"MANIFEST.txt").write_text("\n".join(rels)+"\n",encoding="utf-8")
    lines=[]
    for rel in rels:
        digest=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest(); lines.append(f"{digest}  {rel}")
    (P1/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
    dump("artifact_validation_report.json", {"manifest_entries":len(rels),"sha256_entries":len(lines),
        "status":"GENERATED; VERIFY_AFTER_FINAL_COMMIT", "pdf_tex_alignment_checked":False})

if __name__ == "__main__":
    main()
