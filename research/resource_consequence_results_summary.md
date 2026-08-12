# Resource Consequence Results Summary

Experiment: `fourier_phase_sandwich = H D^r H`.

Main comparison:

- `semantic_first`: aggregate the Fourier-layer term before materialization.
- `materialize_first_qiskit_opt3`: materialize/lower first, then use `qiskit opt3`.
- `materialize_first_baseline_ucc`: disable Fourier-layer IR and compile through the materialized path.

Headline result:

| Requested Gates | semantic_first | materialize_first_qiskit_opt3 | materialize_first_baseline_ucc |
|---:|---:|---:|---:|
| `4,000` | `42 / 12 / 22 / 2,200` | `9,588 / 4,788 / 4,793 / 479,300` | `9,588 / 4,788 / 4,793 / 479,300` |
| `10,000` | `42 / 12 / 22 / 2,200` | `23,988 / 11,988 / 11,993 / 1,199,300` | timeout `>120s` |
| `20,000` | `42 / 12 / 22 / 2,200` | `47,988 / 23,988 / 23,993 / 2,399,300` | timeout `>600s` |
| `50,000` | `42 / 12 / 22 / 2,200` | timeout `>600s` | timeout `>600s` |
| `100,000` | `42 / 12 / 22 / 2,200` | timeout `>600s` | timeout `>600s` |

Each non-timeout cell reports:

- gates / `cx` / rotations / `T_proxy(1e-10)`.

The synthesis proxy is:

- `T_epsilon(R) = ceil(3 log2(1/epsilon)) R`,

where `R` is the arbitrary `rx`/`ry`/`rz` rotation count.

Interpretation:

- semantic-first compilation keeps gates, `cx`, rotations, and T-proxy constant across all tested sizes;
- materialize-first compilation grows linearly on smaller sizes and times out at larger sizes;
- this supports the FTQC/resource-estimation consequence of the recoverability gap;
- this is a precision-based resource proxy, not an exact optimal Clifford+T synthesis result.
