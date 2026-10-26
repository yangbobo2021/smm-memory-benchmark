"""Render shareable charts directly from the archived experiment summaries.

Requires matplotlib 3.10.7. No model, embedding service, or network is used.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

for font_path in (
    Path("/System/Library/Fonts/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
):
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(font_path)).get_name()
        break
plt.rcParams.update({
    "font.size": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#94A3B8",
    "axes.labelcolor": "#334155",
    "xtick.color": "#475569",
    "ytick.color": "#334155",
    "svg.fonttype": "path",
    "savefig.facecolor": "white",
})

BLUE = "#2563EB"
GREEN = "#059669"
AMBER = "#D97706"
PURPLE = "#7C3AED"
GRAY = "#CBD5E1"


def read(rel: str):
    return json.loads((ROOT / rel).read_text())


def save(fig, name: str) -> None:
    fig.savefig(HERE / f"{name}.png", dpi=180, bbox_inches="tight", pad_inches=0.3)
    svg_path = HERE / f"{name}.svg"
    fig.savefig(svg_path, bbox_inches="tight", pad_inches=0.3)
    svg_path.write_text("\n".join(line.rstrip(" \t") for line in svg_path.read_text().splitlines()) + "\n")
    plt.close(fig)


def stage1() -> None:
    source = read("experiments/smm-baseline-001/artifacts/high-effort-comparison-v1/comparison.json")
    names = ["GPT-6 Luna", "GPT-6.1 Sol", "GLM-5.3 Flash", "GLM-5.3", "DeepSeek Flash"]
    ids = ["gpt-6-luna", "gpt-6.1-sol", "glm-5.3-flash", "glm-5.3", "deepseek-flash"]
    pairs = {p["model"]: p for p in source["pairs"]}
    values = []
    for model in ids:
        pair = pairs[model]
        row = []
        for effort, task in (("low", "oracle_answer"), ("low", "candidate_answer"),
                             ("high", "oracle_answer"), ("high", "candidate_answer")):
            summary = pair[effort]["summary"][task]
            assert summary["primary_denominator"] == 23
            row.append(summary["primary_correct"])
        values.append(row)
    assert values == [[21, 19, 23, 23], [23, 23, 23, 23], [23, 21, 23, 21],
                      [20, 21, 23, 21], [23, 22, 23, 23]]
    arr = np.array(values)
    fig, ax = plt.subplots(figsize=(10.2, 4.5))
    ax.imshow(arr, cmap="Blues", vmin=18, vmax=23, aspect="auto")
    ax.set_xticks(range(4), ["Low\n准确输入", "Low\n混合候选", "High\n准确输入", "High\n混合候选"])
    ax.set_yticks(range(5), names)
    ax.set_title("阶段 1｜给到资料后，模型能否答对？", loc="left", fontweight="bold", pad=20)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(j, i, f"{arr[i, j]}/23", ha="center", va="center",
                    color="white" if arr[i, j] >= 22 else "#0F172A", fontweight="bold", fontsize=13)
    ax.tick_params(length=0, pad=10)
    for edge in np.arange(-.5, 5, 1):
        ax.axhline(edge, color="white", linewidth=4)
    for edge in np.arange(-.5, 4, 1):
        ax.axvline(edge, color="white", linewidth=4)
    fig.text(.13, .01, "准确输入＝官方相关完整对话；混合候选＝BM25 Top5 ∪ 向量 Top5 的完整对话。仅23道清晰题。",
             fontsize=9.5, color="#64748B")
    fig.tight_layout(rect=[0, .07, 1, 1])
    save(fig, "stage1_models")


def stage2_candidates() -> None:
    source = read("analyses/five-candidate-routes-001/results.json")["summary"]["total"]
    keys = ["bm25_top5", "vector_top5", "bm25_top5_vector_top5", "bm25_top10"]
    names = ["BM25 Top5", "向量 Top5", "两路各 Top5 合并", "BM25 Top10"]
    colors = [BLUE, AMBER, PURPLE, GREEN]
    counts = [source[k]["all"] for k in keys]
    assert [source[k]["cases"] for k in keys] == [232] * 4
    assert counts == [199, 153, 208, 211]
    average = [source[k]["candidate_total"] / 232 for k in keys]
    fig, ax = plt.subplots(figsize=(10.2, 4.4))
    y = np.arange(len(keys))
    bars = ax.barh(y, np.array(counts) / 232 * 100, color=colors, height=.58)
    ax.invert_yaxis()
    ax.set_yticks(y, names)
    ax.set_xlim(0, 107)
    ax.set_xlabel("全部必要信息取齐的题目比例（%）")
    ax.set_title("阶段 2｜相同题目下，哪种候选路线够用？", loc="left", fontweight="bold", pad=18)
    ax.xaxis.grid(True, color="#E2E8F0")
    ax.set_axisbelow(True)
    for bar, count, avg in zip(bars, counts, average):
        ax.text(bar.get_width() + 1.2, bar.get_y() + bar.get_height() / 2,
                f"{count}/232 · 平均 {avg:.1f} 段", va="center", fontsize=10.5, color="#0F172A")
    fig.text(.17, .01, "232道可明确判断的题；25道歧义题单列。取齐的是事前审核的回答依赖，不是回答正确率。",
             fontsize=9.5, color="#64748B")
    fig.tight_layout(rect=[0, .07, 1, 1])
    save(fig, "stage2_methods")


def stage2_scale() -> None:
    source = read("experiments/smm-bm25-scale-1000-002/summary.json")["by_cohort"]
    groups = [("P25", 25), ("L32", 32), ("C200", 200)]
    before = [source[g]["original"]["top5"]["all"] for g, _ in groups]
    after = [source[g]["expanded"]["top5"]["all"] for g, _ in groups]
    assert before == [25, 20, 156] and after == [18, 15, 156]
    fig, ax = plt.subplots(figsize=(10.2, 4.2))
    x = np.arange(3)
    width = .32
    ax.bar(x - width / 2, [v / n * 100 for v, (_, n) in zip(before, groups)], width,
           color=BLUE, label="原题历史（19–62段）")
    ax.bar(x + width / 2, [v / n * 100 for v, (_, n) in zip(after, groups)], width,
           color=AMBER, label="混合1000段")
    for i, ((_, n), b, a) in enumerate(zip(groups, before, after)):
        ax.text(i - width / 2, b / n * 100 + 2, f"{b}/{n}", ha="center", fontsize=10)
        ax.text(i + width / 2, a / n * 100 + 2, f"{a}/{n}", ha="center", fontsize=10)
    ax.set_ylim(0, 112)
    ax.set_xticks(x, ["原25题 P25", "新32题 L32", "LoCoMo 200题"])
    ax.set_ylabel("Top5取齐全部官方参考的题目比例（%）")
    ax.set_title("规模压力测试｜混合1000段后的结果", loc="left", fontweight="bold", pad=31)
    ax.legend(loc="upper right", bbox_to_anchor=(1.0, 1.13), frameon=False, ncol=2)
    ax.yaxis.grid(True, color="#E2E8F0")
    ax.set_axisbelow(True)
    fig.text(.14, .01, "三组的1000段池均混有其他历史，不代表同一用户长期累积1000段。", fontsize=9.5, color="#64748B")
    fig.tight_layout(rect=[0, .07, 1, 1])
    save(fig, "stage2_scale")


def stage3() -> None:
    source = read("experiments/smm-person-time-1000-pilot-001/results.json")
    cases = source["cases"]
    assert len(cases) == 12 and all(c["id"].startswith("C") for c in cases)
    keys = ["raw_all", "authored_all", "authored_person", "authored_person_time"]
    names = ["原问题", "关键词输入", "＋姓名入口", "＋明确日期加分"]
    any_hits = [sum(c["methods"][k]["top5_any"] for c in cases) for k in keys]
    all_hits = [sum(c["methods"][k]["top5_all"] for c in cases) for k in keys]
    assert any_hits == [5, 7, 9, 10] and all_hits == [3, 5, 7, 8]
    x = np.arange(4)
    width = .34
    fig, ax = plt.subplots(figsize=(10.2, 4.2))
    b1 = ax.bar(x - width / 2, any_hits, width, color=BLUE, label="至少一条官方参考")
    b2 = ax.bar(x + width / 2, all_hits, width, color=GREEN, label="全部官方参考")
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + .2,
                    f"{int(bar.get_height())}/12", ha="center", fontsize=10.5, fontweight="bold")
    ax.set_xticks(x, names)
    ax.set_ylim(0, 12.6)
    ax.set_ylabel("Top5命中题数")
    ax.set_title("阶段 3｜逐步减少干扰，正确来源更靠前", loc="left", fontweight="bold", pad=18)
    ax.legend(loc="upper left", frameon=False, ncol=2)
    ax.yaxis.grid(True, color="#E2E8F0")
    ax.set_axisbelow(True)
    fig.text(.16, .01, "12道事先挑选的LoCoMo机制题；每次仍从完整1000段开始，无sample_id过滤。不能当总体准确率。",
             fontsize=9.5, color="#64748B")
    fig.tight_layout(rect=[0, .07, 1, 1])
    save(fig, "stage3_filters")


if __name__ == "__main__":
    stage1()
    stage2_candidates()
    stage2_scale()
    stage3()
    print("Generated four PNG and four SVG charts from archived results")
