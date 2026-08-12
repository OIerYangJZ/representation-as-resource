# Clean-room reproduction report

## Result

PASS.  A minimal artifact was copied to an independent temporary directory, a fresh virtual
environment was created without network access and explicitly bound to the locked project
site-packages at `/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)/.venv/lib/python3.13/site-packages`, and all requested
subsets were executed from that directory.

- Headline-theorem exhaustive subset: 9 tests passed across
  `test_qary_packing.py`, `test_update_stream_equivalence.py`, and
  `search_small_compiler_counterexamples.py`.
- Natural benchmark subset: `qaoa_ising` was independently compiled by the
  authors reference and TKET semantic baseline; both dense projective certificates returned
  `completed_valid`.
- Fixed-total-error QRE subset: both outputs used epsilon_total=1e-6 and 16 factories and returned
  positive physical-qubit, cycle, runtime, and spacetime estimates.
- Deterministic grid-synthesis pairs exercised: 17.

The machine-readable receipt is `data/frozen/clean_room_receipt.json`; the command log is
`reproducibility/clean_room.log` (SHA-256 `aaadc9262d987df2b1ad552111d8898aac293a673d39b8f32629d9d59b9e86eb`).  The temporary directory was
`/var/folders/tg/nbn_fl894vb3j41w5zvzfl1c0000gn/T/ucc-clean-room-kodr6yja` and was removed after verification.

This validates a theorem-test subset, a benchmark subset, and a QRE subset.  It does not rerun the
full 21,060-cell W8 campaign or all 288 W7 cells inside the temporary directory.
