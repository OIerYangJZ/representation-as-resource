# Immutable campaign hierarchy

`campaign_index.json` defines unique reader prefixes and single-parent base
profiles for RP23, HW24, REAL24, MR25, and NF25.  Each campaign manifest records
backend, gate set, seed, timeout policy, memory-cap policy, tool versions,
artifact/freeze provenance, bridge sequence, certificate policy, configuration
hash, and dataset hash.

Historical missing controls are explicit (`not_enforced_historical` or
diagnostic-only); they are never filled with a newer campaign's values.  The
hardware-aware and real-panel source JSON files are copied here canonically and
hashed so later runner changes cannot silently alter reader-facing rows.

