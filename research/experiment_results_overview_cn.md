# 实验结果总览（`#662(issue)`）

本文档汇总 `#662(issue)` 工作区中当前冻结后的主要实验结果与结论，供论文、grant、reviewer 回复和内部讨论统一引用。

对应的 canonical 结果文件主要包括：

- `real_instance_results_summary.md`
- `mqt_bench_results_summary.md`
- `supermarq_results_summary.md`
- `hardware_aware_results_summary.md`
- `runtime_optimization_progress.md`
- `runtime_overheads_issue_summary.md`
- `phase_ladder_positive_results_summary.md`
- `qft_inverse_external_scaling_results_summary.md`
- `noninverse_phase_ladder_scaling_results_summary.md`

## 1. 当前工作的核心问题

当前工作的目标不是提出一个“全面优于 Qiskit 的新编译器”，而是研究：

- UCC 默认流水线在结构化电路上会出现怎样的退化；
- 这种退化是否只是简单的 pass 顺序问题；
- bounded pre-basis structural preprocessing 加上 candidate selection / short-circuiting 是否能稳定修复这些退化；
- 在真实算法族实例、公共 benchmark 和 hardware-aware 条件下，这种修复是否仍然成立。

当前最准确的定位是：

> 这套工作现在应定位为 representation-dependent recoverability gap 的编译实验：basis lowering 保持语义但可能破坏可恢复结构；bounded semantic term controller 能在 UCC 中保留这些结构、延迟 materialization，并在若干结构族上关闭这种 recoverability gap。经验结果包括广泛的 `qiskit opt3` quality recovery、非 inverse `H·D^r·H` Fourier-layer family 的 `5/5` strict structural-quality win、`QFT + QFT^-1` family 的系统性 runtime/scalability 胜场，以及 `hw_mqt_qaoa_20` 的固定实例 hardware-aware 胜场。

## 当前几组数据集的简明对比

| 数据集 | 当前最稳结论 |
|---|---|
| 官方真实实例 | `optimized UCC` 在 `phase_estimation_real`、`grover_real`、`qaoa_real` 上全部追平 `qiskit opt3` 质量，runtime 也已经接近 parity |
| `MQT Bench` | `mqt_qpeexact_32`、`mqt_qaoa_32` 质量追平 `qiskit opt3`；`mqt_grover_20` 也达到 parity，并显著修复 baseline UCC 的超时退化 |
| mirrored/conjugation 正例与 scaling | `grover_real`、`mqt_grover_8/12/16`、`grover_mirrored_10k/20k/50k/100k` 全部追平 `qiskit opt3`，并显著优于 baseline UCC |
| `phase-ladder` 正例集 | `mqt_qpeinexact_24`、`mqt_ae_8`、`mqt_draper_qft_adder_32` 全部追平 `qiskit opt3`，并显著优于 baseline UCC |
| 非 inverse Fourier-layer scaling | `fourier_phase_sandwich = H·D^r·H` 在 `4k/10k/20k/50k/100k` 上全部严格优于 `qiskit opt3` 的 gates/depth/`cx`；50k/100k 时 `qiskit opt3` timeout，而 optimized UCC 输出恒为 `42` gates |
| `QFT + QFT^-1` external scaling | `4k/10k/20k/50k/100k` 全部归零；optimized UCC 在所有规模上相对 `qiskit opt3` 是 no-worse quality + runtime/scalability win，并且全规模快于 `qiskit_commutative_inverse` |
| `SupermarQ` | `mermin_bell` 与 `qaoa_vanilla` 继续是 quality-recovery；`hamiltonian_sim_8` 当前是 parity/mixed family，不应过度主张 |
| fixed-basis 100k | `qft_inverse -> 0`，`qft_control -> 347,500`，`qpe_style -> 164,400`，`qaoa_ring -> 100,000`，`grover_mirrored -> 1,158,011` |
| hardware-aware | `hw_mqt_qpeexact_20` 是 clean parity；`hw_mqt_qaoa_20` 是明确 external-baseline win；`hw_mqt_grover_20` 是更强的 robustness / timeout-recovery case |

## 2. 官方真实实例（Qiskit circuit library）

固定 target basis：

- `['cx', 'rx', 'ry', 'rz', 'h']`

使用的官方实例：

- `PhaseEstimation`
- `GroverOperator`
- `QAOAAnsatz`

