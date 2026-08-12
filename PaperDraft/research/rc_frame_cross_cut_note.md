# V2 验证 Note:RC Pauli frame 是否可被局部消解(frame = cross-cut state 的成立条件)

日期:2026-08-05 · 任务编号:执行方案 V2(单点故障闸门) · 状态:**通过,附作用域精化**

---

## 0. 裁决(一段话)

**通过,但需精化表述。** "frame 可被逐轮清算"这一威胁是真实存在的——在编译期 RC(Wallman–Emerson 原始形式及全部主流实践变体)中 frame 确实被就地折叠、发射流中不存在持久 frame 对象。但清算**不消灭信息,只改变寄存器**:被清算的符号成为发射流中带符号残差的一部分,fooling 论证对带符号聚合类计数,该计数在符号归一化双射下不变,故 $S\ge m\log_2 K_\epsilon$ 的下界**对两种实现模式均逐字成立**。真正需要修改的只是摘要中"$S$ *就是* Pauli frame"的字面认定:它在 **frame-tracked(延迟修正)模式**下字面成立,在编译期 RC 下应改述为"frame 的信息内容以符号位形式存在于穿越 cut 的快照中"。摘要已相应加 "frame-tracked" 限定词。

## 1. 问题与判据

原始威胁(执行方案 V2 / 原注释第七节第 2 项):若 twirl Pauli 被编译进后续 Clifford 层"就地抵消",则发射流中无 frame 对象,Proposition (Frame = cross-cut state) 的 $S\supseteq$ frame 认定可能落空,连带摘要 GATED CLAIM 与 E6 的 twirl 熵论证。

通过判据:能写出 Proposition 的完整证明草稿,并对 (a) Wallman–Emerson 原始形式、(b) 实践变体各给出"为何不能免费清算"的论证或明确适用条件。两项均已完成,见 §3–§4。

## 2. 机制核查

### (a) Wallman–Emerson 原始形式(编译期 RC)

Wallman & Emerson, PRA **94**, 052325 (2016):电路分解为交替的 easy(单比特/Clifford)与 hard 周期;随机 twirl 算子 $T_k$ 与其修正 $T_{k}^{c}$ 被**编译进相邻 easy 周期**,不增加深度、不留运行时对象。对 $R_{P_j}(\theta)$,twirl 的净效应是符号翻转 $\theta\mapsto s_j^{(t)}\theta$($X R_Z(\theta) X=R_Z(-\theta)$)。

**结论:frame 在语法上确实被消解。** 发射的每个随机化实例是一条自含的 Clifford+旋转流,符号 $s_j^{(t)}$ 只能从上下文的 dressing Clifford 中恢复。但信息未消失——见 §3。

### (b) Frame-tracked 架构(延迟修正)

Riesebos, Fu, Varsamopoulos, Almudever & Bertels, *Pauli Frames for Quantum Computer Architectures*, DAC 2017 (doi:10.1145/3061639.3062300);概念源头 Knill, Nature **434**, 39 (2005)。要点:

- Pauli 修正**不物理施加**,以经典寄存器(全体 qubit 的 Pauli record = frame)在控制栈中持续跟踪;Clifford 门下 frame 按共轭规则更新;
- **关键确认**:非 Clifford 门(即我们的 $R_{P_j}$ 旋转)执行前,目标 qubit 的 Pauli record **必须 flush**——或物理施加,或折叠进旋转角(符号翻转)。

**结论:两种子模式,信息去向不同但都被收账。**
- 修正跨 cut 延迟(测量前统一结算):frame 是 cut 时刻控制栈中的活经典寄存器,按 `def:compiler` 的 $\mathsf{ser}_{\mathrm{store}}$ 字段**字面地**被序列化收费——"$S$ 包含 frame"字面成立;
- 逐轮 flush:flush 动作把 generator $j$ 的 frame 位折叠进第 $t$ 轮旋转符号,信息转入带符号残差,归入 (a) 的情形。

### (c) 实践变体(IBM / Berkeley-AQT / True-Q)

- Hashim et al., PRX **11**, 041039 (2021)(Berkeley AQT + Quantum Benchmark):twirl 门在 **transpile 期**折叠进 easy 周期(常为 virtual gate),属编译期模式 (a);
- IBM 错误缓解管线(如 van den Berg et al., Nat. Phys. **19**, 1116 (2023) 的稀疏 Pauli–Lindblad PEC;qiskit-ibm-runtime 的 twirling 选项):Pauli twirl 同样在提交前折叠进电路,属模式 (a);
- FT 控制栈(表面码解码器 + frame 单元,如 Riesebos 的 SC17 仿真):属模式 (b)。

