# 冲击 Quantum (Journal) 的清单

## 目标

这份清单用于界定：当前这条 UCC 优化工作距离 **Quantum (Journal)**
投稿还差什么。

当前最稳的论文定位已经收敛为：

> 一篇量子编译系统研究，说明有界的 basis lowering 前结构化预处理加上
> 保守的 candidate control，能够显著修复 UCC 默认流水线在结构化线路上
> 的退化，在真实与公共 benchmark 上恢复到 `qiskit opt3` 级别的输出质量，
> 并在 `hw_mqt_qaoa_20` 上取得稳定的 hardware-aware 胜场。

## 当前状态

核心实验条件已经满足。

已经具备：

- 官方 Qiskit 真实实例
  - `PhaseEstimation`
  - `GroverOperator`
  - `QAOAAnsatz`
- 强 baseline 对比
  - baseline UCC
  - `qiskit opt3`
  - `qiskit_commutative_inverse`
- scaling 与 ablation
- 两个公共 benchmark source
  - `MQT Bench`
  - `SupermarQ`
- 一组 hardware-aware 实验
- `hw_mqt_qaoa_20` 的 5-seed 稳定胜场
- artifact 和一键复现入口

## 当前最强结果

### 真实实例

- `phase_estimation_real`
  - baseline UCC: `471,819`
  - optimized UCC: `166,805`
  - `qiskit opt3`: `166,805`
- `grover_real`
  - baseline UCC: `287,047`
  - optimized UCC: `79,029`
  - `qiskit opt3`: `79,029`
- `qaoa_real`
  - baseline UCC: `167,833`
  - optimized UCC: `36,512`
  - `qiskit opt3`: `36,512`

### 公共 benchmark

- `MQT Bench`
  - `mqt_qpeexact_32`：optimized UCC 追平 `qiskit opt3`
  - `mqt_qaoa_32`：optimized UCC 追平 `qiskit opt3`
  - `mqt_grover_20`：optimized UCC 追平 `qiskit opt3`，baseline UCC 超时
- `SupermarQ`
  - `supermarq_mermin_bell_8`：optimized UCC 追平 `qiskit opt3`
  - `supermarq_qaoa_vanilla_12`：optimized UCC 追平 `qiskit opt3`
  - `supermarq_hamiltonian_sim_8`：mixed case，不优于最强 Qiskit baseline

### Hardware-aware 胜场

- `hw_mqt_qaoa_20`
  - `qiskit opt3`: `2091` gates, depth `532`, `cx = 1530`
  - optimized UCC: `2050` gates, depth `487`, `cx = 1458`
- 该胜场在 seeds `0`、`1`、`42`、`12345`、`54321` 上稳定成立

## 论文口径

论文 **不应** 主张：

- “我们做出了一个全面更强的新编译器”
- “exact inverse cancellation 本身是新的”
- “我们在所有 workload family 上都超过了 Qiskit”

论文 **应当** 主张：

- baseline UCC 存在真实的结构化退化
- 这种退化不能仅用简单的 pass 顺序修复完全解释
- 有界的 pre-basis 结构化预处理加上 candidate control 能稳定修复这些退化
- 至少在一个稳定的 hardware-aware 公共 benchmark 上，该方法超过 `qiskit opt3`

## 剩余工作

剩余工作已经主要是投稿打包，而不是继续补核心实验：

- 完成 Quantum 版主稿
- 补最小图表集
- 准备投稿元信息与 cover materials

## 当前判断

- 实验：已就绪
- 复现：已就绪
- 主张：已收紧
- 投稿包装：进行中
