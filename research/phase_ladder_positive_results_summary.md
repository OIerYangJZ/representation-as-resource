# Phase-Ladder Positive Cases Summary

This note isolates three additional public-benchmark positive cases that are
particularly relevant to the current `phase-ladder / Fourier-layer` theory
line. They were compared under the same fixed-basis protocol against:

- baseline `UCC`
- optimized `UCC`
- `qiskit opt3`

Target basis:

- `["cx", "rx", "ry", "rz", "h"]`

## Instances

- `mqt_qpeinexact_24`
  - `MQT Bench` `qpeinexact` with `circuit_size=24`
- `mqt_ae_8`
  - `MQT Bench` `ae` with `circuit_size=8`
- `mqt_draper_qft_adder_32`
  - `MQT Bench` `draper_qft_adder` with `circuit_size=32`

## Results

### `mqt_qpeinexact_24`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| baseline UCC | `3,682` | `606` | `513` | `0.023 s` |
| optimized UCC | `1,206` | `228` | `573` | `0.012 s` |
| qiskit opt3 | `1,206` | `228` | `573` | `0.012 s` |

Observation:

- optimized UCC reduces total gates by about `67.2%` versus baseline UCC
- optimized UCC exactly matches `qiskit opt3` in total gates and depth

### `mqt_ae_8`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| baseline UCC | `542` | `191` | `74` | `0.013 s` |
| optimized UCC | `207` | `100` | `74` | `0.014 s` |
| qiskit opt3 | `207` | `100` | `74` | `0.012 s` |

Observation:

- optimized UCC reduces total gates by about `61.8%` versus baseline UCC
- optimized UCC again exactly matches `qiskit opt3`

### `mqt_draper_qft_adder_32`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| baseline UCC | `5,278` | `662` | `730` | `0.034 s` |
| optimized UCC | `1,630` | `275` | `736` | `0.021 s` |
| qiskit opt3 | `1,630` | `275` | `736` | `0.026 s` |

Observation:

- optimized UCC reduces total gates by about `69.1%` versus baseline UCC
- optimized UCC exactly matches `qiskit opt3` in total gates and depth

## Interpretation

These three cases are useful because they are not just more public benchmarks;
they are structurally aligned with the current `phase-ladder / Fourier-layer`
family theorem:

- `qpeinexact` extends the existing QPE-style line beyond the exact-phase case
- `ae` ties the same theory line to amplitude-estimation structure
- `draper_qft_adder` moves the theory into an arithmetic/QFT setting

The cleanest current claim is:

> on three additional phase-heavy public benchmarks, optimized UCC continues to
> match `qiskit opt3` output quality while substantially repairing baseline-UCC
> regressions.

This strengthens the representation-gap story by showing that the current
`Fourier-layer` line is not supported only by one synthetic `qpe_style` family
and one `qpeexact` benchmark, but also by `qpeinexact`, amplitude estimation,
and QFT-based arithmetic.
