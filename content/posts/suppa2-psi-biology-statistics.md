---
{
  "title": "读懂 SUPPA2：从转录本丰度到 PSI，再到差异剪接",
  "slug": "suppa2-psi-biology-statistics",
  "summary": "整理 PSI 的生物学含义与计算逻辑：谁进入分母，0、1 与 NaN 如何区分，ΔPSI 的方向怎样判读，以及经验 p 值、基因内校正和全事件 BH 校正究竟是什么关系。",
  "date": "2026-10-17",
  "updated": "2026-10-17",
  "article_type": "note",
  "evidence_status": "literature",
  "category": "学习记录",
  "category_slug": "study",
  "tags": [
    {"name": "SUPPA2", "slug": "suppa2"},
    {"name": "可变剪接", "slug": "alternative-splicing"},
    {"name": "生物信息学", "slug": "bioinformatics"},
    {"name": "统计学", "slug": "statistics"}
  ],
  "sessions": [],
  "code_url": "",
  "data_url": "",
  "draft": false
}
---

整理可变剪接笔记时，一个看似简单的指标反复引出新问题：PSI 的分母到底是谁？PSI 为 0 和缺失有什么不同？ΔPSI 已经很大，为什么统计检验仍然不显著？

重新沿着 SUPPA2 的数据流核对之后，理解逐渐清楚了：**丰度、比例、变化幅度和统计证据，回答的是四个不同的问题。** 把它们放回各自的位置，结果表才真正读得懂。

本文保留学习笔记的推演过程，并依据官方文档、论文与源码修正容易混淆的说法。所有数字均为教学示例；算术已复核，未使用真实 RNA-seq 数据，也未实际运行 SUPPA2 分析。

## 先把 SUPPA2 放回完整流程

SUPPA2 的局部事件分析，以注释中的转录本结构和上游估计的转录本丰度为基础。它不在这些步骤中直接读取 BAM、重新计数剪接连接 reads。

```text
同一套转录本注释 / 参考序列
       ├─ GTF → generateEvents → 事件与转录本对应表 .ioe
       └─ RNA-seq 定量 → 每个样本的转录本 TPM
                          ↓
                  psiPerEvent → 每样本 PSI
                          ↓
              生物学重复按条件分组 → diffSplice
                          ↓
                 ΔPSI 与显著性统计量
```

这里有两个前提：GTF 与定量参考应对应，转录本 ID 必须一致；组内还需要能够反映变异的生物学重复。技术重复和测序 reads 不能代替独立生物学样本。