**没有发现第三种模式**(即既不留寄存器、又不把符号写进发射流的实现——这在信息论上也不可能,否则语义就错了)。

## 3. 核心论证:清算 = 换寄存器搬运,不 = 免费

威胁的隐含假设是"局部抵消把符号信息变没了"。反驳分三步,全部用论文现有装置:

**(i) 局部抵消是前缀内计算,不减 cut 计数。** 把 $X\,R_Z(\theta)\,X\to R_Z(-\theta)$ 这类改写看作 Alice(`thm:main-tradeoff` 证明中的前缀方)在 cut 前的本地预处理。fooling 论证的计数对象是**前缀等价类**:两条前缀若存在某个后缀补全使总聚合不同,则 crossing 快照必须不同(否则 Bob 恢复出的计算完全一致,与 `lem:nearest-decoder` 的区分要求矛盾)。符号归一化 $a\mapsto s\cdot a$ 是 $\mathbb{Z}_Q$ 上的双射,**不改变可达带符号部分和类的个数** $Q^m$。故无论 Alice 是否先"清算",$B_{\mathrm{cut}}\ge m\log_2 Q - (\text{compact output 松弛})$ 不变。

**(ii) 逐轮 flush 的决策依赖 frame,故快照必须决定 frame 作用。** 在模式 (b) 的逐轮 flush 子情形,cut 之后各轮的 flush 结果(旋转符号)是 cut 时刻 frame 状态的函数。取两条前缀:无符号残差全同、仅 generator $j$ 的待决 frame 不同。任选后缀在 $P_j$ 上施加残差 $a\neq 0$($Q>2$ 时可再取 $a\neq -a$),两条运行的总聚合相差 $2a\not\equiv 0 \pmod Q$,由 `prop:epsilon-packing` 的分离度 $\ge 4\epsilon$,$\epsilon$-正确编译器必须区分——快照必须决定 frame 在全部 $m$ 个 generator 上的作用,即 $\ge m$ 比特。

**(iii) 种子压缩攻击被作用域声明关闭。** 若下游编译器知道上游 RC 的 PRNG 种子,可用 $O(|\text{seed}|)$ 比特再生全部符号。但这等价于看见 RC 之前的信息,恰好违反 T4 作用域 Remark 的前提("downstream of randomization");且确定性 fooling 版(Theorem 2 型)由对抗调度取证,与符号来源是否伪随机无关。此攻击应在 T4 中明写为反例说明作用域必要性。

## 4. Proposition 草稿(供 T3 直接采用)

> **Proposition (Frame as cross-cut state).**
> Let a scheduled phase-accumulation stream over generators $P_1,\dots,P_m$ with grid $\mathbb{Z}_Q$ be processed under randomized compiling, and let $\mathcal{A}$ be any (randomized) compiler that is $\epsilon$-correct on every valid schedule with probability $\ge 1-\delta$ and whose final output is family-relative compact. Fix any inter-round cut $c$ and let $\mathsf{ser}(c)$ be the five-field restart snapshot of Definition [def:compiler]. Then:
> **(i) (both modes)** $\mathsf{ser}(c)$ determines the signed partial-aggregate class of the prefix; hence $\overline B_{\mathrm{pre}}^{\mathrm{rel}} + \overline B_{\mathrm{cut}} \ge (1-\delta)\,m\log_2 K_\epsilon - h_2(\delta)$, exactly as in Theorem [thm:main-tradeoff], applied verbatim.
> **(ii) (frame-tracked mode)** If Pauli corrections are deferred across $c$ (frame tracking in the classical control stack), then $\mathsf{ser}_{\mathrm{store}}(c)$ determines the action of the pending Pauli frame on all $m$ generators, and therefore contains a sub-register of at least $m$ bits identifiable with the frame itself.
> **(iii) (compile-time mode)** If the frame is flushed before $c$ (twirls folded into easy cycles at transpile time), the same $m$ bits appear instead as the sign components of the signed residues carried in $\mathsf{ser}_{\mathrm{parameter}}/\mathsf{ser}_{\mathrm{store}}$; the bound in (i) is unchanged.
>
> *Proof draft.* (i): Sign normalization is a bijection on $\mathbb{Z}_Q$ residues, so the number of reachable signed prefix classes equals $Q^m$ (V1 enumeration confirms prefix-freeness of the aggregate for $r\ge 2$); the one-way simulation of Theorem [thm:main-tradeoff] then applies with Alice performing any local clearing before serializing, which cannot merge two classes separated by a suffix completion, by Lemma [lem:nearest-decoder] and Proposition [prop:epsilon-packing]. (ii): For two prefixes with identical unsigned residues and frames differing on generator $j$, complete with a suffix applying residue $a\notin\{0,-a\}$ on $P_j$; totals differ by $2a\bmod Q\neq 0$, separated by $\ge 4\epsilon$, so the snapshots must differ; ranging over $j$ gives $m$ independent distinguishing coordinates, all resident in classical control state, i.e.\ $\mathsf{ser}_{\mathrm{store}}$. (iii): Immediate from (i) after noting the flush map is measurable from the prefix and injective on sign components. $\square$

