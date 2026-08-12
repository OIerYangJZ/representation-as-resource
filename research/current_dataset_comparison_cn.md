# 当前数据集对比（简版）

这份文档只做一件事：把当前几组核心数据集的结论压成一页，方便和导师、reviewer、合作者快速对齐。

## 1. 官方真实实例

实例：

- `phase_estimation_real`
- `grover_real`
- `qaoa_real`

结论：

- 三组实例上，`optimized UCC` 全部追平 `qiskit opt3` 的输出质量。
- 三组实例上，runtime 也都已经压到和 `qiskit opt3` 同一量级。
- 因此这组证据支持的是：
  - baseline UCC 的退化是真实存在的；
  - 当前方法可以把 UCC 拉回到强外部 baseline 的质量水平。

## 2. `MQT Bench`

实例：

- `mqt_qpeexact_32`
- `mqt_qaoa_32`
- `mqt_grover_20`

结论：

- `mqt_qpeexact_32`、`mqt_qaoa_32` 上，`optimized UCC` 与 `qiskit opt3` 质量追平。
- `mqt_grover_20` 上，baseline UCC 超时，而 `optimized UCC` 能达到 `qiskit opt3` 质量。
- 这说明当前方法不只在官方 Qiskit library 样例上有效，在外部公共 benchmark source 上也成立。

## 3. `SupermarQ`

实例：

- `supermarq_mermin_bell_8`
- `supermarq_qaoa_vanilla_12`
- `supermarq_hamiltonian_sim_8`

结论：

- `mermin_bell` 和 `qaoa_vanilla` 继续体现明显的 quality-recovery。
- `hamiltonian_sim_8` 当前更适合作为 mixed/parity case，不应过度主张。
- 这组结果的意义是：
  - 当前方法不是每个 family 都占优；
  - 但在多个公开 benchmark family 上都能显著修复 baseline UCC 的退化。

## 4. fixed-basis 100k structured families

代表结果：

- repeated `QFT + QFT^-1`：optimized `0`
- repeated `QFT + QFT`：optimized `347,500`
- `qpe_style`：optimized `164,400`
- `qaoa_ring`：optimized `100,000`
- `grover_mirrored`：optimized `1,158,011`

结论：

- `qft_inverse` 和 `qft_control` 说明 pre-basis 结构机会非常强。
- `qpe_style` 继续是当前最强的 fixed-basis 家族之一。
- `qaoa_ring` 的价值主要是防止 baseline UCC 膨胀。
- `grover_mirrored` 质量已经显著优于 baseline UCC，并追平强 fixed-basis Qiskit baseline。

## 5. hardware-aware

实例：

- `hw_mqt_qpeexact_20`
- `hw_mqt_qaoa_20`
- `hw_mqt_grover_20`

结论：

- `hw_mqt_qpeexact_20`：当前是 clean parity case。
- `hw_mqt_qaoa_20`：当前是最明确的 hardware-aware external-baseline win。
- `hw_mqt_grover_20`：当前更适合作为 robustness / timeout-recovery 证据。

当前最新 spot check：

- `hw_mqt_qpeexact_20`：optimized `1572 / 407 / cx 812 / 0.235s`
- `hw_mqt_qaoa_20`：optimized `2050 / 487 / cx 1458 / 0.112s`
- `hw_mqt_grover_20`：optimized `6,467,857 / 4,094,196 / cx 3,045,048 / 1.999s`

## 6. 一句话总论

当前最稳的结论不是：

- “我们全面超过了 Qiskit”

而是：

- `optimized UCC` 现在已经能够在多组真实实例和公共 benchmark 上稳定追平 `qiskit opt3` 的质量，
- 在至少一个 hardware-aware 公共 case 上明确胜出，
- 并在更难的 routed Grover case 上提供强于 baseline 的 robustness/timeout-recovery。