`generateEvents` 是**从已有注释枚举候选事件**，不是仅凭 GTF 证明这些事件都在样本中真实发生。已有高质量参考注释可以直接使用，并不要求先做 StringTie/TACO 组装。新组装也需要额外的质量控制。[官方文档](https://github.com/comprna/SUPPA#overview)

## 七类事件，先认结构，再认分子

SUPPA2 的 `SE SS MX RI FL` 五个选项对应七类局部事件，`SS` 同时生成 A5/A3，`FL` 同时生成 AF/AL。

| 类型 | 结构变化 | PSI 分子对应的形式 |
| --- | --- | --- |
| SE，外显子跳跃 | 包含或跳过中间外显子 | 包含中间外显子的转录本 |
| RI，内含子保留 | 一段内含子保留或被剪除 | 保留该内含子的转录本 |
| A5，可变 5′ 剪接位点 | 使用不同供体位点 | 按官方约定，使该内含子较短的形式 |
| A3，可变 3′ 剪接位点 | 使用不同受体位点 | 按官方约定，使该内含子较短的形式 |
| MX，互斥外显子 | 两种局部形式分别使用不同内部外显子 | 起始基因组坐标较小的可变外显子所在形式 |
| AF，可变第一外显子 | 使用不同首外显子，连接共同下游区域 | 按官方约定，使相应内含子较长的形式 |
| AL，可变末外显子 | 共同上游区域连接不同末外显子 | 按官方约定，使相应内含子较长的形式 |

这些约定来自[官方事件定义](https://github.com/comprna/SUPPA#ioe)。MX 的“坐标较小”不一定等于转录方向上的“更上游”，负链尤其需要注意。A5/A3 的 5′/3′ 也应沿转录方向判断。

MX 描述的是这两种局部形式，不能据此断言同一基因的全部转录本绝不会同时包含或同时跳过那两个区域。AF/AL 可能涉及转录起始或末端加工选择，局部结构本身不足以证明具体调控机制。

这次梳理留下的一个习惯是：**解释 ΔPSI 方向之前，先看 `.ioe` 实际把哪些转录本放进分子。** 对 SE 很直观，对 AF、AL 和 MX 更不能凭“包含率”三个字想当然。

## TPM 提供丰度估计，PSI 表达局部比例

TPM（Transcripts Per Million）的基本思想，是先按有效长度校正分配到转录本的片段量，再在样本内归一到百万：

$$
R_i=\frac{\widehat N_i}{L_i^{\mathrm{eff}}},\qquad
\mathrm{TPM}_i=\frac{R_i}{\sum_jR_j}\times10^6.
$$

这里的 $\widehat N_i$ 是估计分配的片段量。真实转录本定量存在共享 reads、多重比对和偏差校正；Salmon 的 `NumReads` 并不只是唯一比对 reads 的整数计数，有效长度也不总等于注释长度。[Salmon 输出说明](https://salmon.readthedocs.io/en/latest/file_formats.html)

用一个独立的简化例子理解长度校正：

| 转录本 | 估计片段量 | 示例有效长度（kb） | 片段量 / 长度 | 三条转录本构成全样本时的 TPM |
| --- | --- | --- | --- | --- |
| A | 400 | 2 | 200 | 400,000 |
| B | 100 | 1 | 100 | 200,000 |
| C | 800 | 4 | 200 | 400,000 |

A 与 C 的原始片段量不同，长度校正后相同。这说明为何不能直接用原始 reads 数替代转录本丰度，但不代表 TPM 已消除所有误差，或等于真实绝对分子浓度。跨样本差异表达也不能只比较 TPM 就下结论。

下面的 GeneA 数字是**另一个事件示例**，不是把上表的 TPM 随意缩小后继续计算。

## PSI 的关键在分母：不是全基因所有转录本

对局部事件 $e$，设 $I_e$ 是 `.ioe` 第 4 列规定的分子集合，$T_e$ 是第 5 列规定的事件相关总集合，且 $I_e\subseteq T_e$。则：

$$
\Psi_{e,s}=\frac{\sum_{i\in I_e}\mathrm{TPM}_{i,s}}
{\sum_{j\in T_e}\mathrm{TPM}_{j,s}}.
$$

这是样本 $s$ 中、以事件相关转录本为条件的丰度比例；分母大于零且通过过滤时，取值在 $[0,1]$，乘以 100 可写成百分数。

假设考察 GeneA 的 E2 跳跃事件：T1、T2 经过 E1–E2–E3；T3 从 E1 直接连接 E3；T4 从 E3 才开始，不覆盖这个局部选择。

[![GeneA的四条转录本与PSI分母：T1和T2包含E2，T3跳过E2，T4不覆盖事件，因此PSI等于40除以60](../../../assets/uploads/suppa2-psi/event-denominator.svg)](../../../assets/uploads/suppa2-psi/event-denominator.svg)

*图 1｜转录方向为 5′→3′，结构与丰度均为示意，外显子未按真实长度绘制。点击可看大图。*

当 T1、T2、T3、T4 的 TPM 分别为 30、10、20、15 时：

$$
\Psi=\frac{30+10}{30+10+20}=\frac{2}{3}\approx0.667.
$$

T4 虽然属于这个基因，却不进入该事件的分母。因此它改变丰度时，不一定改变这个事件的 PSI。PSI 也不是“67% 的细胞发生了某种剪接”，更不是整个基因表达量的百分比。

## 0、1 与 NaN，需要分开读

沿用图 1 的事件定义：

| T1、T2、T3、T4 的 TPM | PSI | 合适的解释 |
| --- | --- | --- |
| 30、10、20、15 | 0.667 | 估计丰度中，约 66.7% 属于包含型 |
| 50、0、0、10 | 1 | 本次估计只给包含型分配了正丰度 |
| 0、0、45、10 | 0 | 事件分母为正，但分子估计为零 |
| 0、0、0、0 | NaN | 事件总丰度为零，比例无定义 |
| 0、0、0、80 | NaN | 基因仍有 T4 的表达，但事件相关总丰度为零 |

**PSI 为 0 不等于基因不表达；NaN 也不等于完全跳过。** 同样，PSI 为 1 只是当前注释和定量结果下的边界估计，不能证明真实样本绝对不存在跳过型。估计为零也不宜直接写成“基因沉默”。

实际文件还会出现另外两类问题：`psiPerEvent -f` 可将事件总丰度低于阈值的样本记为 `nan`；`.ioe` 所需的转录本 ID 若在表达矩阵中找不到，源码可能输出 `NA`。二者都需要追踪原因，不能统一填成 0。[PSI 计算源码](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/psiCalculator.py)

还要区分“每个样本的 PSI 缺失”和“差异分析无法给出 ΔPSI”。核对版本中，`diffSplice -nan` 默认是 0：**任一条件存在缺失 PSI，就可能因缺失比例超阈值而被排除**，不需要整组全部缺失。放宽阈值会改变纳入规则，不能只是为了得到更多结果而随意调整。

## ΔPSI 回答变化多少，方向由输入顺序决定

若输入顺序为 Control、Treatment，默认按均值计算：

$$
\Delta\Psi=\overline\Psi_{\mathrm{Treatment}}-
\overline\Psi_{\mathrm{Control}}.
$$

例如，三个独立对照样本的 PSI 为 0.15、0.20、0.25，三个处理样本为 0.60、0.65、0.70，两组均值分别是 0.20 和 0.65，故 ΔPSI 为 +0.45。

对图 1 的 SE 事件，这表示包含率升高 **45 个百分点**。写成“提高 45%”会混淆百分点与相对变化。若为 RI，正值表示所定义保留型的比例升高；其他事件仍需回到分子定义解释。

SUPPA2 也提供 `-me`，改用中位数差。交换两组输入会改变符号，因此命令、图注和结果表的方向必须一致。[命令与方向说明](https://github.com/comprna/SUPPA#dpsi-file)

这个例子只演示效应量，**不能从六个示意 PSI 值直接推出下面的经验 p 值**。经验方法还依赖其他事件形成的表达相关背景分布。

## 经验 p 值怎样来，不能只看差值大小

低丰度往往伴随较大的定量不确定性，但“总 TPM 为 500 时 ΔPSI=0.2 就极其显著”不是可直接使用的规则。统计证据还取决于重复间变异和参考分布。

SUPPA2 论文的思路，是把组间变化放到**表达水平相近的事件所呈现的组内重复波动**中比较。对局部事件，相关丰度来自定义该事件的转录本总 TPM，不是简单使用全基因 TPM。[SUPPA2 原始论文](https://doi.org/10.1186/s13059-018-1417-1)

核对的实现中，会对每个样本的事件总 TPM 取 $\log_{10}$，构造重复间的 ΔPSI 与丰度背景，并在相近丰度处取局部窗口；`-a` 控制窗口点数。它不是把所有基因放入几个固定表达“桶”。

如果要复现数值，还必须尊重具体实现：本次核对源码中的经验统计量为

$$
p_{\mathrm{impl}}=\frac{1-\widehat F_{|\Delta\Psi_{\mathrm{rep}}|}
(|\Delta\Psi_{\mathrm{obs}}|)}{2},
$$

其中 $\widehat F$ 是局部重复差值绝对值的经验累积分布。这是该版本的实现约定，不能擅自改成另一种尾概率公式后仍称为同一输出，也不应把它当作所有经验检验的通式。有限经验分布产生的数值零，不表示“绝不可能是随机结果”。[固定版本源码](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/lib/diff_tools.py#L266)

读结果时还要避免一个常见误解：p 值不是“这个事件为假的概率”，也不是效应有多大的评分。

## 多重检验：先说清楚校正的是哪一组事件

单个事件的检验，与同时筛查大量事件，是不同层次的问题。若 10,000 个原假设都成立，且每个检验都具有正确的 0.05 水平，未校正时假阳性个数的期望可达 500；这不是某次实验必然会出现的数量。

FDR 定义为发现集合中假发现比例的期望 $E[V/\max(R,1)]$。BH 方法在检验独立或满足特定正相关条件时控制这个量；每行的 BH 调整 p 值，是用于实施这一筛选的数值，不能直接解释成该事件的假阳性概率。这里用 `p_adj` 表示，也不把它与其他方法估计的 q-value 无条件等同。

[![差异剪接结果解读：先检查PSI有效性，再核对效应量，最后区分原始p值、基因内BH和同一比较全事件BH；基因内校正不等于跨基因统一校正](../../../assets/uploads/suppa2-psi/inference.svg)](../../../assets/uploads/suppa2-psi/inference.svg)

*图 2｜校正方法与检验家族必须一起报告。多个比较、分类型分别运行等情形，需要另行明确校正范围。*

### BH 不是只乘一次排名系数

将同一检验家族的 $m$ 个有效原始 p 值排序后，完整的 BH 调整为：

$$
p^{\mathrm{BH}}_{(i)}=
\min\left\{1,\min_{j\geq i}\left(\frac{m}{j}p_{(j)}\right)\right\}.
$$

后面的最小值步骤保证调整结果单调。只写 $p_{(i)}m/i$ 不完整；只拿出几行 p 值和排名，也通常无法还原全表最终调整值。[R 的 BH 实现](https://github.com/wch/r-source/blob/trunk/src/library/stats/R/p.adjust.R)

例如一个家族只有 0.010、0.011 两个 p 值，中间量为 0.020、0.011；反向取最小值后，两项最终都是 0.011。

原笔记中，$0.0001\times1000/1=0.1$，并不是 0.001；但即使改正乘法，这个 0.1 仍只是该排名的中间量，缺少后续 p 值就不能认定它是最终 BH 值。

### 用一套完整的小例子重新算

下面假设**同一比较的检验家族恰好只有五个有效事件**。原始 p 值人为给定，专门用于演示 BH；并非由前面的 PSI 示例检验得出。

| 事件 | ΔPSI | 原始 p 值 | $mp/i$ 中间量 | 最终 BH `p_adj` | 若预设 $\lvert\Delta PSI\rvert\geq0.10$ 且 `p_adj < 0.05` |
| --- | --- | --- | --- | --- | --- |
| E1 | +0.55 | 0.0001 | 0.0005 | 0.0005 | 通过 |
| E2 | +0.03 | 0.0002 | 0.0005 | 0.0005 | 未达预设效应量门槛 |
| E3 | −0.45 | 0.0200 | 0.033333… | 0.033333… | 通过 |
| E4 | +0.15 | 0.0400 | 0.0500 | 0.0500 | 等于 0.05，不满足严格小于 |
| E5 | −0.20 | 0.2000 | 0.2000 | 0.2000 | 未达统计门槛 |

若另有无法有效检验的事件，应单独记录缺失或排除原因；本例的 $m=5$ 已明确限定为五个有效检验。真实流程不能先挑出原始 p 显著的事件，再只对它们做 BH；缺失、预过滤和多个比较的处理规则也应事先说明。

E2 不满足这里的候选筛选规则，但不能写成“没有生物学意义”。小效应仍可能值得研究，大效应也不自动证明功能改变。0.10 或 0.20 是可选择的分析门槛，不存在一个适用于所有物种和实验的“论文发表级标准”。

### `.dpsi` 的 `p-val` 列，到底是什么？

对本次核对的官方提交 `f41febf`，经验方法最终输出逻辑为：

| 设置 | `p-val` 数值的含义 |
| --- | --- |
| `-m empirical`，不加 `-gc` | 未做多重校正的经验 p 值 |
| `-m empirical -gc` | 同一基因内部的 BH 调整 p 值 |
| 希望按同一比较的全部有效事件统一校正 | 保留未加 `-gc` 的原始结果，明确检验家族后另做 BH |

**基因内校正不等于跨基因所有事件统一校正。** `.dpsi` 的列名不会替你说明这个范围。也不要把已经校正的值再次当原始 p 值送入 BH。[校正与最终写出逻辑](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/lib/diff_tools.py#L631)

源码可能演进，其他安装来源也可能不同。因此这一判断绑定到核对的提交，不只依靠“SUPPA2”这个软件名。这里讨论的是 empirical 路线，不将它的输出语义直接套给其他统计方法。

## 留下一份更稳妥的命令备忘

以下是 Bash 模板，不是已运行的实验记录。输入矩阵应为制表符分隔，首行仅写样本名，之后每行由转录本或事件 ID 加样本值组成。每个条件的 PSI 与 TPM 文件，样本列顺序必须一致，所有条件采用相同事件定义。

```bash
# 1. 从统一注释生成事件
python suppa.py generateEvents \
  -i reference.gtf -o all_events -e SE SS MX RI FL -f ioe

# 2. 合并事件定义：首个文件保留表头，其余文件跳过首行
# 建议在独立目录中运行，确认 all_events_*.ioe 只匹配本次生成文件
awk 'FNR == 1 && NR != 1 {next} {print}' all_events_*.ioe > all_events.ioe

# 3. 分别计算两组每个生物学重复的 PSI
# -f 1 是示例：过滤每样本事件总 TPM < 1 的值
python suppa.py psiPerEvent \
  -i all_events.ioe -e Control.tpm -o Control -f 1
python suppa.py psiPerEvent \
  -i all_events.ioe -e Treatment.tpm -o Treatment -f 1

# 4. 经验检验；此处不加 -gc，以保留原始 p 值供后续统一 BH
# -th 1 过滤事件相关丰度，-nan 0 不允许任一组有缺失 PSI
python suppa.py diffSplice \
  -m empirical -i all_events.ioe \
  -p Control.psi Treatment.psi \
  -e Control.tpm Treatment.tpm \
  -th 1 -nan 0 -o Control_vs_Treatment_raw
```

`psiPerEvent -f` 是**每样本的事件总 TPM 过滤**；`diffSplice -th` 则使用事件总 TPM 的对数及跨重复、跨条件汇总进行过滤，不能解释成“删除每条 TPM 小于 1 的转录本”。原笔记的 `-tpm 1.0` 应改为 `-th 1`，长参数是 `--tpm-threshold`。[参数定义源码](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/significanceCalculator.py)

如果研究方案选择基因内校正，可另行加 `-gc` 并明确标注范围。配对设计也不能只看到 `-pa` 就认为任何方法都会按配对模型分析：核对的 empirical 调用不使用该参数构造配对检验，需要结合方法实现选择适合设计的路线。

假设文件只含一个比较，且确认读入的是上述未加 `-gc` 的原始结果，可在 R 中显式生成调整列：

```r
d <- read.delim("Control_vs_Treatment_raw.dpsi",
                header = TRUE, row.names = 1, check.names = FALSE,
                na.strings = c("nan", "NaN", "NA"))
stopifnot(ncol(d) == 2L)  # 本模板只处理一个比较
names(d) <- c("dPSI", "p_raw")

# 此处明确：家族为当前比较中 ΔPSI 与原始 p 均有效的全部事件
ok <- is.finite(d$dPSI) & is.finite(d$p_raw) &
      d$p_raw >= 0 & d$p_raw <= 1
d$p_adj <- NA_real_
d$p_adj[ok] <- p.adjust(d$p_raw[ok], method = "BH")
d$selected <- FALSE
d$selected[ok] <- abs(d$dPSI[ok]) >= 0.10 & d$p_adj[ok] < 0.05
write.table(d, "Control_vs_Treatment_BH.tsv", sep = "\t",
            quote = FALSE, col.names = NA)
```

这里的效应量筛选放在校正之后，也保留了未通过的有效事件。R 代码为读表与校正模板，尚未用真实 `.dpsi` 文件执行；正式分析应记录输入、参数、样本数、软件提交与依赖版本，并检查运行日志。

还有一个不宜漏掉的检查：核对实现对超过缺失阈值的事件可写出 `ΔPSI=nan、p=1`。所以只看 `p-val` 是否缺失，无法识别所有未有效分析的事件，需要同时看 ΔPSI、输入 PSI 和排除记录。

## 读结果表时，留下四个问题

这一轮整理后，PSI 不再只是一个可以代入公式的小数。每次读到一行差异剪接结果，可以依次确认：

1. **定义**：分子是哪种局部形式，分母包含哪些转录本？
2. **可计算性**：丰度足够吗，有没有缺失、ID 错配或重复质量问题？
3. **效应**：ΔPSI 的方向和幅度是什么，各生物学重复是否一致？
4. **证据**：统计量来自哪种方法，校正针对哪个检验家族？

最后再把候选放回结构、表达和功能背景，必要时用连接 reads、可视化和实验验证补充证据。这样，“数值算得出”和“结论站得住”之间的距离，才会更清楚。

## 核对依据

- [Trincado 等，SUPPA2，Genome Biology（2018）](https://doi.org/10.1186/s13059-018-1417-1)：表达相关不确定性与差异剪接方法。
- [SUPPA 官方说明，固定到本次核对提交](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/README.md)：事件、输入输出和运行约定。
- [PSI 计算实现](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/psiCalculator.py)、[差异分析参数](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/significanceCalculator.py)、[差异检验与校正实现](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/lib/diff_tools.py)：核对日期为 2026-10-17，不代表用户本地已安装版本。
- [Salmon 输出格式](https://salmon.readthedocs.io/en/latest/file_formats.html)：有效长度、TPM 与估计片段量。
- [R `p.adjust` 源码](https://github.com/wch/r-source/blob/trunk/src/library/stats/R/p.adjust.R)：核对 BH 的反向累积最小值步骤。