### 2.1 `phase_estimation_real`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation only | 159,838 | 121,214 | 67,608 | 0.100 s |
| qiskit opt3 | 166,805 | 119,204 | 58,491 | 1.298 s |
| baseline UCC | 471,819 | 328,271 | 58,491 | 80.923 s |
| optimized UCC | 166,805 | 119,204 | 58,491 | 1.364 s |

结论：

- 相比 baseline UCC，门数下降约 `64.6%`。
- 输出质量与 `qiskit opt3` 完全追平。
- runtime 已压到与 `qiskit opt3` 同一量级。

### 2.2 `grover_real`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation only | 85,403 | 55,892 | 33,408 | 0.084 s |
| qiskit opt3 | 79,029 | 54,163 | 32,544 | 0.552 s |
| baseline UCC | 287,047 | 152,298 | 32,544 | 1.915 s |
| optimized UCC | 79,029 | 54,163 | 32,544 | 0.556 s |

结论：

- 相比 baseline UCC，门数下降约 `72.5%`。
- 输出质量与 `qiskit opt3` 追平。
- runtime 在小常数因子范围内落后于 `qiskit opt3`，但已远好于早期分支。

### 2.3 `qaoa_real`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation only | 36,512 | 2,416 | 23,808 | 0.020 s |
| qiskit opt3 | 36,512 | 2,416 | 23,808 | 0.272 s |
| baseline UCC | 167,833 | 7,133 | 23,808 | 1.010 s |
| optimized UCC | 36,512 | 2,416 | 23,808 | 0.273 s |

结论：

- 相比 baseline UCC，门数下降约 `78.2%`。
- 输出质量与 `qiskit opt3` 追平。
- runtime 与 `qiskit opt3` 接近。

### 2.4 真实实例总论

在这 3 个官方真实实例上，当前工作已经证明：

- baseline UCC 的退化是真实且严重的；
- optimized UCC 能稳定把输出质量拉回到 `qiskit opt3` 水平；
- 当前 runtime 已压到与 `qiskit opt3` 几乎同一量级，其中 `grover_real`
  与 `qaoa_real` 基本达到 runtime parity。

## 3. 公共 benchmark source 1：MQT Bench

实例：

- `mqt_qpeexact_32`
- `mqt_qaoa_32`
- `mqt_grover_20`

### 3.1 `mqt_qpeexact_32`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation only | 2,620 | 367 | 1,037 | 0.007 s |
| qiskit opt3 | 1,891 | 307 | 904 | 0.023 s |
| baseline UCC | 5,494 | 818 | 764 | 0.074 s |
| optimized UCC | 1,891 | 307 | 904 | 0.023 s |

### 3.2 `mqt_qaoa_32`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation only | 1,422 | 213 | 884 | 0.004 s |
| qiskit opt3 | 1,422 | 213 | 884 | 0.014 s |
| baseline UCC | 6,310 | 597 | 884 | 0.074 s |
| optimized UCC | 1,422 | 213 | 884 | 0.016 s |

### 3.3 `mqt_grover_20`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| translation only | 4,099,297 | 3,300,108 | 1,546,096 | 6.106 s |
| qiskit opt3 | 3,848,810 | 3,269,433 | 1,546,096 | 38.043 s |
| baseline UCC | timeout | - | - | > 120 s |
| optimized UCC | 3,848,810 | 3,269,433 | 1,546,096 | 39.123 s |

### 3.4 `MQT Bench` 总论

- 在 `mqt_qpeexact_32` 和 `mqt_qaoa_32` 上，optimized UCC 与 `qiskit opt3` 输出质量追平，并显著优于 baseline UCC。
- 在 `mqt_grover_20` 上，optimized UCC 也达到 `qiskit opt3` 质量，但 runtime 仍更慢。
- 这组结果说明：当前方法并不局限于官方 Qiskit library 样例，在外部公共 benchmark source 上仍成立。

### 3.5 `phase-ladder` 正例补充

为支撑当前 `phase-ladder / Fourier-layer` 理论线，还补了 3 个聚焦正例：

- `mqt_qpeinexact_24`
- `mqt_ae_8`
- `mqt_draper_qft_adder_32`

结果如下：

