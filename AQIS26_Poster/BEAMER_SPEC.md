# Beamer 施工规范：Representation as a Computational Resource in Quantum Compilation

> **给 Claude Code 的任务**：按本文件生成一份可编译的 Beamer 演示文稿（组会 report，同时作为 AQIS 2026 poster session 的预演）。
>
> **绝对要求：正文（Part I–Part VI）必须严格按本文件 §0 → §5 的顺序排布，不得重排、合并或调整节的先后。** 附录部分（Part VII）位于 §5 之后，是 backup，不参与主线顺序。

---

## 0. 全局技术要求

### 0.1 文件与编译

- 输出单文件 `main.tex`，用 `xelatex` 编译（若需中文 speaker notes）。
- 若 speaker notes 中的中文导致编译问题，改用 `\usepackage{ctex}` 并保持 `xelatex`。
- 导言区必须包含：

```latex
\documentclass[aspectratio=169,10pt]{beamer}
\usetheme{metropolis}          % 若不可用，退回 \usetheme{default} + 简洁配色
\usepackage{amsmath,amssymb,amsthm,mathtools}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,calc,decorations.pathreplacing,patterns}
\usepackage{booktabs}
\usepackage{xcolor}
\setbeamertemplate{navigation symbols}{}
\setbeamertemplate{caption}[numbered]
```

### 0.2 语言策略

- **幻灯片正文用英文**（与论文/海报一致，可直接复用于 AQIS）。
- **每一帧附中文 speaker note**，用 `\note{...}`，内容取自本文件各帧的「讲台提示」。
- 若需要中文正文版，只需把各帧标题与正文替换为本文件括注的中文说明；请把这个开关做成导言区的一个布尔宏 `\newif\ifzh \zhfalse`。

### 0.3 定理环境

必须定义并使用，编号连续：

```latex
\newtheorem{claim}{Claim}
\newtheorem{lemma2}{Lemma}     % 若主题已占用 lemma，用别名
\theoremstyle{definition}
\newtheorem{defn}{Definition}
\newtheorem{remark2}{Remark}
```

统一记号宏（必须定义，全文只用这些）：

```latex
\newcommand{\dproj}{d_{\mathrm{proj}}}
\newcommand{\op}{\mathrm{op}}
\newcommand{\Fb}{\mathbb{F}_2}
\newcommand{\ZQ}{\mathbb{Z}_Q}
\newcommand{\cd}[1]{\langle\!\langle #1 \rangle\!\rangle}   % 圆周距离
\newcommand{\Bcut}{B_{\mathrm{cut}}}
\newcommand{\Ldelta}{L_\delta(m,K)}
\newcommand{\hbin}{h_2}
```

### 0.4 视觉与节奏

- **一帧一个 message**。禁止一帧塞两个定理。
- 关键常数、关键假设用 `\alert{}` 高亮。
- 凡本文件标注「⚑ 必答」的内容，做成 `\begin{block}{}...\end{block}` 或带边框的 callout，视觉上区别于正文。
- 用 `\pause` 或 `\onslide` 做逐步揭示，但**每帧不超过 3 个 pause**。
- 结构帧：在每个 Part 开始处插入 `\section{}` 并启用 `\AtBeginSection` 输出一页 outline（当前节高亮）。

### 0.5 目标页数

正文 28–34 帧，附录 8–12 帧。若超出，优先压缩 §0（术语）而非 §4（下界）。

---

# Part I —— §0 术语与工具字典

**本 Part 的作用**：让不熟悉容错量子编译的听众在 5 分钟内具备听懂 §1–§5 的最小词汇量。**这是唯一可以在时间紧张时压缩的 Part。**

## Frame 0.1 — Title page

- 标题：`Representation as a Computational Resource in Quantum Compilation`
- 副标题：`Approximate recoverability tradeoffs and model-specific fault-tolerant consequences`
- 作者：`Jinze Yang${}^1$ \quad Yangyang Li${}^1$ \quad Xiu-Hao Deng${}^{2,3}$`
- 单位脚注：`${}^1$ Xidian University \quad ${}^2$ Shenzhen International Quantum Academy \quad ${}^3$ Hefei National Laboratory`
- 日期：`Group seminar — AQIS 2026 poster session rehearsal`

## Frame 0.2 — One-slide thesis

用一个居中的 block 放这三行，不加任何其他内容：

> Fault-tolerant compilation **deliberately destroys structure**.
>
> Putting it back together has a price, payable in **exactly two currencies**:
> **bits of compiler state**, or **magic states**.
>
> Design rule with a proof: **randomize and lower late.**

**⚑ 讲台提示（note）**：这一页是全场的锚。Q&A 被打乱时随时回到这三行。

## Frame 0.3 — Qubits, unitaries, and $Z$-type characters

内容（分栏，左公式右解释）：

- State space $\mathbb{C}^{2^n}$, computational basis $|z\rangle$, $z\in\Fb^n$. Every gate is a $2^n\times2^n$ unitary; a circuit is a product of unitaries.
- For $a\in\Fb^n$: $Z^a:=Z^{a_1}\otimes\cdots\otimes Z^{a_n}$ is **diagonal**, and
$$Z^a|z\rangle=(-1)^{a\cdot z}|z\rangle=:\chi_a(z)|z\rangle,\qquad a\cdot z=\textstyle\sum_i a_iz_i \bmod 2.$$
- $\chi_a:\Fb^n\to\{\pm1\}$ is the **character** of $a$: a homomorphism from the additive group $\Fb^n$ to $\{\pm1\}$.

**加一个 callout**：`This is the only "group theory" in the talk. "$a_j$ linearly independent" will become "the characters jointly realize every sign pattern."`

## Frame 0.4 — Rotations, and why phase layers aggregate

- For Hermitian $P$ with $P^2=I$:
$$R_P(\theta):=e^{-i\theta P/2}=\cos(\theta/2)I-i\sin(\theta/2)P.$$
（注明推导：幂级数展开，用 $P^2=I$ 把偶次项收成 $\cos$、奇次项收成 $\sin$。）
- All $Z^a$ are diagonal $\Rightarrow$ pairwise commuting $\Rightarrow$
$$\alert{\prod_j R_{P_j}(\theta_j)=\exp\Big(-\tfrac i2\sum_j\theta_jP_j\Big)}.$$

**⚑ 必答 callout（本帧最重要）**：
> This is the physical premise of the whole paper. Commutation is what makes "add the coefficients across rounds" a legal simplification. Insert a non-commuting layer (the $R_X$ layers of a generic Trotter step) and the exponents no longer add — **the aggregate does not exist at all.**

**中文 note**：这一句是后面回答"假设太强"的伏笔，一定要在这里就埋下。

## Frame 0.5 — Clifford cheap, $T$ expensive: the economics

用两列对照：

**Clifford group** = the *normalizer* of the Pauli group: $C$ is Clifford iff $C^\dagger PC$ is again a Pauli (up to sign) for every Pauli $P$. Examples: $H,S,\mathrm{CNOT}$. Intuition: Clifford gates only move Paulis to Paulis, so their effect on Pauli errors is trackable with classical bits.

**Cost hierarchy**（做成一个 4 行的小 table 或 itemize）:

| Object | Meaning | Cost |
|---|---|---|
| logical qubit | surface code, $O(d^2)$ physical qubits, code distance $d$ | hundreds–thousands of physical qubits |
| Clifford gate | implementable fault-tolerantly by the code itself | ~free |
| $T=\mathrm{diag}(1,e^{i\pi/4})$ | needs a **magic state** $\lvert T\rangle$ | must be **distilled** in a dedicated **factory** |
| $T$-count | — | \alert{the unit of account of FT computation} |

**中文 note**：把"magic state / distillation / factory / code distance"四个词一次讲完，后面 §2 和 §5 就不必再解释。听众只需接受一句：$T$ 门是唯一真正花钱的门。

## Frame 0.6 — Three mechanisms that disperse an angle

三条 itemize，每条一行，右侧配一个极简示意（可用 TikZ 三个小方块）：

1. **Scheduling.** Time-dependent / variational layers split one accumulated phase across $r$ rounds.
2. **Synthesis (Ross–Selinger).** An angle becomes a Clifford+$T$ **word** in which no single letter carries the angle. Typical $T$-count $=3\log_2(1/\varepsilon)+O(\log\log(1/\varepsilon))$.
3. **Randomized compiling (twirling).** Each rotation is multiplied by a random sign $s\in\{\pm1\}$ with Pauli compensation, so coherent noise averages into Pauli noise. Two presentations:
   - **folded**: sign absorbed at emission, $a\mapsto sa \bmod Q$;
   - **tracked**: signs live in a classical **Pauli frame** register carried by the control stack.

**⚑ 必答 callout**：
> The bound is carried by the **schedule alone**. Sign normalization is a bijection of the residue alphabet, so the standard **folded (compile-time)** presentation inherits the bound verbatim. **Nothing depends on tracking Pauli frames.**

**中文 note**：这句话背熟。"你是在说 randomized compiling 不好吗"这个问题的答案就是它。

## Frame 0.7 — Where the compiler sits: downstream

