# Data audit report

## Result

The normalized provenance index contains **24,748** source rows and
**0** duplicate nine-field primary-key rows.  The index is
`data/frozen/unified_experiments.parquet` (SHA-256 `7defd561f20436eda1a022512c744bdc135b4eecb90c5d88d646cc2f770d526e`).
Status classes are preserved as `{"completed_valid": 24700, "predicate_error": 48}`;
non-completed rows are not coerced into numeric outcomes.

Registered-file omissions: 0.  Registered row-count
mismatches: 0.  Conflicting CSV/parquet cells:
0.  Duplicate labels among the active manuscript-directory
TeX sources: 0 across 187 labels.

## Numeric mirror checks

- `data/frozen/matched_representation.csv` vs `data/frozen/matched_representation.parquet`: 1080 rows, 0 conflicting cells.
- `data/frozen/external_baselines.csv` vs `data/frozen/external_baselines.parquet`: 1728 rows, 0 conflicting cells.
- `data/frozen/qre_results.csv` vs `data/frozen/qre_results.parquet`: 288 rows, 0 conflicting cells.
- `data/frozen/natural_workloads.csv` vs `data/frozen/natural_workloads.parquet`: 21060 rows, 0 conflicting cells.

## Receipt hash drift

- None.

Receipt drift is reported, never repaired in place.  A drifted file must be rerun and re-frozen or
explicitly classified as historical before it can support a manuscript number.

## Optional raw provenance archive

Not materialized. The optional archive is `ssh://git@github.com/OIerYangJZ/paper1-data.git` at revision `5f90733d7d83d2690f3e0ad5164824879ca95b84` and can be fetched with `./reproducibility/fetch_raw_data.sh`. Its absence does not affect the committed frozen-data rebuild.

## Unregistered frozen artifacts

- None.

These files are not silently treated as evidence.  They are auxiliary analysis outputs or old
receipts until registered in `data/manifest.yaml`.

## Historical/intermediate data retained

- `data/raw-archive/runs/w4-matched-representation-20260802` — historical_raw_provenance: Raw representations and logs are in the optional archive; the committed parquet freeze is canonical.
- `data/raw-archive/runs/w5-external-baselines-20260803` — historical_raw_provenance: Raw per-cell logs are in the optional archive; the committed parquet freeze is canonical.
- `data/raw-archive/runs/w8-natural-20260803-local/natural_baselines.parquet` — intermediate_noncanonical: The final factorial parquet includes the matched external rows.

The full raw run tree is retained in the separately versioned archive.  The manifest identifies
which immutable in-repository table is canonical so that duplicate filenames in raw, CSV, and
parquet forms cannot be mixed during analysis.

## Reproduction

```bash
.venv/bin/python scripts/audit_results.py
.venv/bin/python -m pytest tests/test_paper_number_provenance.py -q
```