| Instance | baseline UCC | optimized UCC | qiskit opt3 |
|---|---:|---:|---:|
| `mqt_qpeinexact_24` | `3,682` gates, depth `606` | `1,206` gates, depth `228` | `1,206` gates, depth `228` |
| `mqt_ae_8` | `542` gates, depth `191` | `207` gates, depth `100` | `207` gates, depth `100` |
| `mqt_draper_qft_adder_32` | `5,278` gates, depth `662` | `1,630` gates, depth `275` | `1,630` gates, depth `275` |

这 3 个正例的意义不是“又多了几张表”，而是：

- `qpeinexact` 说明当前理论不只覆盖 exact-QPE
- `ae` 把同一条线扩展到 amplitude-estimation family
- `draper_qft_adder` 把同一条线扩展到 QFT-based arithmetic family

因此现在更稳的理论叙事是：

> `phase-ladder / Fourier-layer` 结构带来的 representation-dependent
> recoverability gap，并不只存在于单一的 `qpe_style` 合成族，而是已经在
> `qpeinexact`、`ae`、`draper_qft_adder` 这 3 个额外公共 benchmark 正例上得到支持。

### 3.6 非 inverse `Fourier-layer` scaling

为了避免 `QFT + QFT^-1` 被解释成简单 inverse cancellation，又补了一条
非 inverse 的 Fourier/phase-polynomial family：

> `fourier_phase_sandwich = H · D^r · H`

其中 `D` 是重复的 commuting diagonal phase-polynomial layer。这个 family
没有 `U U^\dagger` 结构，核心考察的是：basis lowering 后局部 flat 表示
能否恢复中间 diagonal phase polynomial 的可聚合结构。

结果如下：

| Requested Gates | Actual Input Gates | qiskit opt3 | optimized UCC |
|---:|---:|---:|---:|
| `4,000` | `3,998` | `9,588` gates, depth `5,593`, cx `4,788`, `1.898s` | `42` gates, depth `24`, cx `12`, `3.164s` |
| `10,000` | `9,998` | `23,988` gates, depth `13,993`, cx `11,988`, `11.805s` | `42` gates, depth `24`, cx `12`, `14.621s` |
| `20,000` | `19,998` | `47,988` gates, depth `27,993`, cx `23,988`, `46.009s` | `42` gates, depth `24`, cx `12`, `55.843s` |
| `50,000` | `49,998` | timeout `>90s` | `42` gates, depth `24`, cx `12`, `20.129s` |
| `100,000` | `99,998` | timeout `>120s` | `42` gates, depth `24`, cx `12`, `27.064s` |

这组结果目前是最强的非 inverse phase-ladder/Fourier-layer 证据：

- `5/5` strict structural-quality win over `qiskit opt3`
- `50k/100k` 上同时形成 scalability win
- 输出门数、depth、`cx` 都稳定塌缩到常数规模
- **width 轴扩展**：在 $n=5$ 和 $n=6$ 的 width-axis sweep 中，`semantic_ucc` 的输出门数分别恒定为 `65` 和 `93` gates，准确验证了 $O(m)$ 的理论 scaling（其中 $m = n(n-1)/2$ 为 controlled-phase 项数）。
- 这不是 inverse cancellation，而是 commuting diagonal / phase-polynomial
  结构在 semantic representation 中可恢复、在 flat lowered path 中难以恢复

因此 PRX-style 主张现在可以从“主要依赖 `QFT + QFT^-1`”升级为：

> representation-dependent recoverability gap 已经在一个非 inverse
> Fourier/phase-polynomial family 上形成系统性 strict structural-quality
> separation，且在 width 轴上符合理论 $O(m)$ 预测。

### 3.7 Correctness Certificate (Unitary Equivalence)

为了确保 semantic Fourier 压缩没有牺牲电路正确性，对 $n=4, 5, 6$ 在不同尺寸 ($4k, 10k, 20k$) 和 Seed ($0-4$) 下进行了严格的 Unitary 等效性验证：

- **验证方法**：使用 Qiskit `Operator.equiv` 检查 `semantic_ucc` 输出与原始输入的等效性（允许 global phase）。
- **覆盖范围**：45 个 primary cases。
- **结果**：所有 45 个测试用例均通过验证（`is_equivalent=True`）。
- **结论**：Fourier 层语义压缩在实现常数级简化的同时，严格保持了电路的数学语义。

### 3.8 Seed Robustness (稳健性验证)

