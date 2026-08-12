# Round 6 Pre-change Inventory

Generated: 2026-07-12T04:52:24+00:00

## Repository and manuscript

- Repository root: `/Users/yangjinsey/Desktop/QFT + inverse-QFT circuits #662(issue)`
- Git commit at inventory: `229eafdb4127ab98b2ad925a9657fa67510a12e7`
- Main TeX: `PaperDraft/ucc_paper_draft_latex.tex`
- Appendices A--C: `PaperDraft/appendix/appendix_A.tex`, `appendix_B.tex`, `appendix_C.tex`
- Final PDF: `PaperDraft/ucc_paper_draft_latex.pdf`
- Current PDF: 42 pages, 783093 bytes
- Latest cleanup reports: `ROUND5_FINAL_MINOR_CLEANUP_REPORT.md` and `ROUND5_CLAIM_SCOPE_MICROPATCH_REPORT.md`
- Canonical experiment harness: `research/round3_protocol_repair/run_round3_protocol_repair.py`
- Canonical validators and figure generators: `validate_round3_outputs.py`, `generate_round3_manuscript_figures.py`, and `generate_round3_cleanup_figures.py` in the same directory.

## Gate convention and theorem hooks

- Canonical rational witness source: `_phase_diagonal_block` and `build_fourier_phase_sandwich` in `research/round3_protocol_repair/run_round3_protocol_repair.py`.
- Its middle layer uses Qiskit `RZ(theta)` and `CP(theta)` gates. Qiskit `RZ(theta)=exp(-i theta Z/2)`; `CP(phi)=diag(1,1,1,exp(i phi))`.
- The fixed-width family is `H D^r H` with all four leading and trailing Hadamards explicit.
- Proposition 1 is `prop:fooling-set` in the main TeX; its coefficient-uniqueness dependency is `lem:pauli-uniqueness`.
- The validated pumping architecture is Theorem `thm:final-output`, Corollary `cor:finite-tail`, and Appendix A's restated pumping chain; these are preserved structurally.
- The canonical rational witness remains finite-range only: `T=131040`, reported maximum `R=9999`, and `rank_F2(A)=4<10`.

## Local environment

- Python: `3.13.12 (main, Mar 20 2026, 00:20:47) [Clang 22.1.1 ]`
- Platform: `macOS-26.5.1-arm64-arm-64bit-Mach-O`
- qiskit: `2.4.0`
- PyZX: `0.10.2`
- pytket: `2.16.0`
- pytket-qiskit: `unavailable`
- UCC: `0.4.12`

## Existing SSH execution environment

- Alias: `school-server`; remote project root used previously: `/home/lyy/ucc_paper_round3`.
- Recorded host: `327-cloudhin-3090`, Ubuntu 22.04 kernel 6.8, Intel i7-13700KF, 24 cores, 65,676,560 kB RAM.
- Recorded runtime: Python 3.10.12, qiskit 2.5.0, PyZX 0.10.4, pytket 2.18.0, pytket-qiskit 0.77.0, UCC 0.4.12.
- Previous canonical command: `./.venv/bin/python research/round3_protocol_repair/run_round3_protocol_repair.py --full --timeout-s 600`.
- Round 6 will use a new remote root and new result paths; the old remote/local Round 3 outputs will not be overwritten.

## Key file hashes

