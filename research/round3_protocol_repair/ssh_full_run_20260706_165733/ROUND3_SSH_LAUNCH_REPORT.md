# Round 3 SSH Launch Report

Status: `FULL_RUN_LAUNCHED_BACKGROUND`

Generated: `2026-07-06T04:46:23+00:00` UTC

## Roots And Upload

- Local project root: `/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)`
- Remote project root: `/home/lyy/ucc_paper_round3`
- Upload strategy: compact dependency-closure upload with `rsync -azR`, no `--delete`.
- Upload selection report: `research/round3_protocol_repair/FILES_SELECTED_FOR_SSH_UPLOAD.md`
- Required remote entry points verified before setup:
  - `research/round3_protocol_repair/run_round3_protocol_repair.py`
  - `research/round3_protocol_repair/validate_round3_outputs.py`

## Environment Setup Summary

- Environment report: `research/round3_protocol_repair/ssh_environment_setup.md`
- Project-local virtual environment: `.venv/`
- Python executable: `./.venv/bin/python`
- Server system Python is `3.10.12`; project metadata declares `>=3.12,<3.14`.
- `uv` was installed, but managed Python 3.12 download stalled; fallback used user-level `virtualenv` with Python 3.10.
- `quimb==1.12.1` was not installed because it requires Python >=3.11 and is not used by the Round 3 runner/default UCC path.
- `pytket-qiskit`: available (`pytket.extensions.qiskit` imports).
- TKET passes: `FullPeepholeOptimise=yes`, `PauliSimp=yes`, `GuidedPauliSimp=yes`.

## Smoke Result

- Smoke command:

```bash
./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --smoke --timeout-s 30 2>&1 | tee research/round3_protocol_repair/logs/ssh_smoke.log
```

- Smoke status: passed, exit code 0.
- Smoke validator status: passed, exit code 0.
- Smoke validator log: `research/round3_protocol_repair/logs/ssh_validate_after_smoke.log`

## Full Run Launch

- Background method: `tmux`
- Session name: `round3_repair`
- Pane PID: `3633513`
- Exact full-run command launched inside tmux:

```bash
./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --full --timeout-s 600
```

- Full-run log path: `research/round3_protocol_repair/logs/ssh_full_600s.log`
- Exact validator command queued after full run inside tmux:

```bash
./.venv/bin/python research/round3_protocol_repair/validate_round3_outputs.py
```

- Full validator log path: `research/round3_protocol_repair/logs/ssh_validate_after_full.log`
- Exit status file written after session command finishes: `research/round3_protocol_repair/logs/ssh_full_exit_status.txt`

## Monitor Commands

```bash
ssh school-server
cd /home/lyy/ucc_paper_round3
tmux attach -t round3_repair
tail -f research/round3_protocol_repair/logs/ssh_full_600s.log
tail -f research/round3_protocol_repair/logs/ssh_validate_after_full.log
cat research/round3_protocol_repair/logs/ssh_full_exit_status.txt
```

## After Run Finishes

If the runner does not create or update the report you need automatically, run:

```bash
cd /home/lyy/ucc_paper_round3
./.venv/bin/python research/round3_protocol_repair/validate_round3_outputs.py
sed -n "1,220p" research/round3_protocol_repair/round3_summary_for_paper_patch.md
sed -n "1,220p" research/round3_protocol_repair/round3_table_provenance_map.md
```

## Immediate Launch Evidence

```text
dyn1: 1 windows (created Thu Jun  4 08:55:22 2026)
round3_repair: 1 windows (created Mon Jul  6 12:45:27 2026)
ye0: 1 windows (created Thu May 21 20:12:14 2026)
```

## Initial Full Log Tail

```text
main_external_baselines: size=4000 method=qiskit_opt3 timeout=600s
main_external_baselines: size=4000 method=qiskit_commutative_inverse timeout=600s
main_external_baselines: size=4000 method=pyzx_configured timeout=600s
main_external_baselines: size=4000 method=pyzx_full_reduce timeout=600s
```


## Operator Notes

- Direct `ssh 39.103.49.217` used the default config entry and failed authentication; the configured `school-server` alias with port 7105 and the dedicated key was used successfully.
- One attempted environment-report generation command was misquoted by the local shell; it did not modify manuscript/proof/runner files and was retried successfully using SSH heredoc into remote Python.
- No `--delete` sync, manuscript edit, proof edit, or old-output overwrite command was used.
