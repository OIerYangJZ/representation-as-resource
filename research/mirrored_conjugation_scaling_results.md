# Mirrored / Conjugation Scaling Positive Cases

Target basis: `['cx', 'rx', 'ry', 'rz', 'h']`

## mqt_grover

| Size | Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---:|---|---|---:|---:|---:|---:|
| 8 | qiskit_opt3 | ok | 5,170 | 3,788 | 2,192 | 0.062 s |
| 8 | baseline_ucc | ok | 18,992 | 10,990 | 2,192 | 0.149 s |
| 8 | optimized_ucc | ok | 5,170 | 3,788 | 2,192 | 0.07 s |
| 12 | qiskit_opt3 | ok | 71,706 | 55,801 | 29,190 | 0.579 s |
| 12 | baseline_ucc | ok | 259,797 | 150,911 | 29,190 | 1.791 s |
| 12 | optimized_ucc | ok | 71,706 | 55,801 | 29,190 | 0.754 s |
| 16 | qiskit_opt3 | ok | 581,098 | 476,428 | 234,300 | 5.741 s |
| 16 | baseline_ucc | ok | 2,112,285 | 1,255,608 | 234,300 | 14.004 s |
| 16 | optimized_ucc | ok | 581,098 | 476,428 | 234,300 | 4.722 s |

## grover_mirrored

| Size | Method | Status | Output Gates | Output Depth | CX Count | Runtime |
|---:|---|---|---:|---:|---:|---:|
| 10,000 | qiskit_opt3 | ok | 115,811 | 76,210 | 46,800 | 0.868 s |
| 10,000 | baseline_ucc | ok | 412,206 | 216,621 | 46,800 | 2.693 s |
| 10,000 | optimized_ucc | ok | 115,811 | 76,210 | 46,800 | 0.917 s |
| 20,000 | qiskit_opt3 | ok | 231,611 | 152,410 | 93,600 | 1.818 s |
| 20,000 | baseline_ucc | ok | 824,406 | 433,221 | 93,600 | 5.334 s |
| 20,000 | optimized_ucc | ok | 231,611 | 152,410 | 93,600 | 1.829 s |
| 50,000 | qiskit_opt3 | ok | 579,011 | 381,010 | 234,000 | 4.602 s |
| 50,000 | baseline_ucc | ok | 2,061,006 | 1,083,021 | 234,000 | 13.307 s |
| 50,000 | optimized_ucc | ok | 579,011 | 381,010 | 234,000 | 6.171 s |
| 100,000 | qiskit_opt3 | ok | 1,158,011 | 762,010 | 468,000 | 9.648 s |
| 100,000 | baseline_ucc | ok | 4,122,006 | 2,166,021 | 468,000 | 27.802 s |
| 100,000 | optimized_ucc | ok | 1,158,011 | 762,010 | 468,000 | 12.695 s |
