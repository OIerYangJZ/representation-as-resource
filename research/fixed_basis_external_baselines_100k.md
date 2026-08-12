# Fixed-Basis External Baselines

Target basis: `['cx', 'rx', 'ry', 'rz', 'h']`

## qft_inverse

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| translation_only | ok | 400,000 | 142,500 | 170,000 | 0.336 s |
| qiskit_opt0 | ok | 400,000 | 142,500 | 170,000 | 0.265 s |
| qiskit_opt1 | ok | 365,002 | 130,002 | 140,000 | 0.711 s |
| qiskit_opt3 | timeout | - | - | - | > 120 s |
| qiskit_commutative_inverse | ok | 0 | 0 | 0 | 2.341 s |
| tket_full_peephole | unavailable | - | - | - | - |
| baseline_ucc | ok | 968,784 | 276,266 | 135,004 | 6.405 s |
| optimized_ucc | ok | 0 | 0 | 0 | 2.596 s |

## qft_control

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| translation_only | ok | 400,000 | 140,000 | 170,000 | 0.249 s |
| qiskit_opt0 | ok | 400,000 | 140,000 | 170,000 | 0.253 s |
| qiskit_opt1 | ok | 400,000 | 140,000 | 170,000 | 0.559 s |
| qiskit_opt3 | ok | 347,500 | 125,000 | 170,000 | 1.956 s |
| qiskit_commutative_inverse | ok | 400,000 | 140,000 | 170,000 | 2.296 s |
| tket_full_peephole | unavailable | - | - | - | - |
| baseline_ucc | ok | 1,207,504 | 317,501 | 170,000 | 7.315 s |
| optimized_ucc | ok | 347,500 | 125,000 | 170,000 | 4.637 s |

## qpe_style

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| translation_only | ok | 396,000 | 296,001 | 156,000 | 0.256 s |
| qiskit_opt0 | ok | 396,000 | 296,001 | 156,000 | 0.257 s |
| qiskit_opt1 | ok | 396,000 | 296,001 | 156,000 | 0.539 s |
| qiskit_opt3 | timeout | - | - | - | > 120 s |
| qiskit_commutative_inverse | ok | 396,000 | 296,001 | 156,000 | 1.948 s |
| tket_full_peephole | unavailable | - | - | - | - |
| baseline_ucc | ok | 456,013 | 236,011 | 60,002 | 3.271 s |
| optimized_ucc | ok | 164,400 | 110,001 | 60,200 | 5.285 s |

## qaoa_ring

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| translation_only | ok | 100,000 | 62,000 | 40,000 | 0.027 s |
| qiskit_opt0 | ok | 100,000 | 62,000 | 40,000 | 0.034 s |
| qiskit_opt1 | ok | 100,000 | 62,000 | 40,000 | 0.08 s |
| qiskit_opt3 | ok | 100,000 | 62,000 | 40,000 | 0.397 s |
| qiskit_commutative_inverse | ok | 100,000 | 62,000 | 40,000 | 0.531 s |
| tket_full_peephole | unavailable | - | - | - | - |
| baseline_ucc | ok | 300,055 | 163,055 | 40,000 | 1.612 s |
| optimized_ucc | ok | 100,000 | 62,000 | 40,000 | 0.116 s |

## grover_mirrored

| Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---|---|---:|---:|---:|---:|
| translation_only | ok | 1,370,000 | 840,009 | 492,000 | 2.538 s |
| qiskit_opt0 | ok | 1,370,000 | 840,009 | 492,000 | 2.616 s |
| qiskit_opt1 | ok | 1,184,009 | 772,009 | 468,000 | 4.517 s |
| qiskit_opt3 | ok | 1,158,011 | 762,010 | 468,000 | 10.67 s |
| qiskit_commutative_inverse | ok | 1,334,004 | 836,009 | 492,000 | 3.108 s |
| tket_full_peephole | unavailable | - | - | - | - |
| baseline_ucc | ok | 4,122,006 | 2,166,021 | 468,000 | 29.692 s |
| optimized_ucc | ok | 1,158,011 | 762,010 | 468,000 | 13.191 s |
