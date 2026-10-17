---
{
  "title": "读懂 SUPPA2：从转录本丰度到 PSI，再到差异剪接",
  "slug": "suppa2-psi-biology-statistics",
  "summary": "用图理解七类剪接事件与 TPM 计算，串起 PSI、ΔPSI、经验 p 值和 BH 校正，并结合 Nature 系列论文整理候选筛选与验证建议。",
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

整理 SUPPA2 笔记时，最容易混淆的是四件事：转录本表达多少、某种剪接形式占多少、两组相差多少，以及差异有多可靠。这篇记录按 TPM → PSI → ΔPSI → 统计检验的顺序，把计算和判读连起来。

文中数字均为教学示例，算术已复核，未运行真实 RNA-seq 分析。

## 先把 SUPPA2 放回完整流程

SUPPA2 根据注释定义局部事件，再用上游估计的转录本丰度计算 PSI；这些步骤不直接读取 BAM 计数剪接连接 reads。

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

GTF、定量参考和转录本 ID 必须对应。差异分析需要生物学重复，技术重复和 reads 数不能充当独立样本数。

`generateEvents` 从注释枚举候选事件，是否在样本中发生还需表达证据。高质量参考注释可直接使用，不要求先组装；新组装须另做质控。[官方文档](https://github.com/comprna/SUPPA#overview)

## 七类事件，先认结构，再认分子

SUPPA2 的 `SE SS MX RI FL` 五个选项对应七类局部事件，`SS` 同时生成 A5/A3，`FL` 同时生成 AF/AL。

[![SE、RI、A5、A3的两种转录本形式：橙色为可变区域，F1为PSI分子](../../../assets/uploads/suppa2-psi/seven-events-basic.svg)](../../../assets/uploads/suppa2-psi/seven-events-basic.svg)

*图 1｜SE、RI、A5、A3。统一按正链 5′→3′ 绘制；RI 斜线区域表示保留内含子。*

[![MX、AF、AL的结构示意：内部外显子二选一，或更换首末外显子](../../../assets/uploads/suppa2-psi/seven-events-ends.svg)](../../../assets/uploads/suppa2-psi/seven-events-ends.svg)

*图 2｜MX、AF、AL。F1 的定义按 SUPPA2 约定，负链解释应回到 `.ioe`。*

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

读 ΔPSI 前，先查 `.ioe` 的分子定义。SE 的“包含”较直观，AF、AL、MX 则要按具体形式解释。

## TPM 提供丰度估计，PSI 表达局部比例

TPM（Transcripts Per Million）的基本思想，是先按有效长度校正分配到转录本的片段量，再在样本内归一到百万：

$$
R_i=\frac{\widehat N_i}{L_i^{\mathrm{eff}}},\qquad
\mathrm{TPM}_i=\frac{R_i}{\sum_jR_j}\times10^6.
$$

$\widehat N_i$ 是估计分配的片段量。Salmon 会处理共享 reads、多重比对和偏差，`NumReads` 可为非整数，有效长度也不等于简单的注释长度。[Salmon 输出说明](https://salmon.readthedocs.io/en/latest/file_formats.html)

[![TPM计算示意：片段量除以有效长度，得到200、100、200；总和500，再分别缩放到400000、200000、400000](../../../assets/uploads/suppa2-psi/tpm-normalization.svg)](../../../assets/uploads/suppa2-psi/tpm-normalization.svg)

*图 3｜先校正长度，再按全样本校正值之和归一到百万。横条只表示有效长度。*

A、C 校正后丰度相同。TPM 仍是相对丰度估计，不能保证消除全部偏差，也不等于绝对分子浓度；跨样本差异表达需另做统计分析。

下文 GeneA 使用另一组独立示例数值。

## PSI 的关键在分母：不是全基因所有转录本

对局部事件 $e$，设 $I_e$ 是 `.ioe` 第 4 列规定的分子集合，$T_e$ 是第 5 列规定的事件相关总集合，且 $I_e\subseteq T_e$。则：

$$
\Psi_{e,s}=\frac{\sum_{i\in I_e}\mathrm{TPM}_{i,s}}
{\sum_{j\in T_e}\mathrm{TPM}_{j,s}}.
$$

分母大于零且通过过滤时，PSI 在 $[0,1]$ 内，乘以 100 即百分数。

假设考察 GeneA 的 E2 跳跃事件：T1、T2 经过 E1–E2–E3；T3 从 E1 直接连接 E3；T4 从 E3 才开始，不覆盖这个局部选择。

[![GeneA的四条转录本与PSI分母：T1和T2包含E2，T3跳过E2，T4不覆盖事件，因此PSI等于40除以60](../../../assets/uploads/suppa2-psi/event-denominator.svg)](../../../assets/uploads/suppa2-psi/event-denominator.svg)

*图 4｜转录方向为 5′→3′，结构与丰度均为示意，外显子未按真实长度绘制。点击可看大图。*

当 T1、T2、T3、T4 的 TPM 分别为 30、10、20、15 时：

$$
\Psi=\frac{30+10}{30+10+20}=\frac{2}{3}\approx0.667.
$$

T4 属于同一基因，但不进入这个事件的分母。PSI 约 0.667 指事件相关转录本的丰度占比，不是细胞占比，也不是全基因表达占比。

## 0、1 与 NaN，需要分开读

沿用图 4 的事件定义：

| T1、T2、T3、T4 的 TPM | PSI | 合适的解释 |
| --- | --- | --- |
| 30、10、20、15 | 0.667 | 估计丰度中，约 66.7% 属于包含型 |
| 50、0、0、10 | 1 | 本次估计只给包含型分配了正丰度 |
| 0、0、45、10 | 0 | 事件分母为正，但分子估计为零 |
| 0、0、0、0 | NaN | 事件总丰度为零，比例无定义 |
| 0、0、0、80 | NaN | 基因仍有 T4 的表达，但事件相关总丰度为零 |

**0 表示分子估计为零，NaN 表示比例无法计算。** PSI 为 1 也只是当前估计的边界值，不能证明另一形式绝对不存在；零丰度不足以证明基因沉默。

低于 `psiPerEvent -f` 的事件总丰度阈值可产生 `nan`；转录本 ID 缺失可产生 `NA`。这些值都要查原因，不能填成 0。[PSI 计算源码](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/psiCalculator.py)

核对版本的 `diffSplice -nan` 默认为 0，任一组出现缺失 PSI 就可能被排除，无须等到整组缺失。若允许部分缺失，应预先规定比例并报告有效样本数。

## ΔPSI 回答变化多少，方向由输入顺序决定

若输入顺序为 Control、Treatment，默认按均值计算：

$$
\Delta\Psi=\overline\Psi_{\mathrm{Treatment}}-
\overline\Psi_{\mathrm{Control}}.
$$

例如，三个独立对照样本的 PSI 为 0.15、0.20、0.25，三个处理样本为 0.60、0.65、0.70，两组均值分别是 0.20 和 0.65，故 ΔPSI 为 +0.45。

对图 4 的 SE 事件，这表示包含率升高 **45 个百分点**。写成“提高 45%”会混淆百分点与相对变化。若为 RI，正值表示所定义保留型的比例升高；其他事件仍需回到分子定义解释。

`-me` 可改用中位数差。交换组别会改变符号，命令、图注与结果表须保持一致。[命令与方向说明](https://github.com/comprna/SUPPA#dpsi-file)

此例只演示效应量。SUPPA2 的经验 p 值还依赖其他事件构成的背景，不能由这六个示意值直接推出。

## 经验 p 值怎样来，不能只看差值大小

低丰度常伴随较大的定量不确定性。相同的 ΔPSI，可能因重复间波动和参考分布不同而得到不同 p 值。

SUPPA2 论文的思路，是把组间变化放到**表达水平相近的事件所呈现的组内重复波动**中比较。对局部事件，相关丰度来自定义该事件的转录本总 TPM，不是简单使用全基因 TPM。[SUPPA2 原始论文](https://doi.org/10.1186/s13059-018-1417-1)

实现上，对事件总 TPM 取 $\log_{10}$，在表达相近处取局部窗口作为参考，`-a` 控制窗口点数。

经验 p 值的具体尾部计算依版本而定，复现时应核对[固定源码](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/lib/diff_tools.py#L266)。有限背景可能产生数值零，不表示随机发生的概率绝对为零；p 值也不是“事件为假的概率”。

## 多重检验：先说清楚校正的是哪一组事件

若 10,000 个原假设均成立、各检验的水平为 0.05，未校正时假阳性数的期望为 500。因此大规模筛查还需处理多重检验。

FDR 是发现集合中假发现比例的期望 $E[V/\max(R,1)]$。BH 在检验独立或满足特定正相关条件时控制 FDR；调整 p 值记作 `p_adj`，不等于单个事件的假阳性概率，也不能与其他方法的 q-value 无条件等同。

[![差异剪接结果解读：先检查PSI有效性，再核对效应量，最后区分原始p值、基因内BH和同一比较全事件BH；基因内校正不等于跨基因统一校正](../../../assets/uploads/suppa2-psi/inference.svg)](../../../assets/uploads/suppa2-psi/inference.svg)

*图 5｜校正方法与检验家族必须一起报告。多个比较、分类型分别运行等情形，需要另行明确校正范围。*

### BH 不是只乘一次排名系数

将同一检验家族的 $m$ 个有效原始 p 值排序后，完整的 BH 调整为：

$$
p^{\mathrm{BH}}_{(i)}=
\min\left\{1,\min_{j\geq i}\left(\frac{m}{j}p_{(j)}\right)\right\}.
$$

反向取最小值保证结果单调；仅算 $p_{(i)}m/i$，或只拿出全表几行，都不能保证得到最终 BH 值。[R 的 BH 实现](https://github.com/wch/r-source/blob/trunk/src/library/stats/R/p.adjust.R)

例如一个家族只有 0.010、0.011 两个 p 值，中间量为 0.020、0.011；反向取最小值后，两项最终都是 0.011。

### 用一套完整的小例子重新算

假设一个检验家族只有五个有效事件。以下原始 p 值为人为设定，用于演示 BH，与前面的 PSI 示例独立。

| 事件 | ΔPSI | 原始 p 值 | $mp/i$ 中间量 | 最终 BH `p_adj` | 若预设 $\lvert\Delta PSI\rvert\geq0.10$ 且 `p_adj < 0.05` |
| --- | --- | --- | --- | --- | --- |
| E1 | +0.55 | 0.0001 | 0.0005 | 0.0005 | 通过 |
| E2 | +0.03 | 0.0002 | 0.0005 | 0.0005 | 未达预设效应量门槛 |
| E3 | −0.45 | 0.0200 | 0.033333… | 0.033333… | 通过 |
| E4 | +0.15 | 0.0400 | 0.0500 | 0.0500 | 等于 0.05，不满足严格小于 |
| E5 | −0.20 | 0.2000 | 0.2000 | 0.2000 | 未达统计门槛 |

若另有无法有效检验的事件，应单独记录缺失或排除原因；本例的 $m=5$ 已明确限定为五个有效检验。真实流程不能先挑出原始 p 显著的事件，再只对它们做 BH；缺失、预过滤和多个比较的处理规则也应事先说明。

E2 未达到预设效应量门槛，不代表没有生物学意义；大效应也不自动证明功能改变。具体筛选建议见下节。

### `.dpsi` 的 `p-val` 列，到底是什么？

对本次核对的官方提交 `f41febf`，经验方法最终输出逻辑为：

| 设置 | `p-val` 数值的含义 |
| --- | --- |
| `-m empirical`，不加 `-gc` | 未做多重校正的经验 p 值 |
| `-m empirical -gc` | 同一基因内部的 BH 调整 p 值 |
| 希望按同一比较的全部有效事件统一校正 | 保留未加 `-gc` 的原始结果，明确检验家族后另做 BH |

**基因内校正不等于跨基因所有事件统一校正。** `.dpsi` 的列名不会替你说明这个范围。也不要把已经校正的值再次当原始 p 值送入 BH。[校正与最终写出逻辑](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/lib/diff_tools.py#L631)

以上结论限定于核对提交的 empirical 路线。正式分析应记录安装来源、提交和依赖版本。

### 高水平期刊怎么筛，实际分析怎样选？

论文通常结合效应量和显著性筛选，有时还要求多个比较一致。以下是具体实例，不是期刊统一规定：

| 论文实例 | 文中筛选条件 | 借鉴时要注意 |
| --- | --- | --- |
| [人胚胎异构体图谱，Nature Communications，2023](https://www.nature.com/articles/s41467-023-42558-y) | SUPPA2；$\lvert\Delta PSI\rvert>0.10$ 且 p < 0.05 | 该段写的是 p-value，不能自行改称全事件 BH-FDR |
| [胶质瘤剪接研究，Nature Communications，2022](https://www.nature.com/articles/s41467-022-28253-4) | 包含率变化 >15 个百分点，FDR < 0.05；分析使用 rMATS 与 SUPPA2 | 工具和事件定义不同，不能直接搬用另一工具的统计量 |
| [NCBP1 应激与 S6K1 剪接，Nature Chemical Biology，2026](https://www.nature.com/articles/s41589-025-02135-4) | SUPPA2；调整 p ≤ 0.05，并在三个处理–对照比较中至少两个满足要求 | 说明多对照一致性也可参与筛选；该规则针对其多对照设计 |

据此，下面给出筛选起点。其中全事件 BH 是本文建议，不代表上述论文均采用此方案：

| 目的 | 建议起点 | 后续检查 |
| --- | --- | --- |
| 常规候选筛选 | $\lvert\Delta PSI\rvert\geq0.10$，同一比较全体有效事件 BH `p_adj < 0.05` | 检查表达、缺失、重复分布和剪接连接支持 |
| 优先安排 RT-PCR 等验证 | 在前一候选集内优先考虑 $\lvert\Delta PSI\rvert\geq0.20$ | 再看结构清晰度、引物可设计性和研究相关性；小效应不直接删除 |
| 探索性筛选 | $\lvert\Delta PSI\rvert\geq0.10$、原始经验 p < 0.05；若加 `-gc`，另标基因内 `p_adj < 0.05` 的集合 | 同时提供全事件 BH 列作比较；未通过统一校正的结果保留为探索候选 |

阈值在分析前确定，并报告 0.10、0.15、0.20 等效应量门槛下结果是否稳定；不要根据“显著事件够不够多”反复调参数。若目标是复现某篇论文，应保留其严格/非严格不等号、校正范围和全部过滤条件。

## 留下一份更稳妥的命令备忘

以下 Bash 模板尚未运行。矩阵以制表符分隔，表头仅写样本名；各行以 ID 开头。PSI、TPM 的样本顺序及各组事件定义必须一致。

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

效应量筛选放在校正之后，保留未入选事件。此 R 模板尚未用真实文件运行；使用时记录输入、参数、样本数和版本，检查日志。

超过缺失阈值的事件可写出 `ΔPSI=nan、p=1`，因此应同时核对 ΔPSI、输入 PSI 和排除记录。

## 读结果表时，留下四个问题

读每行结果，依次检查：

1. **定义**：分子是哪种局部形式，分母包含哪些转录本？
2. **可计算性**：丰度足够吗，有没有缺失、ID 错配或重复质量问题？
3. **效应**：ΔPSI 的方向和幅度是什么，各生物学重复是否一致？
4. **证据**：统计量来自哪种方法，校正针对哪个检验家族？

候选事件还需结合剪接连接 reads、结构可视化及实验验证。阈值负责筛选，功能结论需要另外的证据。

## 核对依据

- [Trincado 等，SUPPA2，Genome Biology（2018）](https://doi.org/10.1186/s13059-018-1417-1)：表达相关不确定性与差异剪接方法。
- [SUPPA 官方说明，固定到本次核对提交](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/README.md)：事件、输入输出和运行约定。
- [PSI 计算实现](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/psiCalculator.py)、[差异分析参数](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/significanceCalculator.py)、[差异检验与校正实现](https://github.com/comprna/SUPPA/blob/f41febfb5be8f6257428150e701d187d49d542b0/lib/diff_tools.py)：核对日期为 2026-10-17，不代表用户本地已安装版本。
- [Salmon 输出格式](https://salmon.readthedocs.io/en/latest/file_formats.html)：有效长度、TPM 与估计片段量。
- [R `p.adjust` 源码](https://github.com/wch/r-source/blob/trunk/src/library/stats/R/p.adjust.R)：核对 BH 的反向累积最小值步骤。