为了证明 $O(m)$ 压缩不是单一随机参数 Seed 的巧合，跨越 $n=4, 5, 6$ 进行多 Seed 稳健性实验：

- **实验配置**：$n \in \{4, 5, 6\}$，5 个随机 Seed ($0-4$)，3 种尺寸 ($4k, 10k, 20k$)。
- **核心证据**：对每个 $n$，`semantic_ucc` 的输出门数方差为 **0**。
  - $n=4$: 恒定 42 门
  - $n=5$: 恒定 65 门
  - $n=6$: 恒定 93 门
- **稳定性**：结果对重复次数 $r$ 和随机角度 Seed 均保持完全独立和稳定。

### 3.9 `mirrored / conjugation` 正例补充

为支撑第二条 `mirrored / conjugation` 理论线，又补了一组聚焦正例：

- `grover_real`
- `mqt_grover_8`
- `mqt_grover_12`
- `mqt_grover_16`
- `grover_mirrored_100k`

结果如下：

| Instance | baseline UCC | optimized UCC | qiskit opt3 |
|---|---:|---:|---:|
| `grover_real` | `287,047` gates, depth `152,298` | `79,029` gates, depth `54,163` | `79,029` gates, depth `54,163` |
| `mqt_grover_8` | `18,992` gates, depth `10,990` | `5,170` gates, depth `3,788` | `5,170` gates, depth `3,788` |
| `mqt_grover_12` | `259,797` gates, depth `150,911` | `71,706` gates, depth `55,801` | `71,706` gates, depth `55,801` |
| `mqt_grover_16` | `2,112,285` gates, depth `1,255,608` | `581,098` gates, depth `476,428` | `581,098` gates, depth `476,428` |
| `grover_mirrored_100k` | `4,122,006` gates, depth `2,166,021` | `1,158,011` gates, depth `762,010` | `1,158,011` gates, depth `762,010` |

这组结果的意义是：

- `grover_real` 说明官方真实 Grover-family 实例本身就是 clean positive case
- `mqt_grover_8/12/16` 说明 Grover-style positive case 不是单一 benchmark 尺度上的偶然
- `grover_mirrored_100k` 把同一条线扩展到大规模 repeated mirrored shell 结构

因此现在更稳的第二理论线叙事是：

> `mirrored / conjugation` 结构带来的 recoverability gap，也不再只是
> `hw_mqt_grover_20` 的 routed timeout-recovery 现象，而已经有一组 clean
> all-to-all / fixed-basis 正例在支持它。

### 3.8 `mirrored / conjugation` scaling 正例

为了让第二条理论线不只依赖离散正例，又补了一轮带 scaling 的正例实验。

第一组是公开 `MQT Bench` Grover scaling：

| Instance | baseline UCC | optimized UCC | qiskit opt3 |
|---|---:|---:|---:|
| `mqt_grover_8` | `18,992` gates, depth `10,990` | `5,170` gates, depth `3,788` | `5,170` gates, depth `3,788` |
| `mqt_grover_12` | `259,797` gates, depth `150,911` | `71,706` gates, depth `55,801` | `71,706` gates, depth `55,801` |
| `mqt_grover_16` | `2,112,285` gates, depth `1,255,608` | `581,098` gates, depth `476,428` | `581,098` gates, depth `476,428` |

第二组是 fixed-basis `grover_mirrored` repeated-shell scaling：

| Target Gates | baseline UCC | optimized UCC | qiskit opt3 |
|---:|---:|---:|---:|
| `10,000` | `412,206` gates, depth `216,621` | `115,811` gates, depth `76,210` | `115,811` gates, depth `76,210` |
| `20,000` | `824,406` gates, depth `433,221` | `231,611` gates, depth `152,410` | `231,611` gates, depth `152,410` |
| `50,000` | `2,061,006` gates, depth `1,083,021` | `579,011` gates, depth `381,010` | `579,011` gates, depth `381,010` |
| `100,000` | `4,122,006` gates, depth `2,166,021` | `1,158,011` gates, depth `762,010` | `1,158,011` gates, depth `762,010` |

这轮 scaling 的意义是：

- `mqt_grover_8/12/16` 说明公开 Grover-style family 随规模增大仍保持同一结论
- `grover_mirrored_10k/20k/50k/100k` 说明 repeated mirrored shell 的 recoverability gap 随 materialization 规模扩大稳定存在
- 第二条 `mirrored / conjugation` 理论线现在不仅有 clean positive cases，也有 scaling 支撑

