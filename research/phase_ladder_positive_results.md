# Public Benchmark Suite Baselines (MQT Bench)

Target basis: `['cx', 'rx', 'ry', 'rz', 'h']`

## mqt_qpeinexact_24

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| baseline_ucc | ok | 3,682 | 606 | 513 | 0.023 s |
| optimized_ucc | ok | 1,206 | 228 | 573 | 0.012 s |
| qiskit_opt3 | ok | 1,206 | 228 | 573 | 0.012 s |

## mqt_ae_8

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| baseline_ucc | ok | 542 | 191 | 74 | 0.013 s |
| optimized_ucc | ok | 207 | 100 | 74 | 0.014 s |
| qiskit_opt3 | ok | 207 | 100 | 74 | 0.012 s |

## mqt_draper_qft_adder_32

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| baseline_ucc | ok | 5,278 | 662 | 730 | 0.034 s |
| optimized_ucc | ok | 1,630 | 275 | 736 | 0.021 s |
| qiskit_opt3 | ok | 1,630 | 275 | 736 | 0.026 s |
