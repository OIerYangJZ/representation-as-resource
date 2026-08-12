# Symbolic certificate mutation and dense cross-check

`scripts/verify_symbolic_certificate.py` implements the exact canonical
`{cx, rz, barrier, id}` checker described in the manuscript.  Angles belong to
`Q*pi` plus a sparse rational module over declared formal symbols.  The checker
compares the final binary linear frame and every parity-support coefficient,
reducing only the rational-pi coefficient modulo 2.

The frozen report contains 20 cases: widths 2 through 5 crossed with an
equivalent split, angle mutation, support mutation, Clifford-frame mutation,
and unsupported-H case.  Supported cases are independently cross-checked with
dense matrices up to global phase.  Recheck with:

```sh
../../.venv/bin/python scripts/verify_symbolic_certificate.py \
  --check research/symbolic_certificate/mutation_crosscheck.json
```
