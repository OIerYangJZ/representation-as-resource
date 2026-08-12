# Round 3 SSH Environment Setup

Generated: `2026-07-06T04:43:38+00:00` UTC

## Commands Used

```bash
python3 -m pip install --user -U uv
cd /home/lyy/ucc_paper_round3 && ~/.local/bin/uv venv --python 3.12 .venv && ~/.local/bin/uv sync --group research && ~/.local/bin/uv pip install pytket-qiskit
# The uv-managed Python 3.12 download stalled with no cache growth and was terminated.
python3 -m pip install --user -U virtualenv
cd /home/lyy/ucc_paper_round3 && ~/.local/bin/virtualenv --clear -p /usr/bin/python3 .venv
./.venv/bin/python -m pip install -U pip setuptools wheel
./.venv/bin/python -m pip install "cirq-core>=1.4.1,<2.0.0" "ply>=3.11,<4.0.0" "pytket>=1.40.0,<3.0.0" "qbraid>=0.9.3,<1.0.0" "qiskit>=1.4.2,<3.0.0" "qiskit-qasm3-import>=0.5.1,<1.0.0" "pyzx>=0.9.0,<0.11.0" pytket-qiskit
./.venv/bin/python -m pip install --no-deps --ignore-requires-python -e .
```

## Environment Decision Notes

- Server system Python is `3.10.12`; project metadata declares `>=3.12,<3.14`.
- `uv` was installed, but `uv venv --python 3.12` stalled while downloading the managed Python runtime; cache growth was only about 32K after several minutes.
- Fallback used project-local `virtualenv` on system Python 3.10 and installed the actual Round 3 runner dependency closure.
- `quimb==1.12.1` was not installed because it requires Python >=3.11 and the Round 3 runner/default UCC path does not import it.
- Local `ucc` was installed editable with `--no-deps --ignore-requires-python` after external dependencies were installed normally.

## Paths

- Remote project path: `/home/lyy/ucc_paper_round3`
- Python executable path: `/home/lyy/ucc_paper_round3/.venv/bin/python`

## Versions And Imports

- Python version: `3.10.12`
- pip version: `pip 26.1.2 from /home/lyy/ucc_paper_round3/.venv/lib/python3.10/site-packages/pip (python 3.10)`
- uv version: `uv 0.11.26 (x86_64-unknown-linux-gnu)`
- qiskit version: `2.5.0`
- pyzx version: `0.10.4`
- pytket version: `2.18.0`
- pytket-qiskit distribution: `0.77.0`
- pytket.extensions.qiskit imports: `yes`
- FullPeepholeOptimise imports: `yes`
- PauliSimp imports: `yes`
- GuidedPauliSimp imports: `yes`
- ucc version: `0.4.12`

## Machine

- Hostname: `327-cloudhin-3090`
- Date/timezone: `Mon Jul  6 12:43:39 CST 2026; TZ=system default`
- OS/kernel: `Linux 327-cloudhin-3090 6.8.0-111-generic #111~22.04.1-Ubuntu SMP PREEMPT_DYNAMIC Tue Apr 14 17:13:45 UTC  x86_64 x86_64 x86_64 GNU/Linux`
- Platform: `Linux-6.8.0-111-generic-x86_64-with-glibc2.35`
- CPU model: `13th Gen Intel(R) Core(TM) i7-13700KF`
- CPU core count: `24`
- RAM: `65676560 kB`

## Git Snapshot

- Git branch: `unavailable: CalledProcessError: Command '['git', 'rev-parse', '--abbrev-ref', 'HEAD']' returned non-zero exit status 128.`
- Git commit: `unavailable: CalledProcessError: Command '['git', 'rev-parse', 'HEAD']' returned non-zero exit status 128.`
- Git status: `unavailable: CalledProcessError: Command '['git', 'status', '--short', '--branch']' returned non-zero exit status 128.`
