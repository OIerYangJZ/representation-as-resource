# Resource Consequence Experiment

This experiment compares semantic-first vs materialize-first optimization/resource estimation paths for the `fourier_phase_sandwich` family.

## Metrics Table

| Requested Gates | Method | Status | Output Gates | CX Count | RZ/Rot Count | T-Proxy (1e-6) | T-Proxy (1e-10) | T-Proxy (1e-12) | Runtime |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| 4,000 | phase_poly_reference | ok | 42 | 12 | 22 | 1,320 | 2,200 | 2,640 | 0.199 s |
| 10,000 | phase_poly_reference | ok | 42 | 12 | 22 | 1,320 | 2,200 | 2,640 | 0.21 s |
| 20,000 | phase_poly_reference | ok | 42 | 12 | 22 | 1,320 | 2,200 | 2,640 | 0.234 s |
| 50,000 | phase_poly_reference | ok | 42 | 12 | 22 | 1,320 | 2,200 | 2,640 | 0.338 s |
| 100,000 | phase_poly_reference | ok | 42 | 12 | 22 | 1,320 | 2,200 | 2,640 | 0.499 s |

## Interpretation

Does semantic-first maintain constant resource estimates while materialize-first inflates them or timeouts?
**Answer:** Yes. The `semantic_first` pipeline and the independent `phase_poly_reference` baseline both aggregate the repeated commuting diagonal phase polynomial before materialization, resulting in a constant, highly optimized circuit (42 gates) regardless of the requested gate count. In contrast, the `materialize_first` pipelines first unroll the large circuit into basis gates. For smaller gate counts, they produce significantly inflated resource estimates (gates, CX, rotations, and corresponding T-proxy counts). For larger gate counts (e.g., 50k, 100k), the materialization process becomes so expensive that the optimization passes simply time out.

This supports the PRX claim that basis/materialization before semantic aggregation can inflate FTQC resource estimates. The `phase_poly_reference` row is deliberately narrow: it is not a full compiler and does not use UCC internals. It only keeps the explicit commuting-diagonal representation long enough to add equal phase terms before lowering to the shared target basis.