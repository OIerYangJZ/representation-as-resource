# Event-level masked-share cut trace

`scripts/trace_cut_budget.py` executes the two-round masked-share reference
compiler, five memory-capped hybrids, and the direct semantic-stream compiler
at `m = 8, 16, 32, 64`.  Every input update is an event cut.  At each nonfinal
cut the explicit live compiler-state object is serialized and deleted;
resumption receives only a byte-for-byte copy of the committed output prefix,
the five self-delimiting byte fields (control, store, window, parameter, and
IR), and the unread input suffix.  A reported event is accepted only if this
restart reconstructs the final aggregate exactly.

Outputs:

- `cut_trace_events.jsonl`: all 1,320 event records, including pass index,
  fieldwise byte counts, RSS, and elapsed nanoseconds;
- `cut_trace_summary.csv`: the 24 measured cut points;
- `commitment_vs_cross_cut.pdf`: the paper-facing measured curve;
- `cut_trace_report.json`: schema, restart assertion, and file hashes.

Reproduce with `../../.venv/bin/python scripts/trace_cut_budget.py
--output-dir research/cut_trace` from the repaired-manuscript root.