配套的 Fano/twirl 熵推广(E6 理论配套):把 `thm:main-tradeoff` 随机版证明中的条件熵项换成 $H(\text{frame}\mid\text{unsigned stream}) = \eta m$(twirl 强度 $\eta$ 下每 generator 每轮独立翻转),得 $A_p+(2p-1)S \gtrsim \eta\,m\log_2 K_\epsilon - O(\log m)$。风险低:仅替换熵源,不动打包与解码器。

## 5. 已考虑并关闭的攻击

| 攻击 | 关闭方式 |
|---|---|
| 局部共轭抵消($XR_ZX\to R_Z^{-}$) | §3(i):前缀内双射,不减类数 |
| 逐轮物理 flush(Riesebos 语义) | §3(ii):flush 决策函数依赖 frame,快照必须决定之 |
| PRNG 种子再生符号 | §3(iii):违反 downstream 作用域;确定性版对抗取证免疫 |
| twirl 进入后续 easy 层被吸收 | 即模式 (a):吸收后符号在 dressing Clifford 中,仍是发射流的带符号内容 |

旁证:arXiv:2607.26756(*Randomized Compiling Does Not Destroy Coherent-Error Information*)在噪声表征语境下独立支持"RC 不消灭信息、只重定位信息"的直觉(仅作方向性引用,未依赖其结论)。

## 6. 对正文的影响

1. **摘要 GATED CLAIM [V2/T3]**:句子限定为 "Under **frame-tracked** randomized compiling the state $S$ is the Pauli frame itself"(已改);编译期 RC 情形由 Proposition (iii) 覆盖,正文 T3 小节陈述两模式。闸门在 T3 落入正文后解除。
2. **T3**:直接采用 §4 的 Proposition 三段式;Physical instantiation (c) 分 (c-tracked) 与 (c-folded) 两条。
3. **T4 作用域 Remark**:补一句种子攻击反例(§3(iii))作为"downstream 前提必要"的论证。
4. **E6**:twirl 熵推广按 §4 末段执行,无额外风险。

## 7. 文献定位

- Wallman & Emerson, *Noise tailoring for scalable quantum computation via randomized compiling*, [PRA 94, 052325 (2016)](https://doi.org/10.1103/PhysRevA.94.052325) — 原始形式;twirl 编译进 easy 周期。
- Hashim et al., *Randomized Compiling for Scalable Quantum Computing on a Noisy Superconducting Quantum Processor*, [PRX 11, 041039 (2021)](https://journals.aps.org/prx/abstract/10.1103/PhysRevX.11.041039) / [arXiv:2010.00215](https://arxiv.org/abs/2010.00215) — 实践确认 transpile 期折叠、virtual gate 实现。
- Riesebos et al., *Pauli Frames for Quantum Computer Architectures*, [DAC 2017](https://dl.acm.org/doi/abs/10.1145/3061639.3062300) — frame 为控制栈经典寄存器;**非 Clifford 门前必须 flush**(§2(b) 的关键机制来源)。
- Knill, *Quantum computing with realistically noisy devices*, Nature 434, 39 (2005) — frame 概念源头。
- van den Berg et al., *Probabilistic error cancellation with sparse Pauli–Lindblad models*, Nat. Phys. 19, 1116 (2023) — IBM 实践中 twirl 的编译期折叠。
- [AQT Randomized Compiling 页面](https://aqt.lbl.gov/aqt-research/quantum-computation-simulation/randomized-compiling/) — 实现描述。
- 旁证:[arXiv:2607.26756](https://arxiv.org/html/2607.26756) — RC 不消灭相干误差信息。
