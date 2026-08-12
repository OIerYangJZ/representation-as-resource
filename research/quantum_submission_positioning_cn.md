# Quantum 投稿口径

## 一句话定位

这篇论文是一篇可复现的量子编译系统研究，说明有界的 basis lowering 前结构化预处理加上保守的 candidate control，能够作为 UCC 的 anti-regression / quality-recovery layer。

## 我们主张什么

1. baseline UCC 在结构化 workload 上存在真实退化
2. 这些退化不能仅用简单的 pass 顺序修复完全解释
3. 当前优化分支在官方真实实例和多个公共 benchmark family 上恢复到 `qiskit opt3` 级别的输出质量
4. 当前优化分支在至少一个稳定的 hardware-aware 公共 benchmark（`hw_mqt_qaoa_20`）上超过 `qiskit opt3`

## 我们不主张什么

1. 我们没有做出一个全面更强的新编译器
2. exact inverse cancellation 本身不是本文的新意
3. 当前方法并没有在所有 workload family 上都压过强 Qiskit baseline

## 面向审稿人的 framing

最关键的一点是：贡献不是某个单独 rewrite rule，而是 UCC 决策流程的一次有界重设计：

- pre-basis structural preprocessing
- conservative candidate selection
- source-level short-circuiting
- 仅在必要时触发的 backend-aware portfolio search

## 最值得强调的证据

- 官方真实实例：
  - `phase_estimation_real`
  - `grover_real`
  - `qaoa_real`
- 公共 benchmark source：
  - `MQT Bench`
  - `SupermarQ`
- 稳定性：
  - `hw_mqt_qaoa_20` 在 5 个 fixed seed 上稳定胜出
- hardware-aware 证据：
  - `hw_mqt_qaoa_20` 是稳定胜场
  - `hw_mqt_qpeexact_20` 在当前 canonical fixed seed 上与 `qiskit opt3` 追平

## 需要主动承认的弱点

- 有些 family 目前仍然只是追平 `qiskit opt3`
- `supermarq_hamiltonian_sim_8` 是 mixed case
- 当前方法是 bounded heuristic，不是全局最优方法
- `hw_mqt_grover_20` 目前仍更适合作为 timeout-recovery / robustness case，
  而不是主质量结果；不过 stronger mirrored/self-inverse repeated-run IR
  已经进一步降低了它的 total gates / depth / `cx`

## 最推荐的论文主张

> 有界的 pre-basis 结构化预处理，是 UCC 的一个有意义的优化方向：它能修复默认流水线的严重退化，在真实和公共 benchmark 上恢复到 Qiskit 级别的输出质量，并在稳定的 hardware-aware 公共 case 上超过 `qiskit opt3`，同时在更难的 routed case 上提升鲁棒性。
