# 仓库清理候选清单（仅列出，未执行任何删除）

仓库当前 2.1 GB。核心「论文 + 可复现源码」约 80 MB。

复现入口是 `reproducibility/run_submission.sh`，它依赖：
`scripts/` → `data/frozen/` + `data/manifest.yaml` + `data/provenance_map.yaml` +
`schema/` + `configs/` + `benchmarks/` `certificates/` `compiler/` `encoding/`
`instrumentation/` `qre/` `workloads/` `baselines/` → `figures/` + `PaperDraft/generated/`
→ `tests/` → `PaperDraft/main.tex` + `supplement.tex`。
以下清单均已核对不在这条链上。

---

## 必须保留（勿删）

- `PaperDraft/`：`main.tex` `main_arXiv.tex` `supplement.tex` `references.bib`
  `main.bbl` `supplement.bbl`（arXiv 投稿需要）`main.pdf` `supplement.pdf`
  `appendix/` `figures/` `generated/` `research/` `scripts/` `cover_letter/*.tex,*.pdf`
- `theory/*.tex`（被 `main.tex` 直接 `\input`）
- `scripts/` `tests/` `reproducibility/` `schema/` `configs/`
- `data/frozen/` `data/manifest.yaml` `data/provenance_map.yaml`
- `benchmarks/` `certificates/` `compiler/` `encoding/` `instrumentation/` `qre/`
  `workloads/` `baselines/` `figures/`
- `ucc/__init__.py` `ucc/_version.py` `ucc/compile.py` `ucc/transpilers/` `ucc/tests/`
- `pyproject.toml` `uv.lock` `LICENSE` `README.md` `CHANGELOG.md` `docs/`
  `.github/` `.gitignore` `.pre-commit-config.yaml` `.coveragerc` `.readthedocs.yml`
- `research/` 中被 appendix 引用的部分（见 C-4）

---

## A 档：确定可删，零信息损失（约 155 MB）

### A-1 缓存与系统垃圾（约 9 MB）
```
.DS_Store                      # 共 10 个，遍布各目录
PaperDraft/.DS_Store
**/__pycache__/                # 共 73 个目录（不含 .venv）
.pytest_cache/
.ruff_cache/
```

### A-2 LaTeX 编译中间产物（2.3 MB，`latexmk` 可重建）
```
PaperDraft/main.aux
PaperDraft/main.log
PaperDraft/main.blg
PaperDraft/main.fls
PaperDraft/main.fdb_latexmk
PaperDraft/main.out
PaperDraft/mainNotes.bib
PaperDraft/supplement.aux
PaperDraft/supplement.log
PaperDraft/supplement.blg
PaperDraft/supplement.fls
PaperDraft/supplement.fdb_latexmk
PaperDraft/supplement.out
PaperDraft/supplementNotes.bib
PaperDraft/out/                # 旧一轮的 aux/log/pdf/synctex 输出目录
PaperDraft/cover_letter/out/
PaperDraft/patches/out/
```
注意：`main.bbl` / `supplement.bbl` **保留**（arXiv 上传需要）。

### A-3 `tmp/` 全部（142 MB）— 预检脚本的临时工作区
```
tmp/                           # 整个目录
  ├ pdfs/                 53M  # 页面截图 PNG + 字体缓存
  ├ w4-*-preflight*/      70M  # 5 份 w4 预检重复副本
  ├ w5-preflight*/       1.4M
  ├ fontconfig-w8|w9/     12M  # 字体缓存
  ├ matplotlib-w8|w9|qre/ 432K # matplotlib 缓存
  ├ round5_final/        5.3M
  ├ w4-analysis-unit/
  └ certificate-preflight.json
```

