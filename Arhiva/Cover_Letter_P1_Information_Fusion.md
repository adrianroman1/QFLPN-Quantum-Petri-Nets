# Cover Letter — Information Fusion (Elsevier, Q1)
## Manuscript P1: Formal Operator Semantics for Quantum-Fuzzy Logical Petri Nets

**To:** Prof. Francisco Herrera, Editor-in-Chief  
*Information Fusion*, Elsevier  
**Date:** 10 November 2026  
**Corresponding Author:** Adrian Roman (`adrianroman304@gmail.com` / `adrian.roman@campus.utcluj.ro`)  
**Affiliation:** Faculty of Automation and Computer Science, Technical University of Cluj-Napoca (UTCN), Memorandumului 28, 400114 Cluj-Napoca, Romania  

---

Dear Editor-in-Chief and Editorial Board of *Information Fusion*,

We are pleased to submit our original research manuscript entitled:  
**"Formal Operator Semantics for Quantum-Fuzzy Logical Petri Nets"**  
for consideration as a regular paper in *Information Fusion*.

In strict compliance with the **Guide for Authors of Information Fusion**, we provide below the direct, detailed responses to the **Seven Mandatory Editorial Desk Screening Questions**:

### 1. State of the art with 5 recent references
The formal integration of multi-source information fusion, Petri net discrete-event concurrency, fuzzy activation logic, and quantum state dynamics has evolved rapidly. Five representative landmark and recent works defining the state of the art are:
1. Deng, Y. et al., "Quantum Evidence Theory and Information Fusion," *Information Fusion*, vol. 92, pp. 102–118, 2023 (Pioneering quantum mass functions and Dempster-Shafer combinations).
2. Vallero, M., Rech, P., and Vella, F., "State of Practice: Evaluating GPU Performance of State Vector and Tensor Network Methods," *Future Generation Computer Systems*, vol. 174, art. 107927, 2026.
3. Pastor, A. M., Badia, J. M., and Castillo, M., "A community detection-based parallel algorithm for quantum circuit simulation using tensor networks," *The Journal of Supercomputing*, vol. 81, art. 450, 2025.
4. Letia, T. S., Durla-Pasca, E. M., Al-Janabi, D., and Cuibus, O. P., "Development of Evolutionary Systems Based on Quantum Petri Nets," *Mathematics*, vol. 10, no. 23, art. 4404, 2022.
5. Williams, S., Waterman, A., and Patterson, D., "Roofline: An insightful visual performance model for multicore architectures," *Communications of the ACM*, vol. 52, no. 4, pp. 65–76, 2009.

### 2. Benchmark datasets / instances used
The study develops and tests:
- A deterministic 4-qubit reference system cross-validated on Qiskit Aer and PennyLane.
- Completely positive trace-preserving (CPTP) open-system quantum channels: Amplitude Damping $\Phi_\gamma$ and Phase Damping $\Phi_p$.
- Concrete benchmark cases with overlapping and non-overlapping subsystem supports testing non-commutative concurrency.

### 3. Validation measures
Validation is established through:
- Exact trace conservation ($\mathrm{Tr}(\rho) = 1.000000000000000 \pm 10^{-16}$) across all CPTP evolution steps.
- Commutator Frobenius norm $\|[U_a, U_b]\|_F = 2.366$ and trace distance $\Delta\rho = \frac{1}{2}\mathrm{Tr}|U_b U_a \rho_0 U_a^\dagger U_b^\dagger - U_a U_b \rho_0 U_b^\dagger U_a^\dagger| > 0$.
- Analytical Holevo information capacity bound: $\chi(\gamma) = h((1-\gamma)/2) - \frac{1}{2}h(1-\gamma)$ in bits.
- Closed-form phase damping semigroup composition: $\Phi_{p_2} \circ \Phi_{p_1} = \Phi_{p_1 + p_2 - 2p_1p_2}$.

### 4. Principal original claim
The principal original contribution is the **first typed, layered operator semantics** that rigorously connects discrete Petri net marking evolution, continuous fuzzy t-norm activation degrees, and density matrix quantum mechanics without semantic conflation. We prove that structural Petri net concurrency ($\bullet t_a \cap \bullet t_b = \emptyset$) does *not* imply quantum state permutability unless the underlying unitary commutators vanish on shared subsystem supports.

### 5. Concrete evidence provided
- Analytical proofs for Definition 1 (six stages of step execution), Proposition W (well-definedness), Corollary B (channel composition), and Proposition C (controlled-$X$ focal set permutations).
- Reproducible simulation scripts in Python and Qiskit with 0 discrepancies against independent numerical baselines.
- Openly archived code with persistent identifier DOI: `10.5281/zenodo.10823479`.

### 6. Closely related prior works
Prior models by Letia et al. (UTCN) and classical fuzzy Petri nets established algebraic transitions but lacked Kraus-operator open-system dynamics, typed semantic separation, and Holevo information bounds. The quantum evidence frameworks of Deng et al. operated at mass function levels without event-driven discrete transition firings.

### 7. Prior publications declaration
The authors confirm that this manuscript represents original research, has not been published previously in whole or in part, and is not currently under consideration for publication elsewhere.

---

Sincerely,  
**Adrian Roman**, MSc / PhD Candidate  
Faculty of Automation and Computer Science  
Technical University of Cluj-Napoca (UTCN), Romania  
Email: `adrianroman304@gmail.com` / `adrian.roman@campus.utcluj.ro`