## 4. 公共 benchmark source 2：SupermarQ

实例：

- `supermarq_hamiltonian_sim_8`
- `supermarq_mermin_bell_8`
- `supermarq_qaoa_vanilla_12`

### 4.1 代表性结论

- `supermarq_mermin_bell_8`
  - baseline UCC: `386` gates, depth `135`
  - optimized UCC: `76` gates, depth `44`
  - `qiskit opt3`: `76` gates, depth `44`

- `supermarq_qaoa_vanilla_12`
  - baseline UCC: `947` gates, depth `225`
  - optimized UCC: `222` gates, depth `80`
  - `qiskit opt3`: `222` gates, depth `80`

- `supermarq_hamiltonian_sim_8`
  - baseline UCC: `71` gates, depth `36`
  - optimized UCC: `51` gates, depth `24`
  - `qiskit opt3`: `51` gates, depth `24`

### 4.2 `SupermarQ` 总论

- 这组结果继续支持 representation-aware recovery 的主张：在多个公共 benchmark 上，semantic/controller 路径能修复 baseline UCC 的退化并恢复到 `qiskit opt3` 质量。
- 但也暴露边界：当前方法并不是每个 family 都优于强 Qiskit baseline。
- 因此目前最稳的论文口径不是“全面超过 Qiskit”，而是“representation choice 会造成可测的 recoverability gap；bounded semantic compilation 能在若干结构族和真实实例上关闭这个 gap”。

## 5. Hardware-aware 结果

固定后端：

- 20-qubit bidirectional line backend
- native operations: `u`, `sx`, `p`, `cx`, `measure`, `id`

实例：

- `hw_mqt_qpeexact_20`
- `hw_mqt_qaoa_20`
- `hw_mqt_grover_20`

### 5.1 `hw_mqt_qpeexact_20`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| qiskit opt3 | 1,572 | 407 | 812 | 0.056 s |
| baseline UCC | 1,976 | 648 | 1,350 | 0.174 s |
| optimized UCC | 1,572 | 407 | 812 | 0.269 s |

结论：

- optimized UCC 在当前 canonical fixed-seed 结果上与 `qiskit opt3`
  完全追平。
- 相比 baseline UCC，三项结构指标仍显著更好。
- 因此这条现在应表述为一个 clean parity case，而不是 routed-quality
  win。

### 5.2 `hw_mqt_qaoa_20`

| Method | Output Gates | Output Depth | CX Count | Runtime |
|---|---:|---:|---:|---:|
| qiskit opt3 | 2,091 | 532 | 1,530 | 0.078 s |
| baseline UCC | 2,057 | 513 | 1,503 | 0.141 s |
| optimized UCC | 2,050 | 487 | 1,458 | 0.157 s |

结论：

- optimized UCC 在 **总门数、深度、CX 数** 三项上都优于 `qiskit opt3`。
- 这是当前最明确的 hardware-aware external-baseline win。
- 相比 baseline UCC，optimized UCC 在总门数、深度和 CX 数三项上都更好。
- 当前 canonical runtime 为 `0.157 s`。

### 5.3 `hw_mqt_grover_20`

- `qiskit opt3` 与 baseline UCC 仍然在当前 timeout 设置下超时。
- optimized UCC 现在可以在 `2.146 s` 内返回结果。
- 当前 stronger mirrored/self-inverse repeated-run candidate 虽然仍然很大，但已经把输出进一步压到了 `6,467,857` gates、`4,094,196` depth、`3,045,048` `cx`，比此前 fallback 的总门数、深度和 `cx` 都更低。
- 因此这条仍然更适合作为“robustness / timeout recovery”证据，而不是主质量对比图。

### 5.4 Hardware-aware 总论

当前 hardware-aware 结果表明：

- 我们的工作不只是“追平 Qiskit 输出质量”；
- 在一个公开 hardware-aware case（`hw_mqt_qaoa_20`）上，已经取得
  固定-seed 的明确胜场；
- 在另一个 case（`hw_mqt_qpeexact_20`）上，已达到与 `qiskit opt3`
  的固定-seed parity；
- 并且在 `hw_mqt_grover_20` 上，optimized UCC 还修复了原先的 timeout 问题；
- 这使得当前工作从“只修 UCC 退化”进一步提升到“在部分 routed case 上可超过 `qiskit opt3`，并在更难 case 上提供 robustness”。