一个从左到右的流水线 TikZ 图：

```
high-level circuit  →  schedule  →  twirl  →  lower  ──┤ cut ├──►  DOWNSTREAM COMPILER  →  synthesis  →  QRE
                                                        ↑
                                    upstream context is NOT available here
```

三个真实例子（itemize）：
- a cloud transpiler receiving a flat QASM/QIR program without the user's high-level intent;
- a real-time stream optimizer inside the classical control stack;
- a vendor-side pass post-processing an already emitted instruction stream.

**⚑ callout**：`If the compiler can see the circuit before randomization and lowering, the theorems do not apply — and that boundary is itself the content of the design rule.`

**中文 note**：先把这个位置立牢，否则后面所有质疑都会退化成"我为什么不能看上游"。

## Frame 0.8 — Also worth knowing (rapid fire)

一页扫过，每条一行，不展开：

- **fidelity** — a closeness measure for states/operations; *not used here*, we use operator-norm distances because they satisfy the triangle inequality (needed for packing arguments).
- **oracle** — a black-box subroutine charged per call; appears only in scope statements ("an uncharged random-access input oracle would be a different model").
- **FPGA / control stack** — the classical electronics adjacent to the chip must resolve corrections **before the next non-Clifford operation**, under hard latency and buffer budgets. \alert{This is why the bounded-memory streaming model is an engineering constraint, not a mathematical convenience.}
- **spacetime volume** — physical qubits $\times$ time (qubit-seconds).
- **QRE** — quantum resource estimator: logical circuit + architecture assumptions $\mapsto$ $T$ count, physical qubits, cycles, factories.
- **lowering / IR / transpiler** — lowering produces a **flat instruction stream**; the graph/table the compiler keeps internally is the **IR**.
- **QAOA cost layer** — $e^{-i\gamma C}$, $C=\sum_j w_jZ_{u_j}Z_{v_j}$: one $R_{ZZ}$ per edge.

## Frame 0.9 — Mathematical toolkit (1/2): circle distance

$$\cd{u}:=\min_{k\in\mathbb{Z}}|u-2\pi k|\in[0,\pi],\qquad d_\circ(\alpha,\beta):=\cd{\alpha-\beta}.$$

$d_\circ$ is a metric on $\mathbb{R}/2\pi\mathbb{Z}$ (triangle inequality holds). The identity used throughout:

$$\boxed{\ |e^{iu}-1|=2\sin\big(\cd{u}/2\big).\ }\tag{0.1}$$

**verification（放小字）**: $|e^{iu}-1|=2|\sin(u/2)|$; for $u\in[0,\pi]$, $\cd u=u$; for $u\in[\pi,2\pi]$, $\cd u=2\pi-u$ and $2\sin(\frac{2\pi-u}2)=2\sin(\pi-\frac u2)=2\sin\frac u2$.

## Frame 0.10 — Mathematical toolkit (2/2): four information-theoretic facts

**Prefix-free code**: no codeword is a prefix of another; concatenations are uniquely parseable without out-of-band lengths. All five serialization fields of the model are such codes.

**Fact K (Kraft).** $\sum_i2^{-\ell_i}\le1$, hence
$$N\cdot2^{-\max_i\ell_i}\le1\ \Longrightarrow\ \max_i\ell_i\ge\log_2N.$$
*Proof (one line):* map codeword $w$ to the dyadic interval $I_w=[0.w,\,0.w+2^{-|w|})$; $w$ is a prefix of $w'$ iff $I_{w'}\subseteq I_w$; prefix-freeness $\Rightarrow$ the $I_i$ are pairwise disjoint $\Rightarrow\sum2^{-\ell_i}=\sum|I_i|\le1$. $\qed$

**Fact S (Shannon).** Any prefix-free code satisfies $\mathbb{E}|E(X)|\ge H(X)$.

**Fact F (Fano).** If $\hat X=f(Y)$ and $\Pr[\hat X\ne X]\le\delta$, then
$$H(X\mid Y)\le \hbin(\delta)+\delta\log_2(|\mathcal X|-1).$$
*Intuition (this is the proof skeleton):* given $Y$, to finish describing $X$ you need only say (i) did the guess fail — $\hbin(\delta)$ bits; (ii) if so, which of the other $|\mathcal X|-1$ values — on average $\delta\log_2(|\mathcal X|-1)$ bits.

**Corollary F$'$ (the only form used).** For $X$ uniform on $\mathcal X$:
$$I(X;Y)\ \ge\ (1-\delta)\log_2|\mathcal X|-\hbin(\delta).$$
With $|\mathcal X|=K^m$:
$$\boxed{\ \Ldelta:=(1-\delta)\,m\log_2K-\hbin(\delta).\ }\tag{0.2}$$

**中文 note**：$(0.1)$ 和 $(0.2)$ 是全场引用最多的两个式子，编号必须显式打出来，后面所有帧都引用这两个编号。

---

# Part II —— §1 Packing：为什么"可区分的设置"有可数个

**本 Part 是全文地基，也是唯一必须徒手推的部分。给它 6–7 帧，不要压缩。**

## Frame 1.1 — The projective distance, and why

$$\defn\quad \dproj(U,V):=\inf_{\varphi\in\mathbb{R}}\big\|U-e^{i\varphi}V\big\|_\op.$$

两条注记（itemize）：
- **Infimum attained**: $\varphi\mapsto\|U-e^{i\varphi}V\|_\op$ is continuous on the compact circle $\{e^{i\varphi}\}\cong S^1$.
- **Why quotient the global phase**: $U$ and $e^{i\varphi}U$ are physically indistinguishable. Without the quotient we would count physically identical objects as distinct, and \alert{the packing count would simply be wrong}.

**Claim 1.2 (reduction to the relative unitary).**
$$\dproj(U,V)=\inf_\varphi\big\|UV^\dagger-e^{i\varphi}I\big\|_\op.$$
*Proof.* $\|AB\|_\op=\|A\|_\op$ for unitary $B$; take $B=V^\dagger$. $\qed$

**Consequence（做成 callout）**：
> The problem is now purely geometric: **given the spectrum of a unitary (a set of points on the unit circle), rotate the whole circle to sit as close to $1$ as possible — how far is the worst point?**

## Frame 1.3 — Lemma 1.3: the two-point bound, and where the "4" comes from

**Lemma 1.3.** Let $\alpha,\beta\in\mathbb{R}/2\pi\mathbb{Z}$ with $d_\circ(\alpha,\beta)=\gamma\in[0,\pi]$. Then
$$\forall\varphi:\quad\max\big(|e^{i\alpha}-e^{i\varphi}|,\,|e^{i\beta}-e^{i\varphi}|\big)\ \ge\ 2\sin(\gamma/4),$$
with equality when $\varphi$ is the **midpoint of the short arc** between $\alpha$ and $\beta$.

*Proof.* Triangle inequality on $d_\circ$:
$$d_\circ(\alpha,\varphi)+d_\circ(\varphi,\beta)\ge\gamma\ \Longrightarrow\ \max\big(d_\circ(\alpha,\varphi),d_\circ(\beta,\varphi)\big)\ge\gamma/2.$$
WLOG $d_\circ(\alpha,\varphi)\ge\gamma/2$. By $(0.1)$, $|e^{i\alpha}-e^{i\varphi}|=2\sin\big(d_\circ(\alpha,\varphi)/2\big)$; since $t\mapsto2\sin(t/2)$ is increasing on $[0,\pi]$ and $d_\circ\in[0,\pi]$,
$$|e^{i\alpha}-e^{i\varphi}|\ \ge\ 2\sin\big((\gamma/2)/2\big)=2\sin(\gamma/4).$$
Equality: the short-arc midpoint gives $d_\circ(\alpha,\varphi)=d_\circ(\beta,\varphi)=\gamma/2$, and both chords equal $2\sin(\gamma/4)$. $\qed$

**⚑ 必答 callout（本帧的重点，必须单独框出）**：
> **"Why $\sin(\Theta/4)$ and not $\sin(\Theta/2)$?"** — two factors of 2 compose:
> **(i)** the optimal global phase sits **in the middle** $\Rightarrow$ angular distance halves from $\gamma$ to $\gamma/2$;
> **(ii)** the chord formula $|e^{iu}-1|=2\sin(u/2)$ carries a $/2$ of its own.
> $\gamma/2$ then $/2$ gives $\gamma/4$.

**中文 note**：这是全文唯一的"技巧性常数"。讲清楚它，听众会立刻信任后面所有紧性声明；讲不清楚会非常难看。

**建议配一张 TikZ 小图**：单位圆，两个点 $e^{i\alpha},e^{i\beta}$，短弧中点 $e^{i\varphi}$，两条等长弦，标注 $\gamma/2$ 与 $2\sin(\gamma/4)$。

## Frame 1.4 — Lemma 1.4: the character surjectivity lemma

**Lemma 1.4.** For $a_1,\dots,a_m\in\Fb^n$:
$$a_1,\dots,a_m\ \text{linearly independent over }\Fb\iff \Phi:\Fb^n\to\{\pm1\}^m,\ z\mapsto\big(\chi_{a_1}(z),\dots,\chi_{a_m}(z)\big)\ \text{surjective}.$$

