# 冲击 PRX Quantum 的实验清单

## 目标

这份清单用于评估：如果想把当前这条 UCC 优化工作推进到
**PRX Quantum** 的标准，实验和技术层面还差什么。

这条线的要求显著高于 `Quantum (Journal)`。

PRX 真正要求的不是：

- “实验做得不错”

而是更接近：

- 更强的新意
- 更广的影响力
- 更有说服力的强基线胜场
- 更一般性的科学结论

## 当前判断

当前工作 **还不具备 PRX-ready 的实验基础**。

目前最强、最稳的定位是：

- 一篇 UCC 相关的编译系统优化研究
- 清楚展示了 pipeline placement 的重要性
- 说明了有界的 basis lowering 前结构化预处理能修掉严重退化，并恢复强基线质量

这已经是有价值的工作，但它仍然更像：

- 强系统 / 软件优化论文

而不是：

- 具有领域级冲击力的 PRX 论文

## PRX 还需要的东西

### 1. 比“改进 UCC”更强的科学主张

原因：

- PRX 不会因为“某个开源编译器变好了”就轻易买单

需要升级的方向：

- 把问题提升成更一般的量子编译原理问题，例如：
  - basis lowering 何时会不可逆地破坏结构
  - pre-basis simplification 何时具有结构性优势
  - 哪些线路族在 lowering 前后存在可证明的优化差距

完成标准：

- 核心结论看起来像“量子编译的一般性原理”，而不是“UCC 的一个补丁”

### 2. 更广的编译器比较

原因：

- PRX 级实验不能停留在 “baseline UCC vs optimized UCC vs Qiskit”

最低要求：

- `Qiskit`
- `TKET`（如果能稳定跑）
- 至少再加一个相关的编译 / 综合 baseline
  - 例如在适合的设置下加 BQSKit 类参考

完成标准：

- 主表中存在清晰的 cross-compiler comparison，而不只是 UCC 内部比较

### 3. 更广的真实 benchmark 语料

原因：

- 3 个官方 Qiskit 实例对 PRX 来说远远不够

需要扩展：

- 公共 benchmark suite
  - `MQT Bench`
  - `SupermarQ`
  - 必要时再考虑 `QASMBench`
- 更多真实算法族
  - phase-estimation 变体
  - amplitude-estimation / amplification
  - 多种 QAOA 图族
  - 更多 mirrored / structured search circuits

完成标准：

- 论文的 benchmark 语料来自多个公共来源，而不是只靠内部挑选

### 4. 对强外部基线的清晰胜场

原因：

- “追平 `qiskit opt3`” 对系统论文很好
- 但对 PRX 来说通常还不够

需要的结果形态：

- 在多个真实 workload 家族上，明确优于强基线，至少在一个关键指标上胜出：
  - gate count
  - depth
  - 2Q gate count
  - 在相同质量下的 runtime

完成标准：

- 主结果表里不只是 parity，而是有反复出现的 clear wins

### 5. backend-aware / architecture-aware 研究

原因：

- PRX 更希望看到与真实硬件、更真实编译约束的关联

需要补的内容：

- 多个 backend-aware target
- coupling maps 或 native-gate constraints
- routed circuit 的 2Q 指标比较

完成标准：

- 论文中至少有一部分实验明确超越“抽象固定门集”层面

### 6. 更强的 scaling 证据

原因：

- 当前 scaling 很有用，但对 PRX 还不够厚

需要：

- 用最新优化分支刷新 scaling
- 尽可能覆盖更大规模
- 对关键 workload 做重复计时和方差统计

完成标准：

- scaling 结论稳定、清晰、可复现，而不是若干孤立点

### 7. 更明确的理论部分

原因：

- PRX 级稿件通常需要更一般的理论支撑，而不仅仅是经验 heuristics

可以考虑的方向：

- 形式化分类：哪些线路族存在 pre-basis simplification 优势
- 给出 lowering 前后结构丢失的充分条件
- 对 preprocessing 和 placement gap 给出更清楚的复杂度 / 结构性讨论

完成标准：

- 论文不仅是经验规律，还包含一个更一般的理论视角

## 具体实验任务

### 必做

1. 用最新代码刷新所有旧表
2. 增加至少一个公共 benchmark suite
3. 增加至少一个新的外部编译器 baseline
4. 增加 hardware-aware 实验
5. 在真实 workload 上拿到至少一个清晰外部基线胜场

### 强烈建议

6. 对 headline result 做重复计时和方差统计
7. 把真实实例扩展到不止 3 个 Qiskit-library case
8. 增加一节由理论问题驱动的实验分析

## 不要误判成“已经接近 PRX”的事情

下面这些事情都重要，但**单独完成它们并不能让你接近 PRX**：

- 只润色 prose
- 再加一些 synthetic stress tests
- 单纯把 UCC 代码写得更干净
- 只证明 “UCC 不再严重退化”

它们都是必要但不充分的。

## 最终就绪标准

只有当以下大部分条件都满足时，才算真正接近 **PRX Quantum**：

- 主张能泛化到 UCC 之外
- benchmark 语料广且公开
- 在真实 workload 上反复赢过强外部基线
- 有 hardware-aware 证据
- scaling 和方差统计完善
- 同时存在一个更一般的理论结论

在这些条件没满足之前，这项工作更适合视为：

- ACM TQC 级别
- IEEE TQE 级别
- 或者在完成较窄清单后冲击 Quantum