### A-4 `ucc/` 里嵌套的整仓库副本（19 MB）
`ucc/` 同时是 Python 包**和**一份旧的整仓库拷贝。以下是拷贝部分：
```
ucc/RelatedWorks/              13M  # 论文 PDF 副本
ucc/Graph Materials/          2.5M
ucc/research/                 1.5M
ucc/PaperDraft/               600K
ucc/docs/                     396K
ucc/out/                      244K
ucc/Paper/
ucc/ucc/                      608K  # 包对自身的再次嵌套拷贝
ucc/__pycache__/
ucc/draft.tex
ucc/plan.tex
ucc/plan_cn.tex
ucc/uv.lock
ucc/pyproject.toml
ucc/README.md
ucc/LICENSE
ucc/CHANGELOG.md
ucc/GEMINI.md
ucc/DEV_CONTEXT.md
ucc/issue_qft_expansion_bug.md
ucc/pr_fix_lookuperror_env_path_description.md
```

---

## B 档：评审/投稿流程产物，与论文和复现均无关（约 30 MB）

### B-1 根目录逐轮评审报告与日志（约 25 个文件）
```
ROUND3_CLEANUP_PATCH_REPORT.md
ROUND3_CV_MICROPATCH_REPORT.md
ROUND3_MANUSCRIPT_PATCH_REPORT.md
ROUND4_EDITORIAL_REFRAMING_PATCH_REPORT.md
ROUND4_MICRO_BIB_BUILD_PATCH_REPORT.md
ROUND5_CLAIM_SCOPE_MICROPATCH_REPORT.md
ROUND5_FINAL_MINOR_CLEANUP_REPORT.md
ROUND6_1_REMEDIATION_REPORT.md
ROUND6_MAJOR_REVISION_REPORT.md
ROUND6_2_CHANGED_FILES.txt
ROUND6_2_UPLOAD_MANIFEST.txt
ROUND6_2_VALIDATOR_HYGIENE_REPORT.md
ROUND6_2_1_COMMAND_EXECUTION_LOG.txt
ROUND6_2_1_PROTECTED_SCIENTIFIC_SHA256_AFTER.txt
ROUND6_2_1_PROTECTED_SCIENTIFIC_SHA256_BEFORE.txt
ROUND6_2_1_VALIDATOR_HARDENING_REPORT.md
ROUND6_2_2_CHANGED_FILES.txt
ROUND6_2_2_COMMAND_EXECUTION_LOG.txt
ROUND6_2_2_FINAL_VALIDATOR_FREEZE_FINDINGS_EXCERPT.txt
ROUND6_2_2_PROTECTED_SHA256_AFTER.txt
ROUND6_2_2_PROTECTED_SHA256_BEFORE.txt
ROUND6_2_2_PROTECTED_SHA256_DIFF.txt      # 0 字节
ROUND6_2_2_VALIDATOR_MICROFIX_REPORT.md
ROUND6_2_3_CHANGED_FILES.txt
ROUND6_2_3_COMMAND_EXECUTION_LOG.txt
ROUND6_2_3_FABLE_PROMPT.txt
ROUND6_2_3_FABLE_UPLOAD_LIST.txt
ROUND6_2_3_PROTECTED_SHA256_AFTER.txt
ROUND6_2_3_PROTECTED_SHA256_BEFORE.txt
ROUND6_2_3_PROTECTED_SHA256_DIFF.txt      # 0 字节
ROUND6_2_3_TASK_SPECIFICATION.txt
ROUND6_2_3_VALIDATOR_MICROFIX_REPORT.md
FABLE_ROUND6_2_1_PACKAGING_VALIDATION_LOG.txt
README_FOR_FABLE.md
README_ROUND6_2_3_FOR_FABLE.md
final_copyedit_report.md
final_local_edit_report.md
integration_report.md
integration_fix_report.md
pr_fix_lookuperror_env_path_description.md
EXPERIMENT_FILE_INVENTORY.md              # 49 KB 的一次性文件盘点
EXPERIMENT_SIDE_HARDEST_CORE_BUNDLE_MANIFEST.md
```