*Proof.* Let $A\in\Fb^{m\times n}$ have rows $a_j$ and $L(z)=Az$. The map $\Fb^m\to\{\pm1\}^m$, $(b_j)\mapsto((-1)^{b_j})$, is a bijection, and $\Phi=(-1)^{L(\cdot)}$. Hence
$$\Phi\ \text{surjective}\iff L\ \text{surjective}\iff\operatorname{rank}A=m\iff\text{rows independent}.\qed$$

**⚑ callout（scope 伏笔）**：
> This is the entire group-theoretic content — and the origin of the paper's **most attackable assumption**. Lose $\Fb$-independence and $\Phi$ is no longer surjective; the very first step of Theorem 1.7 below cannot be executed, and the coefficients are no longer identifiable.

## Frame 1.5 — Definitions: wrap margin and the phase family

**Definition 1.5 (wrap margin).** For alphabet $[K]_0=\{0,\dots,K-1\}$, $K\ge2$, step $\Delta>0$:
$$\gamma(K,\Delta):=\min_{1\le d\le K-1}\cd{d\Delta}.$$
（一句解释："the least angle by which two coefficients can differ" — and $\cd\cdot$ already accounts for wrapping past $2\pi$.）

**Definition 1.6 (phase family).** $P_j=Z^{a_j}$ with $a_1,\dots,a_m$ $\Fb$-independent,
$$U_x:=\exp\Big(-\tfrac i2\sum_{j=1}^m x_j\Delta P_j\Big),\qquad x\in[K]_0^m.$$

## Frame 1.6 — Theorem 1.7: exact worst-pair separation

**Theorem 1.7.** For every $m\ge1$,
$$\boxed{\ \min_{x\ne y}\dproj(U_x,U_y)=2\sin\!\Big(\frac{\gamma(K,\Delta)}{4}\Big).\ }$$
In particular the family is projectively injective $\iff\gamma(K,\Delta)>0$.

**分两帧或用 pause 呈现证明的两半。**

