# Revision audit for issues 1--15

This directory records the requirement-by-requirement audit requested on
2026-08-01.  `audit.json` is the machine-readable source.  A status of
`fixed_verified` means that the manuscript statement, executable artifact,
and frozen evidence required by that issue were inspected; it does not promote
configured-pipeline diagnostics to theorem evidence.

Key rerunnable checks from the repaired-manuscript root are:

```sh
../../.venv/bin/python research/rational_witness/verify_period.py \
  --check research/rational_witness/period_certificate.txt
../../.venv/bin/python scripts/verify_symbolic_certificate.py \
  --check research/symbolic_certificate/mutation_crosscheck.json
../../.venv/bin/python scripts/trace_cut_budget.py \
  --output-dir research/cut_trace
```

The fixed-total-error QRE is frozen under `research/fixed_budget_qre/`; its
manifest covers the runner, synthesis source and binary, CSV, JSON, and README.
The final PDF is additionally rebuilt and visually inspected as part of this
audit.