## 6. Runtime 结论

runtime profiling 的主结论如下：

### 6.1 all-to-all 路径

对于：

- `phase_estimation_real`
- `grover_real`
- `qaoa_real`

当前 optimized 分支的 runtime 已经与 `qiskit opt3` 接近。主要原因是：

- qiskit-source direct fast path
- source-level short-circuiting

已经把早期分支中的额外 wrapper overhead 明显压掉。

### 6.2 backend-aware 路径

backend-aware 剩余 runtime gap 主要来自：

- backend candidate search
- direct backend reference probe
- seed portfolio

当前又做了一轮 pruning：

- 当 base backend-aware candidate 只比 cheap baseline 小幅更优时，直接返回，不再额外跑 direct backend `qiskit opt3`。
- 当 direct backend `qiskit opt3` 已明显支配 base candidate 时，直接返回它，不再扩 seed portfolio。
- 当 canonical direct reference 和 base candidate 不能分出胜负时，再扩小型 exploratory seed set。
- 对 `hw_mqt_grover_20` 这类 dominant repeated composite-run，增加 repeated-run backend fallback。

结果：

- `hw_mqt_qpeexact_20`：当前是固定-seed parity，runtime `0.269 s`
- `hw_mqt_qaoa_20`：quality win 保持，当前 runtime `0.157 s`
- `hw_mqt_grover_20`：optimized UCC 不再 timeout，当前 runtime `2.146 s`，且 stronger mirrored/self-inverse fallback 进一步降低了 routed total gates / depth / `cx`

## 7. 当前最稳的实验结论

当前最稳的、最适合对外表述的结论是：

1. baseline UCC 的结构化退化是真实存在的。
2. 这种退化不能仅用“简单 UCCDefaults 顺序修复”完全解释。
3. 在官方真实实例上，optimized UCC 已能稳定追平 `qiskit opt3` 的输出质量。
4. 在两个公共 benchmark source（`MQT Bench`、`SupermarQ`）上，optimized UCC 继续支持 phase-ladder 与 mirrored/conjugation 两条 recoverability-gap 线。
5. `QFT + QFT^-1` external scaling 现在给出一个系统性 family-level runtime/scalability 胜场。
6. 在至少一个 hardware-aware 公共 benchmark（`hw_mqt_qaoa_20`）上，optimized UCC 取得了相对于 `qiskit opt3` 的明确 fixed-instance external-baseline win，而 `hw_mqt_qpeexact_20` 则达到固定-seed parity。
7. runtime 方面，all-to-all 已接近或达到 `qiskit opt3` 的同量级，backend-aware 路径也经过剪枝显著缩小了差距。

## 8. 对论文和立项的含义

### 对论文

这组结果支持把论文写成：

- representation-dependent recoverability gap 的理论驱动编译论文
- bounded semantic term algebra / dispatch controller 在 UCC 中的实例化
- phase-ladder 与 mirrored/conjugation 两条结构族的理论和实验支撑
- 至少一个系统性 family-level runtime/scalability win，以及一个稳定 hardware-aware fixed-instance win

这比“玩具结构消除例子”或“只改 pass 顺序”的故事更强。

### 对 grant / 立项

这组结果也足以支持把项目立成：

- UCC 中 representation-aware semantic compilation 的工程化
- recoverability-gap benchmark / artifact project
- bounded term algebra、dispatch controller、cache/reuse、backend-aware selection 的上游候选方案

而不是“一个全新独立 pass”的狭义提案。

## 9. 当前工作区推荐查看顺序

如果要快速理解整篇工作，建议按这个顺序看：

1. `quantum_paper_draft.md`
2. `experiment_results_overview_cn.md`（本文档）
3. `real_instance_results_summary.md`
4. `hardware_aware_results_summary.md`
5. `runtime_optimization_progress.md`

如果只看一句结论：

> 当前结果支持一个更理论化的结论：basis lowering 会造成 representation-dependent recoverability gap；bounded semantic term controller 能在 UCC 中关闭部分结构族的 gap，表现为 `QFT + QFT^-1` 的系统性 runtime/scalability 胜场、多个真实/公共 benchmark 的 `qiskit opt3` quality recovery，以及 `hw_mqt_qaoa_20` 的稳定 hardware-aware fixed-instance 胜场。