*Proof, direction $(\ge)$.* Take $x\ne y$, $s:=x-y\ne0$, pick $j^*$ with $s_{j^*}\ne0$. By Claim 1.2 consider
$$W:=U_xU_y^\dagger=\exp\Big(-\tfrac{i\Delta}2\sum_j s_jP_j\Big),\qquad W|z\rangle=\lambda(z)|z\rangle,\quad \lambda(z)=\exp\Big(-\tfrac{i\Delta}2\sum_j s_j\chi_{a_j}(z)\Big).$$
By Lemma 1.4, $\Phi$ is surjective, so choose $z,z'$ with
$$\chi_{a_j}(z)=\chi_{a_j}(z')\ (j\ne j^*),\qquad \chi_{a_{j^*}}(z)=+1,\ \chi_{a_{j^*}}(z')=-1.$$
Then
$$\arg\lambda(z)-\arg\lambda(z')=-\tfrac\Delta2\big(s_{j^*}-(-s_{j^*})\big)=-\Delta s_{j^*}\ \Longrightarrow\ d_\circ\big(\arg\lambda(z),\arg\lambda(z')\big)=\cd{\Delta s_{j^*}}\ \ge\ \gamma(K,\Delta),$$
since $1\le|s_{j^*}|\le K-1$. Finally
$$\|W-e^{i\varphi}I\|_\op=\max_z|\lambda(z)-e^{i\varphi}|\ \ge\ \max\big(|\lambda(z)-e^{i\varphi}|,|\lambda(z')-e^{i\varphi}|\big),$$
so taking $\inf_\varphi$ and applying Lemma 1.3 gives $\dproj(U_x,U_y)\ge2\sin(\gamma/4)$.

*Proof, direction $(\le)$: equality is attained.* Pick $d\in\{1,\dots,K-1\}$ attaining $\gamma$ and take $x-y=d\,e_{j^*}$. Then $\sum_js_j\chi_{a_j}(z)=d\,\chi_{a_{j^*}}(z)\in\{+d,-d\}$, so the spectrum of $W$ is **exactly two points** $\{e^{\mp i\Delta d/2}\}$ at circle distance $\cd{\Delta d}=\gamma$. Lemma 1.3's equality case gives $\inf_\varphi=2\sin(\gamma/4)$. $\qed$

## Frame 1.7 — Corollary 1.8/1.9: both arithmetic regimes give $\gamma=\Delta$

**Corollary 1.8.**
1. **no-wrap regime**: if $(K-1)\Delta\le\pi$ then for all $1\le d\le K-1$, $d\Delta\in[\Delta,\pi]$, so $\cd{d\Delta}=d\Delta\ge\Delta$ and $\gamma=\Delta$.
2. **cyclic regime**: if $\Delta=2\pi/Q$ and $K\le Q-1$ then $\cd{d\Delta}=\frac{2\pi}Q\min(d,Q-d)\ge\frac{2\pi}Q=\Delta$, so $\gamma=\Delta$.

**Corollary 1.9 (uniform separation).** In both regimes
$$\min_{x\ne y}\dproj(U_x,U_y)=2\sin(\Delta/4),$$
i.e. the $K^m$ targets form a **packing** of separation $2\sin(\Delta/4)$.

**⚑ callout（"合"在这里，单独框出）**：
> In the cyclic regime the coefficient interval $[0,(Q-2)\cdot2\pi/Q]$ **may cross $\pi$**. A textbook principal-value argument on $[-\pi,\pi]$ would go wrong here. Theorem 1.7 handles wraparound exactly via $\cd\cdot$, needing no principal-interval hypothesis. **This is the entire meaning of "exact wrap margin."**

## Frame 1.8 — Lemma 1.10: from packing to a decoder (the pivot)

**Lemma 1.10 (nearest-packing decoder).** If $\mathcal F=\{U_x\}_{x\in\mathcal X}$ is pairwise $\dproj\ge4\varepsilon$ and $\hat x(C):=\arg\min_y\dproj(U(C),U_y)$ (fixed tie rule), then
$$\dproj(U(C),U_x)\le\varepsilon\ \Longrightarrow\ \hat x(C)=x.$$
*Proof.* For $y\ne x$: $\dproj(U(C),U_y)\ge\dproj(U_x,U_y)-\dproj(U_x,U(C))\ge4\varepsilon-\varepsilon=3\varepsilon>\varepsilon\ge\dproj(U(C),U_x)$. $\qed$

**⚑ 必答 callout（本 Part 的收束）**：
> **This lemma is the pivot of the entire paper.** It converts the soft statement *"the compiler's output is correct"* into the hard statement *"the output uniquely determines $x$"*. Hence **any correct compiler is forced to encode all of $x$ somewhere in its output** — and information can be counted in bits. Part V does nothing but apply this conversion three times.

---

# Part III —— §2 Calibration：$K_\varepsilon$ 不是我挑的

**本 Part 的唯一目的**：回答"你的字母表大小是不是为了让界好看而选的"。3–4 帧。

## Frame 2.1 — The question, stated as an objection

一页只放一句质疑 + 一句回答：

> *"Isn't $K$ chosen to make the bound look good?"*
>
> **No: $K_\varepsilon$ equals the metric-entropy count of pairwise distinguishable rotations at tolerance $\varepsilon$, up to an explicitly interpretable factor.**

## Frame 2.2 — Definitions and the exact single-axis distance

**Definition 2.1.** $g_\varepsilon:=4\arcsin(2\varepsilon)$, and
$$N(\varepsilon):=\max\big\{|S|:S\subseteq\{R_P(\theta)\}_{\theta\in\mathbb{R}/2\pi\mathbb{Z}},\ \text{pairwise }\dproj\ge4\varepsilon\big\}.$$

**Lemma 2.2.** $\dproj\big(R_P(\theta),R_P(\theta')\big)=2\sin(g/4)$ where $g:=d_\circ(\theta,\theta')$.
*Proof.* $R_P(\theta)R_P(\theta')^\dagger=R_P(\delta)$, $\delta=\theta-\theta'$, whose spectrum is exactly the two points $e^{\mp i\delta/2}$ at circle distance $\cd\delta=g$; apply the equality case of Lemma 1.3. $\qed$

**Corollary 2.3.** $\text{pairwise }\dproj\ge4\varepsilon\iff\text{pairwise }d_\circ\ge g_\varepsilon$, because $2\sin(g_\varepsilon/4)=2\sin(\arcsin2\varepsilon)=4\varepsilon$ **exactly** — that is how $g_\varepsilon$ was defined.

## Frame 2.3 — Theorem 2.4 and the cyclic exact identity

**Theorem 2.4 (metric-entropy count).**
$$N(\varepsilon)=\Big\lfloor\frac{2\pi}{g_\varepsilon}\Big\rfloor,\qquad \frac1{2\varepsilon}-1<N(\varepsilon)\le\frac\pi{4\varepsilon}.$$
*Proof.* On a circle of circumference $2\pi$, points pairwise $\ge g$ apart number at most $\lfloor2\pi/g\rfloor$ (order them; the gaps sum to $2\pi$ and each is $\ge g$), attained by equal spacing. The two-sided estimate uses $x\le\arcsin x\le\frac\pi2x$ on $[0,1]$: $g_\varepsilon\in[8\varepsilon,4\pi\varepsilon]$. $\qed$

**Corollary 2.5 (cyclic: exact equality).** The paper takes $Q_\varepsilon:=\big\lfloor\frac\pi{2\arcsin2\varepsilon}\big\rfloor$, and
$$\frac\pi{2\arcsin2\varepsilon}=\frac{2\pi}{4\arcsin2\varepsilon}=\frac{2\pi}{g_\varepsilon}\ \Longrightarrow\ \boxed{\,Q_\varepsilon=N(\varepsilon)\,}.$$

**callout**：`The sharing modulus equals the metric-entropy count itself — no free parameter at all.`

## Frame 2.4 — Proposition 2.6: what the factor 4 is

**Proposition 2.6.** With $L_\varepsilon=\lfloor\frac\pi{8\arcsin2\varepsilon}\rfloor$, $K_\varepsilon=L_\varepsilon+1$, $\Delta_\varepsilon=\frac\pi{2L_\varepsilon}$:
$$(K_\varepsilon-1)\Delta_\varepsilon=L_\varepsilon\cdot\frac\pi{2L_\varepsilon}=\frac\pi2\le\pi\quad(\text{no-wrap holds}),$$
$$\frac{\Delta_\varepsilon}4=\frac\pi{8L_\varepsilon}\ge\arcsin2\varepsilon\ \Longrightarrow\ 2\sin(\Delta_\varepsilon/4)\ge4\varepsilon,$$
and with $y:=\frac\pi{2\arcsin2\varepsilon}$ (so $N=\lfloor y\rfloor$, $K_\varepsilon=\lfloor y/4\rfloor+1$):
$$\frac{N(\varepsilon)}4<K_\varepsilon<\frac{N(\varepsilon)}4+\frac32.$$

**⚑ 必答 callout**：
> The factor $4$ is **not slack in an estimate** — it is exactly the price of the no-wrap condition restricting the coefficient range to the quarter period $[0,\pi/2]$. The cyclic version has no such restriction and degenerates to the exact identity $Q_\varepsilon=N(\varepsilon)$. **Both directions are stated as two-sided bounds; no tighter constant is claimed.**

**中文 note**：最后那半句要主动说出来，它挡掉一整类"常数是不是调出来的"追问。

## Frame 2.5 — Remark 2.7: why $\log(1/\varepsilon)$ appears twice

Ross–Selinger guarantees that **every** grid angle costs $\Theta(\log(1/\varepsilon))$ in Clifford+$T$ synthesis, **uniformly over the alphabet**. Hence

$$\underbrace{m\log_2K_\varepsilon}_{\text{information side: alphabet size}}=m\log_2\Theta(1/\varepsilon),\qquad \underbrace{3\log_2(1/\varepsilon)}_{\text{physical side: repair cost per coordinate}}$$

**callout**：`The two logarithms come from the same grid. This — not an analogy — is the technical basis on which "exchange rate" is a legitimate word.`

**在本帧加入"汇率缩影"的具体数字（这是全场最好记的一页，可单独成帧）**：

> One QAOA cost layer, 3-regular MaxCut on 22 vertices: $m=33$ edges, $\varepsilon=10^{-3}$.
> $L_\varepsilon=\lfloor\pi/(8\arcsin2\varepsilon)\rfloor=196$, $K_\varepsilon=197$.
> Per edge: $\log_2197=7.62$ bits. Whole layer: $\alert{252\text{ bits}\approx31\text{ bytes}}$.
> A compiler that **defers** carries those 31 bytes across every cut.
> A compiler that **commits early** buys the same information back at $\approx3\log_2(1/\varepsilon)\approx30$ $T$ gates per corrected coordinate: $\alert{\text{order }10^3\text{ magic states}}$.

**中文 note**：如果全场只有一页被记住，应该是这一页。建议做成独立一帧、大字号。

---

# Part IV —— §3 Dispersal：为什么没有记录泄露 aggregate

**目标**：正确性（同一酉矩阵）+ 信息隐藏（无记录、无真前缀泄露）。后者是 Part V 的原料。4–5 帧。

## Frame 3.1 — Definition 3.1: the $r$-round dispersed update stream

**Definition 3.1.** Fix $Q\ge3$, $\Delta=2\pi/Q$, $K=Q-1$, $r\ge2$.
- **Semantic input**: $x\in[K]_0^m$ — $m$ addressed records.
- **Flat input**: round-major records $\mathrm{Update}(t,j,a_j^{(t)})$, $a_j^{(t)}\in\ZQ$, with
$$\sum_{t=1}^r a_j^{(t)}\equiv x_j\pmod Q,\qquad j\in[m],\tag{3.1}$$
realizing $W=\prod_{t=1}^r\prod_{j=1}^m R_{P_j}\big(\Delta a_j^{(t)}\big)$.

**配图（重要，复用海报的 Fig 1(a) 结构，用 TikZ 重画）**：
- 上排：SEMANTIC — $m$ 个方块 $(P_1,\theta_1),\dots,(P_m,\theta_m)$；
- 中间箭头：`schedule · twirl · lower`；
- 下方：DISPERSED — 3 行 $\times$ $m$ 列的方块 $\pm a_j^{(t)}$，标注 round 1/2/3；
- 底部一行文字：`no record — and no proper prefix — determines the edge total` $x_j=\sum_ts_j^{(t)}a_j^{(t)}\bmod Q$.

## Frame 3.2 — Correctness: Claim 3.2 + Proposition 3.3

**Claim 3.2.** $R_P(\theta+2\pi k)=(-1)^kR_P(\theta)$.
*Proof.* $\exp(-i\pi P)$ acts as $e^{\mp i\pi}=-1$ on both $\pm1$ eigenspaces of $P$, so $\exp(-i\pi P)=-I$; iterate. $\qed$

**Proposition 3.3.** Any flat stream satisfying $(3.1)$ realizes $U_x$ up to a global phase.
*Proof.* The $P_j$ commute, so $W=\prod_jR_{P_j}\big(\Delta\sum_ta_j^{(t)}\big)$. With integer representatives $\sum_ta_j^{(t)}=x_j+Qk_j$ and $Q\Delta=2\pi$, Claim 3.2 gives $R_{P_j}(\Delta x_j+2\pi k_j)=(-1)^{k_j}R_{P_j}(\Delta x_j)$; the product of signs $(-1)^{\sum_jk_j}$ is global, and $\dproj$ has already quotiented it. $\qed$

## Frame 3.3 — Proposition 3.4: record and prefix privacy

**Proposition 3.4.**
1. For any fixed $(t,j,a)$ and any $b\in[K]_0$, there is a valid stream with $a_j^{(t)}=a$ **and** $x_j=b$.
2. Under the **canonical sharing distribution** (first $r-1$ shares i.i.d. uniform on $\ZQ$, last fixed by $(3.1)$), every individual residue is uniform on $\ZQ$ **and independent of $x_j$**.
3. After any proper prefix, the final-round residue choice reaches every aggregate in $\ZQ^m$, hence every $x\in[K]_0^m$.

*Proof.* (1) Since $r\ge2$, pick $t'\ne t$ and set $a_j^{(t')}:=b-a-\sum_{t''\ne t,t'}a_j^{(t'')}\bmod Q$. (2) For $r=2$: $a^{(1)}$ uniform; conditioning on $x_j$ leaves it uniform; $a^{(2)}=x_j-a^{(1)}$ is then uniform. A sum containing at least one independent uniform term is uniform. (3) Apply (1) coordinatewise. $\qed$

**⚑ callout（听众一定会认出这个结构，主动点名）**：
> $(3.1)$ together with 3.4(2) **is additive secret sharing over $\ZQ$** — a one-time pad. Constructing a secret sharing is cheap and is *not* the contribution. The contribution is the next slide.

## Frame 3.4 — Proposition 4: the FT stack emits these streams anyway

**这一帧是本 Part 的核心，必须与上一帧形成对照。**

Each of the following emits streams of Definition 3.1, and each generated family satisfies the hypotheses of the lower bounds:

- **(a) Time-dependent Trotterization.** $H(t)=\sum_jc_j(t)P_j$ with step $\tau$; round $t$ applies $R_{P_j}(2c_j(t_t)\tau)$; grid rounding gives $a_j^{(t)}$, $s\equiv+1$.
- **(b) Layerwise-parameterized phase layers.** A depth-$r$ ansatz whose round-$t$ commuting layer carries free coefficients $\theta_j^{(t)}$.
- **(c) Randomized compiling of (a) or (b).** Twirling multiplies each residue by $s_j^{(t)}$, in folded or tracked mode.

**⚑ 必答 callout（反例，必须自己讲出来）**：
> **The constant schedule $a_j^{(t)}\equiv a_j$ is degenerate**: $x_j=ra_j\bmod Q$ is determined by round one alone.
> This is exactly why **controlled-power ladders and phase estimation are OUT of scope**: they supply contiguity but **not** coefficient freedom.
> An exhaustive enumeration at $(m,r,Q)=(2,2,5)$ confirms all three behaviours (frozen artifact `fooling_set_m2_r2_Q5.json`).

**中文 note**：自己举反例，"假设太强"的攻击就会转化为对你 scope 意识的确认。这一帧的说服力全部来自这个 callout。

## Frame 3.5 — Lemma 3.5 + Corollary 3.6: Clifford records normalize away

**Lemma 3.5 (Clifford interleaving).** Suppose the rounds are separated by Clifford records and the accumulated Clifford $D_{t-1}$ satisfies
$$D_{t-1}^\dagger P_jD_{t-1}=\varepsilon_j^{(t)}P_{\pi_t(j)},\qquad \varepsilon_j^{(t)}\in\{\pm1\},\ \pi_t\in S_m.\tag{3.2}$$
Then commuting every Clifford record to the end yields a stream of Definition 3.1 on the same generators (residues unchanged, signs multiplied by $\varepsilon_j^{(t)}$, coordinates relabelled by $\pi_t$), plus a fixed Clifford suffix $D_r$.

*Proof.* Write the emitted unitary as $D'_rL_r\cdots D'_1L_1$. Moving each Clifford leftwards replaces $L_t$ by $D_{t-1}^\dagger L_tD_{t-1}$; since conjugation is an automorphism and $L_t=\prod_jR_{P_j}(\Delta s_j^{(t)}a_j^{(t)})$, $(3.2)$ gives
$$D_{t-1}^\dagger L_tD_{t-1}=\prod_jR_{P_{\pi_t(j)}}\big(\Delta\varepsilon_j^{(t)}s_j^{(t)}a_j^{(t)}\big).$$
$D_{t-1}$ — hence $\pi_t,\varepsilon^{(t)}$ — is computable from the prefix, so the normalization is **prefix-measurable**; $D_r$ is common to the family and unitary, preserving projective distance and the separation of Theorem 1.7. $\qed$

**Corollary 3.6.** $a\mapsto sa\bmod Q$ ($s=\pm1$) is a bijection of $\ZQ$ $\Rightarrow$ the twirled family maps **record-for-record** onto the untwirled family, preserving aggregates, record boundaries and cut positions.

**⚑ 必答 callout（"不依赖 Pauli frame"的全部内容）**：
> Sign normalization is a **bijection of the residue alphabet**, so the standard folded (compile-time) presentation of randomized compiling inherits every bound verbatim.
>
> **Boundary (state it before being asked):** $(3.2)$ is a real restriction. It holds for Pauli-frame layers ($\pi_t=\mathrm{id}$) and for routing/SWAP layers permuting the generating set. **It fails** if some accumulated Clifford sends a $P_j$ to a *product* of generators rather than a generator — the rounds then accumulate in different bases and the coordinatewise structure is lost.

---

# Part V —— §4 The lower bounds：一个论证的三次变奏

**这是心脏。8–10 帧。开场必须先讲"只有一个论证"。**

## Frame 4.0 — Roadmap: one argument, three variations

一页图示：

```
        packing separation (Part II)
                    ↓
        decoder exists (Lemma 1.10)
                    ↓
   "correct"  ≡  "the output encodes x"
                    ↓
        count bits: Kraft / Fano
```

并列三个变奏（表格）：

| Variation | Setting | Tool |
|---|---|---|
| Theorem 4.2 | deterministic, one pass, zero error | fooling set + Kraft |
| Theorem 4.4 | two-round masked share, binary aggregate | same, new common-suffix construction |
| Theorem 4.6 | randomized, $p$ passes | one-time pad + conditional Fano |

**中文 note**：明确告诉听众：真正要理解的只有一次，后两个只是换一步构造、换一个信息论事实。这句话会让整个 Part 听起来轻松一半。

## Frame 4.1 — Definition 4.1: the cut budget and forward-pass accounting

At every execution cut, the restart snapshot is serialized in **five disjoint fields**:
$$\Bcut=B_{\mathrm{control}}+B_{\mathrm{store}}+B_{\mathrm{window}}+B_{\mathrm{parameter}}+B_{\mathrm{IR}}$$

配一个 5 行表说明各字段内容：

| field | contents |
|---|---|
| control | finite control, pass/head/termination state, random seed + cursor |
| store | RAM, stacks, hash tables, caches **and their layout** |
| window | structural fields of the ordered live read window |
| parameter | every live parameter payload (sparse symbolic form) |
| IR | every other live IR/DAG/table object, **and every rereadable consumed input block** |

Partition the round-major stream into Alice's prefix $A$ (rounds $1,\dots,r-1$) and Bob's suffix $B$ (round $r$). A forward $p$-pass compiler makes at most $p$ crossings $A\to B$ and $p-1$ rewinds $B\to A$:
$$\Sigma_p:=\sum_{\text{crossings}}\Bcut\ \le\ (2p-1)S,\qquad S:=\max_c\Bcut(c).\tag{4.1}$$

**⚑ 必答 callout**：
> **"What is $2p-1$?"** — $p$ forward crossings plus at most $p-1$ backward crossings of that one cut. That is all. **But failing to answer instantly looks like not having read your own definition.**

## Frame 4.2 — Lemma 4.1: the restart lemma (where the model's power lives)

**Lemma 4.1.** At the cut, the five-field serialization together with the already-committed output prefix **completely determines** the continuation of the run for any supplied suffix $v$. (For randomized runs, conditionally on the serialized random tape and cursor.)

*Proof.* `control` restores transitions, heads, dynamic pass schedule, seed cursor; `store`/`window` restore RAM, stacks, hash and cache metadata, live token structures; `parameter` restores every omitted coefficient by location tag; `IR` restores all remaining live intermediate objects and retained rereadable input. The five fields are disjoint and exhaustive, hence reconstruct the full machine configuration; appending the suffix executes the same continuation. $\qed$

**⚑ 必答 callout（本帧单独成 block，视觉最重）**：
> This lemma is where the model's force lies. Materializing round one into a **phase-polynomial table**, a **ZX graph**, or a **cache** is **not an escape channel — it is a billed line item** ($B_{\mathrm{store}}$ or $B_{\mathrm{IR}}$).
>
> Companion guarantee (**Lemma 10, dimension-preserving instrumentation**): a reported field is exactly $8\cdot\texttt{stat}(A).\texttt{st\_size}$ bits. **There is no gate-count-to-bit code path anywhere.**

## Frame 4.3 — Variation 1: Theorem 4.2 (zero error, one pass)

**Theorem 4.2.** A deterministic one-pass compiler correct to $\varepsilon<\sin\big(\frac\pi{2Q}\big)$ on every valid stream of Definition 3.1 satisfies
$$A_1+\Bcut(c_{A\to B,1})\ \ge\ \big\lceil m\log_2Q\big\rceil.$$

*Proof.* For each $u\in\ZQ^m$ take the canonical prefix (put $u$ in round one, zeros elsewhere) and set
$$M(u):=\big(\text{committed output prefix at the cut},\ \text{five-field snapshot}\big).$$

**Claim (injectivity): $u\ne u'\Rightarrow M(u)\ne M(u')$.**

*Construct a common suffix.* Coordinatewise, choose $v_j\in\ZQ$ so that **neither** $u_j+v_j$ **nor** $u'_j+v_j$ equals the excluded residue $Q-1$. At most two values of $v_j$ are forbidden (namely $Q-1-u_j$ and $Q-1-u'_j$), and $Q\ge3$, so a legal $v_j$ exists. Then $x:=u+v$, $x':=u'+v$ both lie in $[K]_0^m$ with $K=Q-1$, and $u_j\ne u'_j\Rightarrow x_j\ne x'_j$.

*Derive the contradiction.* Suppose $M(u)=M(u')$. By Lemma 4.1 the continuation is a deterministic function of (snapshot, suffix), and both runs receive the same suffix $v$, so both emit the **same** final string $C$. Correctness gives $\dproj(U(C),U_x)\le\varepsilon$ and $\dproj(U(C),U_{x'})\le\varepsilon$, hence $\dproj(U_x,U_{x'})\le2\varepsilon$. But $x\ne x'$, so by Theorem 1.7 and Corollary 1.8(2),
$$\dproj(U_x,U_{x'})\ \ge\ 2\sin(\Delta/4)=2\sin\!\Big(\frac\pi{2Q}\Big)\ >\ 2\varepsilon.$$
Contradiction.

Thus $M$ is injective on $Q^m$ values; the messages are prefix-free under the declared serializers, so Fact K gives $\max_u|M(u)|\ge m\log_2Q$, and $|M(u)|\le A_1+\Bcut$. $\qed$

## Frame 4.4 — The one clever step: why $K=Q-1$, why $Q\ge3$

**单独一帧，这是全 Part 唯一需要动脑的地方。**

> **$K=Q-1$ (rather than $K=Q$) is for the fooling set, not for the packing.**
> By Corollary 1.8(2) the separation holds just as well at $K=Q$. Excluding one residue class is what guarantees that for **any** $u,u'$ there exists a **common** suffix $v$ sending both into the legal alphabet.
>
> **And that is why $Q\ge3$**: at most two values of $v_j$ are forbidden, so a third must be available.

**中文 note**：听众若问"为什么 $Q\ge3$"，答案就在这里。这是构造性的一步，也是讲台上最能显示"我真的懂自己的证明"的一处。

## Frame 4.5 — Variation 2: Theorem 4.4 (two-round masked share)

Setting: $Q=3$ (sharing modulus), $\alpha=2\pi/3$, but the **aggregate alphabet is restricted to binary**, $x\in\{0,1\}^m$. First share $u\in\mathbb{Z}_3^m$ arbitrary, second $v$ with $u+v\equiv x\pmod3$.

**Theorem 4.4.** A deterministic compiler correct to $\varepsilon<\varepsilon_0:=\sin(\pi/6)=1/2$ on every valid two-round decomposition satisfies, under the single family-relative output code,
$$B^{\mathrm{rel}}_{\mathrm{pre}}+B^{\mathrm{MS}}_{\mathrm{cut}}\ \ge\ \lceil m\log_23\rceil.\tag{4.2}$$
Hence if the final output is **compact**, $B^{\mathrm{out}}_{\mathrm{rel}}\le m+c\log_2(m+2)$, then
$$B^{\mathrm{MS}}_{\mathrm{cut}}\ \ge\ \lceil m\log_23\rceil-m-c\log_2(m+2)=\Omega(m).\tag{4.3}$$
By contrast a one-pass compiler receiving the semantic aggregate $x$ attains $B^{\mathrm{out}}_{\mathrm{rel}}=m+O(\log m)$ **and** $\Bcut=O(\log m)$.

*Proof (only the step that differs from 4.2 — the coordinatewise common suffix).*
$$u_j=u'_j\ \Rightarrow\ v_j:=-u_j\ \ (\text{both aggregates }0);$$
$$u'_j=u_j+1\ \Rightarrow\ v_j:=-u_j\ \ (\text{aggregates }0,1);$$
$$u_j=u'_j+1\ \Rightarrow\ v_j:=-u'_j\ \ (\text{aggregates }1,0).$$
Both $(u,v)$ and $(u',v)$ are valid **binary**-aggregate instances and their aggregate vectors differ wherever $u\ne u'$. The rest is as in 4.2, using bit-class separation $2\varepsilon_0>2\varepsilon$; Kraft on $3^m$ prefix classes gives $(4.2)$. $\qed$

## Frame 4.6 — Why Variation 2 is not a weakening: it is a separation theorem

**单独一帧，用对照表**：

| | output | crossing state |
|---|---|---|
| **dispersed (masked-share) stream** | $m$ bits suffice for the alphabet | but the cut must carry $m\log_23\approx1.585m$ bits |
| **semantic stream** | $m+O(\log m)$ | $O(\log m)$ |

**⚑ callout**：
> On the dispersed representation, **compact output and small state are not simultaneously achievable**; on the semantic stream **both are**.
>
> This — not merely a lower bound — is the cleanest mathematical statement of *"representation is a resource."* **It is a separation theorem.**

## Frame 4.7 — Variation 3: Theorem 4.6, the main theorem

**Theorem 4.6.** Let $Q\ge3$, $K=Q-1$, $0\le\varepsilon<\sin\big(\frac\pi{2Q}\big)$. Let a possibly randomized compiler be correct within projective error $\varepsilon$ with probability $\ge1-\delta$ for every $x\in[K]_0^m$ and every valid $r$-round dispersed representation, making at most $p=p(m)$ forward passes. Then
$$\overline B^{\mathrm{out}}_{\mathrm{rel}}\ \ge\ \Ldelta,\qquad \overline B^{\mathrm{out}}_{\mathrm{self}}\ \ge\ \Ldelta,\tag{4.4}$$
$$\overline A_p+\overline\Sigma_p\ \ge\ \Ldelta\ \Longrightarrow\ \boxed{\ \overline A_p+(2p-1)S\ \ge\ (1-\delta)m\log_2K-\hbin(\delta)\ }\tag{4.5}$$

**把 $(4.5)$ 做成全场最大的一个公式框。**

## Frame 4.8 — Proof of Theorem 4.6, part (i): the output bound

Take $X$ uniform on $[K]_0^m$, fix one valid dispersed representation per value, let $C$ be the output. By Corollary 1.9 the separation exceeds $2\varepsilon$, so the nearest-packing decoder of Lemma 1.10 recovers $X$ from a successful output with error $\le\delta$. By Fact F$'$,
$$I(X;C)\ \ge\ (1-\delta)m\log_2K-\hbin(\delta)=\Ldelta.$$
Also $H(C)\ge I(X;C)$, so by Fact S the expected length of either prefix-free output code is $\ge\Ldelta$; a worst-input expectation is at least the uniform average.

**⚑ callout**：`This step depends only on the output distribution — random access, dynamic passes, and internal IR cannot weaken it.`

## Frame 4.9 — Proof of Theorem 4.6, part (ii): the transcript bound

Put $U$ uniform on $\ZQ^m$ in round one, zeros in other prefix rounds, and set the last share
$$V:=X-U\bmod Q.$$
Given $X=x$, $V=x-U$ is uniform in $U$, so **$V$ is uniform and independent of $X$** (one-time pad), whence
$$H(X\mid V)=H(X)=m\log_2K.$$
Let the transcript $T$ contain every crossing snapshot and all output chunks written on Alice's side. By Lemma 4.1 (including random tape and dynamic control), $(T,V)$ suffices to reproduce every Bob-side segment and the complete final output, so a decoder recovers $X$ from $(T,V)$ with error $\le\delta$. Conditional Fano gives
$$H(X\mid T,V)\le \hbin(\delta)+\delta\log_2(K^m-1)\ \Longrightarrow\ I(X;T\mid V)\ \ge\ \Ldelta.$$
The framed transcript is prefix-free conditional on $V$, so its expected literal length — which is exactly $\overline A_p+\overline\Sigma_p$ — is at least this. Apply $(4.1)$. $\qed$

## Frame 4.10 — The whole of Part V in one line

一页只放这两行（大字）：

$$\text{packing separation}\ \Rightarrow\ \text{decoder exists}\ \Rightarrow\ \text{“correct”}\equiv\text{“the output encodes }x\text{”}\ \Rightarrow\ \text{count bits}$$

> And **dispersal** guarantees that at the cut, $x$ is not yet determined by any single record or proper prefix. So those bits **must** cross the cut: either in committed output ($A_p$), or in carried state ($S$).
>
> **Two currencies. There is no third.**

## Frame 4.11 — Remark 4.7: what is NOT claimed (say it before being asked)

- $(4.4)$ is an **output-information** bound; $(4.5)$ is a **transcript** bound. **They are not interchangeable**, and neither converts self-contained circuit bits into gate counts.
- At $p=1$ with zero error, Theorem 4.2 strengthens $m\log_2K$ to $m\log_2(K+1)=m\log_2Q$. **No such strengthening is claimed** for randomized or general multipass protocols.
- **Reverse scans, an uncharged random-access input oracle, or a different output code would be a different model.**

## Frame 4.12 — Theorem 4.8: the commitment toll (the two currencies are not at par)

**Theorem 4.8.** Fix $Q$, $K=Q-1$, $\varepsilon<\sin(\frac\pi{2Q})$, a dispersal mask $T\subseteq[m]$ with $|T|=k$. If the compiler is correct on every valid stream and its committed prefix must be **independently parseable** (append-only first-exposure regime: an emitted record is executed and cannot be reinterpreted once the suffix arrives), then at the inter-round cut
$$A_{\mathrm{pre}}\ \ge\ \underbrace{k\log_2(2Q)}_{\text{payload}}+\underbrace{\log_2\binom mk}_{\text{toll}},\tag{4.6}$$
while a deferred compiler attains $A_{\mathrm{pre}}=0$ with $S\le k\log_2(2Q)+O(\log m)$. The toll is **the entropy of the commitment schedule**; it vanishes iff that schedule is determined by public data (in particular at $k=m$).

*Proof.* Two valid streams differing in round-one content (in the mask, in a residue, or in a sign) require different round-one rotations; by Theorem 1.7 their completions are separated by $2\sin(\frac\pi{2Q})>2\varepsilon$, so a prefix executed as emitted must differ. Hence
$$\big(T,\{a_j^{(1)}\}_{j\in T},\{s_j^{(1)}\}_{j\in T}\big)\longmapsto\text{committed prefix}$$
is injective on $\binom mkQ^k2^k$ values, and Kraft gives $(4.6)$. For the deferred compiler: the round-major order of Definition 3.1 is **public**, so stored residues are addressed by position and the mask is disclosed by the round-two records **at no charge**; the $O(\log m)$ term is the header. $\qed$

## Frame 4.13 — Corollary 4.9: the toll does not grow with $m$

With $k=\eta m$, since $\frac1m\log_2\binom m{\eta m}\to \hbin(\eta)$:
$$\frac1k\log_2\binom mk\ \longrightarrow\ \frac{\hbin(\eta)}{\eta},$$
a **constant** per generator: $\approx2$ bits at $\eta=\frac12$, and $0$ at $\eta=1$.

**⚑ callout（全文最漂亮的不对称，把因果说清楚）**：
> Commitment is irreversible, so **you must pay the entropy of your own decision about when to commit**. A compiler that defers is handed that same decision **for free** by the stream that follows.
>
> Three readable consequences, all direct from $(4.6)$: **toll = schedule entropy**; **zero iff public**; **independent of $m$**. All three are measured (see backup).

---

# Part VI —— §5 Upper bounds：为什么这是前沿而非空洞下界

**这一 Part 绝不可省。没有它，下界只是"也许永远达不到"的空话。4–5 帧。**

## Frame 5.1 — Why this Part exists

一页一句：

> Without matching constructions, a lower bound is a statement about a region no one has been shown to reach.
> **This Part turns the bound into a frontier.**

## Frame 5.2 — Proposition 5.1: the semantic corner

**Proposition 5.1.** Under the same public family dictionary, a one-pass semantic compiler receiving $x$ packs the ordered aggregate vector into one base-$K$ integer and streams it:
$$B^{\mathrm{out}}_{\mathrm{rel}}\le\lceil m\log_2K\rceil+O(\log(mK)),\qquad S=O(\log(mK)).$$
*Proof.* Retain only a streaming index and framing state; store no coefficient table and no intermediate graph. Proposition 3.3 gives semantic equality with the flat representation. $\qed$

**Consequence.** $(4.4)$ is tight to framing terms. Adding an input-independent abort coin (run the above with probability $1-\delta$, else emit a fixed short circuit) gives expected relative output
$$(1-\delta)\lceil m\log_2K\rceil+O(\log(mK)+1),$$
so **the randomized output lower bound is matched up to framing and the additive $\hbin(\delta)$ term.**

## Frame 5.3 — Proposition 5.2: the memory-capped block hybrid

**Proposition 5.2.** Fix $p,h\ge1$, $q=\min\{m,ph\}$. There is a deterministic zero-error $p$-pass compiler aggregating $q$ coordinates and passing the rest through in the public $p$-block hybrid mode, with
$$S\le\Big\lceil\frac qp\Big\rceil\log_2Q+O(\log(mQrp)),\qquad A_p\le(r-1)(m-q)\log_2Q+O(r\log(mQrp)).$$
At the **compact-output corner** $h=\lceil m/p\rceil$ (i.e. $q=m$):
$$B^{\mathrm{out}}_{\mathrm{rel}}\le m\log_2K+O(\log(mQrp)),\qquad S\le\Big\lceil\frac mp\Big\rceil\log_2Q+O(\log(mQrp)).$$

*Proof.* Split the first $q$ coordinates into at most $p$ consecutive blocks of size $\le h$. On pass $t$ keep only block $t$'s residues and add their first $r-1$ rounds mod $Q$; when the final-round mates arrive, emit the corresponding base-$K$ aggregate block. On the first pass, emit every share of each unselected coordinate in the declared round-major order — those rotations already have the correct product (Proposition 3.3), so **no coefficient table is retained**. The live packed block, indices and framing give the bound on $S$. Block boundaries are a public function of $(m,p,q)$, so the header stores those integers rather than $p$ separate delimiters. $\qed$

## Frame 5.4 — Theorem 5.3: constant-factor tightness

**Theorem 5.3.** For $r=2$ the construction satisfies $A_p+pS\le m\log_2Q+O(p\log(mQrp))$. Compared with $(4.5)$ at $\delta=0$, the ratio
$$\frac{(2p-1)\log_2(K+1)}{p\log_2K}\ <\ 2\log_23\qquad(\forall K\ge2),$$
so **the lower envelope is attained constructively up to an absolute constant.**
*Proof.* $(2p-1)/p<2$ and $\log_2(K+1)/\log_2K\le\log_23$ (maximal at $K=2$). $\qed$

## Frame 5.5 — THE FRONTIER FIGURE (必做，TikZ)

**这是全场最重要的一张图。TikZ 构造要求（严格按此画）：**

- 横轴：$S$ — crossing state carried (bits)。纵轴：$A_p$ — committed output (bits)。
- **一条实线**：由 $(4.5)$ 给出的 proved floor（一条向下凸的边界曲线，形如 $A_p+(2p-1)S=\Ldelta$，在双对数视觉下呈弯折）。
- 实线**下方区域**用 `\pattern[pattern=north east lines]` 填充，标注 `impossible for a compiler fed the dispersed stream`。
- 曲线上/近处标出三个点，用不同 marker：
  1. **materialize-first** — 靠 $A_p$ 轴顶端，标注 `commits everything`；
  2. **memory-capped block hybrid** — 曲线中段，标注 `within a constant factor of the floor (Thm 5.3)`；
  3. **full deferral** — 靠 $S$ 轴，标注 `$A_p=0$`。
- **一条虚线**：attained envelope（block hybrid 的实际曲线，紧贴实线上方）。
- **左下角外一个孤立的空心圆点**：`semantic input — never dispersed: compact output, log state (Prop 5.1)`，并加一条引线注明 `not on the frontier: it is not in the same input class`。
- 图例：`solid: the proved floor · dashed: the attained envelope`。

**⚑ 讲台提示（note）**：那个孤立点必须解释清楚——它不在前沿上，是因为它根本不在同一个输入类里。讲清这一点，"你的界是不是说编译器不可能做好"这个误解就消失了。

## Frame 5.6 — Scope: the seven assumptions and where each breaks

**这一帧必须放在正文里（不是 backup），且放在 §5 之后、Takeaway 之前。用表格。**

| assumption | what breaks without it |
|---|---|
| $\Fb$-independence | Lemma 1.4 surjectivity fails $\Rightarrow$ first step of Thm 1.7 cannot be executed |
| contiguity | commutation premise (Frame 0.4) fails $\Rightarrow$ **the aggregate does not exist** $\Rightarrow$ the *question* fails, not the bound |
| coefficient freedom across rounds | fooling set collapses to one class (constant schedule, Frame 3.4) |
| $Q\ge3$ | no common suffix $v_j$ exists in Thm 4.2 |
| $\varepsilon<\sin(\pi/2Q)$ | decoder of Lemma 1.10 fails $\Rightarrow$ Fano unusable |
| $\delta<1/2$ | $\Ldelta$ in $(0.2)$ loses meaning |
| Lemma 3.5 condition $(3.2)$ | rounds accumulate in different bases $\Rightarrow$ coordinate structure of Def 3.1 lost |

**⚑ 讲台提示**：这一帧是全场最强的一件装备。主动交出 scope，比被追问着承认要强得多。

## Frame 5.7 — Takeaway

大字，居中：

> ## Randomize and lower late.
>
> The information a compiler discards before aggregating cannot be recovered for free — it must be bought back **in memory** or **in magic states**, and buying it back early is strictly the more expensive of the two.
>
> **Treat recoverability as a controlled variable in compilation and resource estimation.**

---

# Part VII —— 附录 / Backup（位于 §5 之后，不参与 0–5 主线顺序）

**用 `\appendix` 开始，并设置 `\setbeamertemplate{footline}{}` 或标注 BACKUP，使听众知道这是备用帧。**

## Frame A.1 — Evidence classes (Table IV) — 先讲这一帧

**这是所有"你的实验能证明什么"类攻击的挡箭牌。**

| class | contents | authorized inference |
|---|---|---|
| ① **instrumented theorem-model implementation** | traced reference compilers + restart verifier (592 runs) | **directly tests the serialized commitment–cut coordinates; can falsify the theorems** |
| ② **configured-pipeline diagnostic** | matched matrix, external semantic baselines, exact-semantics witnesses, natural workloads | compares observed tool behaviour; **never proves a lower bound** |
| ③ **model-specific consequence** | fixed-total-error synthesis + surface-code calculation | reports consequences under the **disclosed** QRE; **not a hardware-independent forecast** |

## Frame A.2 — Only three experiments can falsify the theory

**Fig 5 — trace-derived frontier (592 runs) $\to$ tests Theorem 4.6.**
Measures the theorem's own coordinates $A_p$, $S$, IR share; the black edge is the measured Pareto set, the theoretical lower envelope evaluated **in the same serialized-bit coordinates**. All frozen points lie in the theorem-allowed region; no point removed as an outlier.
**Falsification: any point below the envelope kills Theorem 4.6.**
(Echo occupies the early-commit corner; full aggregation the state-heavy compact-output corner; three capped hybrids interpolate — matching the three constructions of Part VI.)

**Fig 2 — $\eta$ sweep $\to$ tests Proposition 6 and "two currencies".**
Left: a deferred compact-output compiler pays dispersal in crossing state; slopes $10.3/21.1/43.3$ bytes per unit $\eta$ at $m=32/64/128$, sitting on the zero-error floor $\eta m(\log_23+1)/8$ bytes (ratios $0.99$–$1.05$). *Read the floor:* $\log_23=1.585$ bits of residue $+1$ bit of sign/frame $=2.585$. Right: a streaming compiler pays the same dispersal in committed prefix (slopes $60/129/260$, larger by the public addresses) while its crossing state stays flat at $\le8$ bytes.
**Falsification: no tradeoff between panels, or state channel below the floor.**

**Fig 3 — commitment toll, preregistered $\to$ tests Theorem 4.8 + Corollary 4.9.**
Four serializers at $m\in\{128,512,2048\}$ (two up to $m=32768$), every cell restart-verified:
- matches $\log_2\binom mk/k$ within $0.17$ bits worst case, $0.02$ typically;
- **flat in $m$** at fixed $\eta$ ($2.11/1.99/1.97$ at $\eta=\frac12$ across a $16\times$ range);
- **exactly zero at $\eta=1$**;
- **exactly zero at every $\eta$ in the control** (prefix omits the mask, recovers it from the suffix).

These are precisely the four assertions of Corollary 4.9. The last one shows **irreversibility of commitment, not addressing, is what buys the asymmetry.** Right panel: under an identity-optimal serializer the ratio is $1.00$ at $\eta=1$ and $\le2.64$ throughout — the $6{:}1$ of Fig 2 is **codec slack**, and only the slack grows with address width ($5.4{:}1$ at $m=128$ to $10.8{:}1$ at $m=32768$). **The preregistration recorded "there is no address-width law here" as a prediction against the natural reading of Fig 2, and it is reported as such.**
**Falsification: toll growing with $m$, or nonzero in the control, or nonzero at $\eta=1$.**

## Frame A.3 — Diagnostics (class ②): what they do and do not show

- **Fig 8 + Table VII — mechanism ablation.** With Fourier-layer IR disabled, the compiler completes at 4k/10k/20k but materializes outputs of the same order as `qiskit opt3`, and exceeds the 600 s budget at 50k/100k; enabled, it returns the same 42-gate circuit at every scale. **The constant form is caused by semantic lifting + coefficient aggregation, not by a lucky pass ordering.** (This is the only experiment answering that objection.)
- **Fig 6/7 + Tables XIII/XIV — exact-semantics witnesses (Corollary 1, $\varepsilon=0$, fixed width).** Semantic UCC constant (42 rational / 27 irrational). **Rebased TKET PauliSimp recovers a small validated form at all five scales (52–73 / 35–38)** — the classification's *positive* prediction. staq / `qiskit opt3` / GuidedPauliSimp grow linearly. **None of these is an impossibility result.**
- **Fig 4 — matched matrix (1080 cells).** Same target, basis, budget, seed; **only the representation varies.** (a) certified completion probability, (b) serialized output size among completed cells only. masked-share $\times$ Qiskit L3 completes at $0.38$ (`predicate_error`), **retained as a status observation, never scored as a numerical loss.**
- **Tables V/VI.** Table V is explicitly **not** an instance of the masked-share lower bound (balanced encoding tokens contain $x_j/r$, hence leak the aggregate). Table VI tests Prop 13: output constant in $r$, $O(m_{\mathrm{CP}})=O(n(n-1)/2)$ across widths.
- **Certificate audit.** 56 adversarial mutations (angle, sign, support bit, qubit permutation, Clifford frame, deletion, duplication) with **0 false accepts**; 12 dense/symbolic cross-checks at $n\le6$ with no disagreement. This is what makes "only `completed_valid` enters quality means" meaningful.

## Frame A.4 — The E7 preregistered TKET scan: report, do not repair

$m\in\{8,16,32,64,128\}$, three seeds, byte-identical pass sequence. TKET achieved compact output in **every** cell (508 dispersed rotations $\to$ 127 non-Clifford $R_z$ at $m=128$); its pass-phase memory and serialized IR grew with log–log slope $\approx1.7$ in $m$, while the instrumented semantic-input control stayed flat ($196\to199$ bytes over a $16\times$ range).

**The preregistered point prediction of exactly linear growth was rejected under its own frozen decision rule, and is reported as rejected.**

Two scope limits, stated explicitly:
1. What is measured at a third-party API boundary is a pass-phase memory and serialized-IR snapshot — **class ②; not promoted to a measurement of $\Bcut$, and not commensurable with the $S$ of the frontier.** The scan tests only the qualitative dichotomy (dispersed input forces growth in $m$; semantic input does not) — neither the constant nor the exponent.
2. Superlinear growth means **the floor is not the binding constraint on this tool**: the bound establishes the floor, the observed cost exceeds it, and the excess is implementation structure (the pairwise commutation structure of a Pauli graph is itself superlinear in the number of terms). **No claim that our implementation outperforms these tools.**

## Frame A.5 — Consequences (class ③): the QRE campaign

Table VIII + Fig 9 + Fig 13, **288 rows**. One fixed $\varepsilon_{\mathrm{total}}$ split additively: $0.10$ algorithmic, $0.45$ rotation synthesis, $0.45$ logical failure. **Every angle actually synthesized** by a frozen deterministic GMP build of staq `grid_synth` (670 angle–precision pairs; reported error never exceeds the allocated radius).

Across all 96 matched target/error/allocation/QEC/factory settings: materialize-first uses **385–1753$\times$** the logical $T$ states and **538–5573$\times$** the spacetime volume of semantic-first. **No reversal in the scanned grid.**

**Two things to volunteer:**
1. This is **not** a claim that our implementation dominates other semantic tools — external **TKET PauliSimp uses 0.443–0.536$\times$ our $T$ states** on this witness, i.e. it is better, and crediting that recovery is part of the comparison.
2. Absolute physical numbers still depend on routing, correlated errors, factory layout, feed-forward and code-distance assumptions. **Not a hardware-independent forecast.**

## Frame A.6 — Honest nulls and anti-regression

- **Fig 10 / Table IX — real instances.** Parity with `qiskit opt3`; $\approx65\%/73\%/78\%$ gate reduction against the upstream UCC v0.4.12 pre-semantic default. **The paper explicitly states this is an anti-regression check, not evidence of semantic recovery.**
- **Fig 11/12 + Table X — W8 six-factor ablation (21,060 cells).** Preset recognizer largest main effect (mean reduction $364.9$, bootstrap CI $[349.8,380.5]$); **selector, cache/reuse and projected-block selection have exactly zero isolated effect.** Both negative controls show zero all-on-minus-all-off differences in gates, depth, CX, logical $T$ and spacetime. **Five structured families meet the predeclared all-size/all-seed criterion; QFT arithmetic and phase-polynomial blocks do not and are retained in the table.**

## Frame A.7 — The falsifiability one-liner (最后一帧，全场最强装备)

一页大字：

> **Only three experiments can falsify my theorems: Fig 5 (the frontier envelope), Fig 2 (the two channels and the floor), Fig 3 (the four predictions of the toll).**
>
> **Everything else is either a configured-pipeline diagnostic or a consequence under a disclosed model — I use none of it to support any lower bound.**
>
> **Two third-party preregistrations failed; I report them rather than repair them.**

**中文 note**：这句话把"你的实验能证明什么"这个开放式攻击，压缩成一个你已经先答完的封闭问题。

## Frame A.8 — Reproducibility (one slide, only if asked)

- Canonical registry `data/manifest.yaml`; normalized Parquet index with **24,748 unique records**, retaining **48 predicate-error rows outside quality means**.
- Primary key: `experiment_id, instance_id, representation_id, method_id, seed, backend_hash, tool_version, artifact_commit, config_hash`.
- Every printed number traced to a unique source row via `data/provenance_map.yaml`, tested by `tests/test_paper_number_provenance.py`.
- One-command entry point `reproducibility/run_submission.sh`: reruns audits, regenerates all tables/figures, executes the test suite, builds the manuscript, rejects unresolved references.
- Clean-room runner: independent temporary directory + fresh environment on locked packages; reconstructs 9 headline-theorem tests, one certified QAOA/Ising instance through both paths, 17 deterministic synthesis pairs. **This is working-directory isolation, not host-binary independence.**

---

## 施工检查清单（Claude Code 请逐项确认）

- [ ] Part I–VI 的顺序严格为 §0 → §1 → §2 → §3 → §4 → §5，无重排。
- [ ] Frame 1.3 的「为什么是 $\sin(\Theta/4)$」callout 存在且视觉突出。
- [ ] Frame 3.4 的常数 schedule 反例 callout 存在。
- [ ] Frame 4.4 的「$K=Q-1$ 是为了 fooling set」独立成帧。
- [ ] Frame 5.5 的 frontier 图按规范用 TikZ 绘制，含孤立的 semantic 点及其引线说明。
- [ ] Frame 5.6 的七条假设表格在正文（非 backup）中。
- [ ] 公式编号 $(0.1)$、$(0.2)$、$(3.1)$、$(3.2)$、$(4.1)$–$(4.6)$ 全部显式打出并被后续引用。
- [ ] 每帧有中文 `\note{}`。
- [ ] 附录以 `\appendix` 开始，Frame A.1（证据分级）位于附录首位。
- [ ] 全文无一处把门数/节点数换算为比特数的表述。
- [ ] 编译零错误、零未解析引用。