### B-2 打包上传的 bundle 目录与 zip（约 24 MB）
每个都是当时仓库子集的完整拷贝：
```
ROUND6_2_2_FABLE_BUNDLE/            2.9M
ROUND6_2_2_FABLE_BUNDLE.zip         1.2M
ROUND6_2_3_FABLE_BUNDLE/            3.0M
ROUND6_2_3_FABLE_BUNDLE.zip         1.2M
ROUND6_2_3_FABLE_BUNDLE.zip.sha256
FABLE_ROUND6_2_1_VALIDATOR_DELTA_BUNDLE/    2.9M
FABLE_ROUND6_2_1_VALIDATOR_DELTA_BUNDLE.zip 1.2M
FABLE_ROUND6_UPLOAD/                1.4M
fable_round6_1_verification_bundle/ 1.6M
fable_round6_1_verification_bundle.zip      951K
CLAUDE_EXPERIMENT_SIDE_UPLOAD/      1.1M
EXPERIMENT_SIDE_HARDEST_CORE_BUNDLE.zip     188K
review_bundles/                     4.0M   # round6_2_fable_final/ + .zip
witness_rank_audit/                  24K
witness_rank_audit.zip
witness_noncollision_audit/          28K
```

### B-3 `PaperDraft/` 内的历史稿与评审文档
```
PaperDraft/legacy_main_v7_2.tex          # v7.2 旧主稿，103 KB
PaperDraft/parking_lot.tex               # 弃用段落暂存
PaperDraft/patches/                      # 逐轮 .docx 攻击/验证报告 + patch tex
PaperDraft/overleaf_bundle/              # 由 scripts/make_overleaf_bundle.sh 重建
PaperDraft/overleaf_bundle.zip           690K
PaperDraft/0808comment.md
PaperDraft/BUILD_PLAN_claude_code.md
PaperDraft/Comments on new proposal-Opus-5.md    # 43 KB
PaperDraft/Manuscript_Revision_Suggestions.docx
PaperDraft/PACKING_SCALING_EXPERIMENT_REPORT.md
```

### B-4 图片镜像目录 `Graph Materials/`（924 KB）
无任何 `.tex` 引用它；是 `PaperDraft/figures/` 的镜像。已逐一核对哈希：
`01_fourier_separation.pdf` 与 `04_unbounded_witness_scaling.pdf` 与
`PaperDraft/figures/` 下对应文件**完全相同**；`02`/`03` 是更旧的版本。
```
Graph Materials/                    # 整个目录
```
可选：保留 `generate_prx_figures.py` / `generate_separation_figure.py` 两个绘图脚本
和 `conceptual_theorem_figure.tex`，若它们是当前图的唯一生成源。

### B-5 根目录一次性审计报告
这些是过程报告，其结论已写入论文正文/附录：
```
CERTIFICATE_AUDIT_REPORT.md
CHANGELOG_PRXQ.md
CLAIM_EVIDENCE_MATRIX.md
CLEAN_ROOM_REPORT.md
DATA_AUDIT_REPORT.md
EXTERNAL_BASELINE_REPORT.md
MATCHED_REPRESENTATION_REPORT.md
MODEL_ACCOUNTING_AUDIT.md
NATURAL_WORKLOAD_REPORT.md
QRE_REPORT.md
SUBMISSION_READINESS_REPORT.md
THEORY_STATUS.md
TRADEOFF_VALIDATION_REPORT.md
XX_chain_166q_experiment_proposal.md
DEV_CONTEXT.md
ucc_paper_draft_latex.pdf            # 767 KB，旧编译产物
```
（若想留一份可追溯记录，建议只留 `CLAIM_EVIDENCE_MATRIX.md` 和
`CHANGELOG_PRXQ.md`，其余删。）

### B-6 空目录
```
tables/                              # 0 字节，由 build_all_tables.py 重建
```

---

## C 档：需要你拍板（约 1.7 GB —— 主要空间在这里）

### C-1 `.venv/`（941 MB）⚠️ 最大项
可由 `uv sync` + `uv.lock` 完整重建，本身不应进仓库。
但 `reproducibility/run_submission.sh` 与 `run_clean_room.py` 硬编码使用
`.venv/bin/python`，删掉后要复现必须先重建虚拟环境。
**建议：删除，并在 `.gitignore` 里补上 `.venv/`**（目前它不在 `.gitignore` 里）。

