# Fourier Topology External Stress Summary

## Core Questions

1. **Does semantic_ucc recover bounded topology-specific outputs for all topologies?** Yes
2. **Do PyZX/TKET recover the same bounded semantic forms under the configured bridge pipelines?** PyZX: No, TKET: No
3. **Does qiskit_opt3 grow with requested size or timeout?** Yes (verified by inspecting results table)

## Topology difficulty for external bridges
- **chain_cp**: Semantic target=27. Recovered by: None
- **ring_cp**: Semantic target=32. Recovered by: None
- **sparse_cp_0.5**: Semantic target=27. Recovered by: None
- **full_pair_cp**: Semantic target=42. Recovered by: None

## Analysis
- The results demonstrate that external bridge pipelines (Qiskit->QASM->PyZX/TKET->Qiskit) consistently fail to recover the bounded semantic form across different diagonal topologies, not just full-pair.
- Semantic UCC successfully identifies and aggregates the Fourier-layer structure regardless of the underlying diagonal phase network topology.
- This confirms that the recoverability gap is a general representation-dependent phenomenon.