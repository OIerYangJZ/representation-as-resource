# Ablation Study (10,000 gates)

## qft_inverse

| Ablation | Output Gates | Output Depth | 2Q Gates | Runtime |
|---|---:|---:|---:|---:|
| full | 0 | 0 | 0 | 5.892 s |
| candidate_selection_only | 0 | 0 | 0 | 5.866 s |
| commutative_only | 0 | 0 | 0 | 6.098 s |
| no_prefix | 0 | 0 | 0 | 6.043 s |
| no_run | 0 | 0 | 0 | 6.04 s |
| no_adjacent_inverse | 0 | 0 | 0 | 8.712 s |
| no_candidate_selection | 0 | 0 | 0 | 6.254 s |

## qft_control

| Ablation | Output Gates | Output Depth | 2Q Gates | Runtime |
|---|---:|---:|---:|---:|
| full | 34,750 | 12,500 | 17,000 | 0.181 s |
| candidate_selection_only | 34,750 | 12,500 | 17,000 | 0.184 s |
| commutative_only | 34,750 | 12,500 | 17,000 | 0.19 s |
| no_prefix | 34,750 | 12,500 | 17,000 | 0.173 s |
| no_run | 34,750 | 12,500 | 17,000 | 0.184 s |
| no_adjacent_inverse | 34,750 | 12,500 | 17,000 | 0.181 s |
| no_candidate_selection | 34,750 | 12,500 | 17,000 | 0.197 s |

## qpe_style

| Ablation | Output Gates | Output Depth | 2Q Gates | Runtime |
|---|---:|---:|---:|---:|
| full | 21,206 | 14,002 | 6,002 | 2.632 s |
| candidate_selection_only | 21,206 | 14,002 | 6,002 | 2.529 s |
| commutative_only | 21,206 | 14,002 | 6,002 | 2.527 s |
| no_prefix | 21,206 | 14,002 | 6,002 | 2.616 s |
| no_run | 21,206 | 14,002 | 6,002 | 2.403 s |
| no_adjacent_inverse | 21,206 | 14,002 | 6,002 | 2.473 s |
| no_candidate_selection | 21,206 | 14,002 | 6,002 | 2.47 s |

## qaoa_ring

| Ablation | Output Gates | Output Depth | 2Q Gates | Runtime |
|---|---:|---:|---:|---:|
| full | 10,000 | 6,200 | 4,000 | 0.016 s |
| candidate_selection_only | 10,000 | 6,200 | 4,000 | 0.023 s |
| commutative_only | 10,000 | 6,200 | 4,000 | 0.016 s |
| no_prefix | 10,000 | 6,200 | 4,000 | 0.016 s |
| no_run | 10,000 | 6,200 | 4,000 | 0.016 s |
| no_adjacent_inverse | 10,000 | 6,200 | 4,000 | 0.024 s |
| no_candidate_selection | 10,000 | 6,200 | 4,000 | 0.016 s |

## grover_mirrored

| Ablation | Output Gates | Output Depth | 2Q Gates | Runtime |
|---|---:|---:|---:|---:|
| full | 115,811 | 76,210 | 46,800 | 0.872 s |
| candidate_selection_only | 115,811 | 76,210 | 46,800 | 0.897 s |
| commutative_only | 115,811 | 76,210 | 46,800 | 0.915 s |
| no_prefix | 115,811 | 76,210 | 46,800 | 0.915 s |
| no_run | 115,811 | 76,210 | 46,800 | 0.928 s |
| no_adjacent_inverse | 115,811 | 76,210 | 46,800 | 0.913 s |
| no_candidate_selection | 115,811 | 76,210 | 46,800 | 0.9 s |