| Path | SHA-256 | Bytes |
|---|---|---:|
| `PaperDraft/ucc_paper_draft_latex.tex` | `51eb50b4ed29397162fae7f25299d84dc140b36f21e84471cc3bbecbd1a582f9` | 80071 |
| `PaperDraft/appendix/appendix_A.tex` | `99ab61de92d86f8c925a9ded1b23fc3b3899735578a350ae214278355958da7a` | 20038 |
| `PaperDraft/appendix/appendix_B.tex` | `4f464487827d4d450346d2fff2501c6f2483ecf222a00b5bcdd614eea3c7d4ba` | 13762 |
| `PaperDraft/appendix/appendix_C.tex` | `bd808bf12fcdfab973e185f642ba5b7563860e3bfe6c47386999c75a68715b2d` | 25478 |
| `PaperDraft/ucc_paper_draft_latex.pdf` | `3687ef1f2f9b26205457ae2e29871ed91fd9ec954c791568222264be111106a9` | 783093 |
| `research/round3_protocol_repair/run_round3_protocol_repair.py` | `a42807b06e0bf75289654c50bcd00858e17e86d2e71b5527ca92ea957f646ce7` | 49898 |
| `research/round3_protocol_repair/validate_round3_outputs.py` | `2de41feed6cd383c1c206af6262e0f4a39a43d98235524c96b6437a59ce8aff8` | 4379 |
| `research/round3_protocol_repair/generate_round3_manuscript_figures.py` | `94080ec7c78a2069550c39caebe6b668e82e7659d611cd93630847216ad3395e` | 14029 |
| `research/round3_protocol_repair/generate_round3_cleanup_figures.py` | `f361884fd62a52b887d1cae05dcea76749dd808000537a91b7c0336f7beb715b` | 10550 |
| `ROUND5_FINAL_MINOR_CLEANUP_REPORT.md` | `90aedf0450495ec08274e0a673e00c4aa28c889a0f52dc2d8773c673dcef065a` | 8563 |
| `ROUND5_CLAIM_SCOPE_MICROPATCH_REPORT.md` | `e3370bb46ae53b9aecb11604193ddabeeb65c371b2fb7fc8de5509f215b88a77` | 12122 |

## Frozen JSON baseline

- `research/round6_major_revision/prechange_frozen_hashes.json` records SHA-256 for all 41 pre-existing JSON files under `research/`.
- The following canonical sources are explicitly frozen and will remain byte-for-byte unchanged:

  - `research/round3_protocol_repair/ssh_full_run_20260706_165733/round3_main_external_baselines_results.json` (`3a81d199433b4539a2f932161973b994d41f38bec27ff1267fd73ce9b0b30b2d`)
  - `research/round3_protocol_repair/ssh_full_run_20260706_165733/round3_fourier_ablation_completion_results.json` (`e93c5b00f4bdb12de9802af6c45a6c794cfffdf2ce5e2d9df0f857580fe6ee9c`)
  - `research/round3_protocol_repair/ssh_full_run_20260706_165733/round3_resource_consequence_check_results.json` (`798e92f96127ee30d33cfb80ec48eb62a3caf66c245ddb47ba9d665982bce80d`)
  - `research/round3_protocol_repair/ssh_full_run_20260706_165733/round3_correctness_extension_results.json` (`1d3de2a01c93fb02ca6610486e59a60fd9e126226ac2268251a0e32b269f4575`)
  - `research/noninverse_phase_ladder_scaling_results.json` (`2b5b0a85f796dc3dd02321d29f416384803ba907f75b128a5456ee6f91add146`)
  - `research/generalized_fourier_witness_results.json` (`c2de45ebb141801ecad2b63096176dfa7677bc081fe5aa58cb0dc15c19cdaa42`)
  - `research/fourier_correctness_certificate_results.json` (`f1cd4feb39c74245b66c1bb746cb657169b22beefb98f04245a52d2a185cfc12`)
  - `research/fourier_seed_robustness_results.json` (`3816578512ac0790f0c4ae5634ee1c0b3844c26490e2e88d5376a897dc53e47e`)
  - `research/fourier_topology_external_stress_results.json` (`6e1f65936def3909f3d91b1c657f2e29862e6d0379f91994dda67651f9dfd72e`)
  - `research/width_axis_external_stress_results.json` (`df55e8a32fe0d2f0ff4f31ece73538c8a1af824b051661d2f3f3de44421ab418`)
  - `research/resource_consequence_results.json` (`000dca42da18f209d3141d3ec5bd3f2c1813a738189335f1b756cac36c89db9b`)
  - `research/scaling_results.json` (`3201a3b218698e3b05cd032fb10e871b0e45ad748b618f7493c2b9163a43bd9b`)
  - `research/real_instance_results.json` (`332bbf04482f69f25903bc13818216a57b469631d8ef40b4d3ccc6cf0e1e5a0a`)

## Isolation rule

All new scripts, logs, JSON, provenance records, validators, and experimental figures are written under `research/round6_major_revision/`. Existing JSON is read-only. Manuscript and named publication-facing figure assets are edited only after new results validate.
