# Mirrored / Conjugation Scaling Positive Cases Summary

This scaling set supports the second theory line with two positive families:

- public `mqt_grover` amplitude-amplification/conjugation scaling
- synthetic repeated `grover_mirrored` shell scaling

## `mqt_grover`

### size `8`
- baseline UCC: `18,992` gates, depth `10,990`, `cx=2,192`
- optimized UCC: `5,170` gates, depth `3,788`, `cx=2,192`
- qiskit opt3: `5,170` gates, depth `3,788`, `cx=2,192`
- conclusion: exact `qiskit opt3` parity while improving over baseline UCC.

### size `12`
- baseline UCC: `259,797` gates, depth `150,911`, `cx=29,190`
- optimized UCC: `71,706` gates, depth `55,801`, `cx=29,190`
- qiskit opt3: `71,706` gates, depth `55,801`, `cx=29,190`
- conclusion: exact `qiskit opt3` parity while improving over baseline UCC.

### size `16`
- baseline UCC: `2,112,285` gates, depth `1,255,608`, `cx=234,300`
- optimized UCC: `581,098` gates, depth `476,428`, `cx=234,300`
- qiskit opt3: `581,098` gates, depth `476,428`, `cx=234,300`
- conclusion: exact `qiskit opt3` parity while improving over baseline UCC.

## `grover_mirrored`

### size `10,000`
- baseline UCC: `412,206` gates, depth `216,621`, `cx=46,800`
- optimized UCC: `115,811` gates, depth `76,210`, `cx=46,800`
- qiskit opt3: `115,811` gates, depth `76,210`, `cx=46,800`
- conclusion: exact `qiskit opt3` parity while improving over baseline UCC.

### size `20,000`
- baseline UCC: `824,406` gates, depth `433,221`, `cx=93,600`
- optimized UCC: `231,611` gates, depth `152,410`, `cx=93,600`
- qiskit opt3: `231,611` gates, depth `152,410`, `cx=93,600`
- conclusion: exact `qiskit opt3` parity while improving over baseline UCC.

### size `50,000`
- baseline UCC: `2,061,006` gates, depth `1,083,021`, `cx=234,000`
- optimized UCC: `579,011` gates, depth `381,010`, `cx=234,000`
- qiskit opt3: `579,011` gates, depth `381,010`, `cx=234,000`
- conclusion: exact `qiskit opt3` parity while improving over baseline UCC.

### size `100,000`
- baseline UCC: `4,122,006` gates, depth `2,166,021`, `cx=468,000`
- optimized UCC: `1,158,011` gates, depth `762,010`, `cx=468,000`
- qiskit opt3: `1,158,011` gates, depth `762,010`, `cx=468,000`
- conclusion: exact `qiskit opt3` parity while improving over baseline UCC.

## Interpretation

- The MQT Grover scaling points show that the mirrored/conjugation line is not a single-size artifact.
- The fixed-basis `grover_mirrored` scaling points show the same recoverability pattern under increasing repeated-shell materialization.
- Across these scaling points, optimized UCC is expected to track `qiskit opt3` quality while baseline UCC exhibits large structural overhead.