### C-2 `data/runs/`（553 MB）⚠️ 第二大项
```
data/runs/w3-tradeoff-20260802-local        253M
data/runs/w5-external-baselines-20260803    178M
data/runs/w4-matched-representation-20260802 76M
data/runs/w8-natural-20260803-local          46M
data/runs/w7-fixed-total-error-20260803-local 1.2M
```
`data/manifest.yaml` 明确写着：
> "Raw run trees are retained as provenance but are not scanned as independent
> canonical datasets."

也就是说 **canonical 数据全在 `data/frozen/`（65 MB）**，`data/runs/` 只是原始溯源。
但 `PaperDraft/appendix/appendix_B.tex:310` 在正文里点名了
`data/runs/w7-fixed-total-error-20260803-local/`。

**建议：删除 w3/w4/w5/w8 四个大目录（547 MB），保留 w7（1.2 MB，被附录引用）。**
如果期刊可能要求原始数据，请先归档到外部存储再删。

### C-3 `research/round6_major_revision/tools/`（95 MB）
第三方外部工具的源码与编译产物，非本项目代码：
```
research/round6_major_revision/tools/feynman/     46M
research/round6_major_revision/tools/staq/        36M
research/round6_major_revision/tools/staq-venv/   13M
research/round6_major_revision/tools/staq_rotation_optimizer/  608K
```
可从上游仓库重新获取。**建议删除，但在 README 里记下版本/commit 以保证可复现。**
`research/round6_major_revision/` 的其余部分（结果 JSON、验证脚本）**必须保留** ——
`PaperDraft/appendix/appendix_B.tex:259` 直接引用它。

### C-4 `research/`（根目录，去掉 tools 后约 4 MB）
这是早期探索性实验，与当前论文的 W3–W9 流程无关。
但 appendix 引用了其中一部分。核对结果：

**必须保留**：
- `research/round6_major_revision/`（除 `tools/`）
- `research/rc_frame_cross_cut_note.md`（`main.tex:103` 引用）
- `research/compare_real_instances.py`（`appendix_B.tex:173` 引用）
- `research/round3_protocol_repair/`（536 KB，未确认，建议保留）

**可删**（早期探索，无引用）：约 130 个 `*_results.json` / `*_results.md` /
`compare_*.py` 散落文件，例如
`generalized_fourier_witness_results.json`、`quantum_paper_draft.md`（68 KB 旧草稿）、
`experiment_results_overview_cn.md`、`fourier_seed_robustness_results.json` 等。
**建议：这一档先不动，等你确认后我再逐个核对引用。**

---

## 汇总

| 档位 | 内容 | 可回收 |
|---|---|---|
| A | 缓存、LaTeX 中间产物、`tmp/`、`ucc/` 嵌套副本 | ~155 MB |
| B | 评审报告、bundle/zip、历史稿、图片镜像 | ~30 MB |
| C-1 | `.venv/` | 941 MB |
| C-2 | `data/runs/` 中 w3/w4/w5/w8 | 547 MB |
| C-3 | `research/round6_major_revision/tools/` | 95 MB |
| **合计** | | **~1.77 GB → 剩余约 330 MB**（含 `data/frozen/` 65 MB） |

## 执行前提醒

1. **A 档 + B 档中有部分文件已被 git 跟踪**（`Graph Materials/`、`ucc/` 嵌套副本、
   `docs/`），删除它们会产生一次 commit，需要 `git rm` 而非 `rm`。
2. 当前分支 `exp-commit-toll` 有 **201 项未提交改动**，建议**先提交或打 tag** 再清理，
   这样任何误删都能从 git 恢复。
3. C-2（`data/runs/`）删除前，如原始数据不可再生，请先外部归档。
4. 清理后建议在 `.gitignore` 补充：
   `.venv/`、`.pytest_cache/`、`.ruff_cache/`、`tmp/`、
   `*.aux *.log *.fls *.fdb_latexmk *.out *.blg *Notes.bib`
5. 本文件 `CLEANUP_CANDIDATES.md` 本身在清理完成后也应删除。
