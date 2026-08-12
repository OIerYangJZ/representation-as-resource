# Round 3 Run Log

Protocol repair implementation was added under
`research/round3_protocol_repair/`. Old frozen experiment JSON/MD files were
not overwritten.

## Completed In This Session

- Implemented `run_round3_protocol_repair.py`.
- Implemented `validate_round3_outputs.py`.
- Generated `method_name_map.md`.
- Generated `baseline_call_sequences.md`.
- Ran smoke mode successfully.
- Validated smoke JSON schemas successfully.

## Smoke Command

```bash
./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --smoke
```

Smoke result files use the `smoke_` prefix and are not manuscript-facing full
experimental results.

## Full Commands

Default full repair run:

```bash
./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --full --timeout-s 600
```

Allowed shorter disclosed budget:

```bash
./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --full --timeout-s 300
```

Validate generated JSON:

```bash
./.venv/bin/python research/round3_protocol_repair/validate_round3_outputs.py
```

