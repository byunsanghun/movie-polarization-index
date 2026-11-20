"""
결과 그래프 3종을 만들어 results/figures/ 에 PNG로 저장

  fig1_pi_vs_mean.png    PI와 평균 평점의 관계 (영화 10,326편의 겹침 밀도)
  fig2_h3_by_mean_bin.png H3: 평균 평점 구간별 PI 효과 (계수 + 95% 신뢰구간)
  fig3_h2_by_genre.png    H2: 장르별 PI 효과 (계수 + 95% 신뢰구간)

색 규칙
- 투표 수 = 파랑, popularity = 주황 (그림이 달라도 같은 지표는 같은 색)
- 두 색은 색각 이상 환경 검증을 통과한 팔레트의 1·2번 슬롯
- 겹침 밀도는 파랑 한 가지 색의 진하기(연함 → 진함)로만 표현
- 그림 속 숫자는 표(results/*.csv)와 같은 값이며, 그림은 그 값을 옮겨 그린 것

입력: results/pi_by_movie.csv, results/h3_regression.csv, results/h2_regression.csv
실행 방법 (프로젝트 폴더에서):
    python -X utf8 src/make_figures.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "figures"

# ===== 색 (검증된 기본 팔레트, 밝은 배경 기준) =====
SURFACE = "#fcfcfb"
INK = "#0b0b0b"          # 제목·값 라벨
INK2 = "#52514e"         # 축 제목·보조 설명
MUTED = "#898781"        # 눈금·0 기준선
GRID = "#e1e0d9"         # 격자 (실선 헤어라인)
AXIS = "#c3c2b7"
C_VOTE = "#2a78d6"       # 투표 수 (범주 슬롯 1)
C_POP = "#eb6834"        # popularity (범주 슬롯 2)
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]  # 연속형 100→700

DV_COLOR = {"투표 수": C_VOTE, "popularity": C_POP}


def setup_style():
    plt.rcParams.update({
        "font.family": "Malgun Gothic",          # Windows 한글 글꼴
        "axes.unicode_minus": False,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "text.color": INK, "axes.labelcolor": INK2,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
        "axes.axisbelow": True,
        "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    })


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path, dpi=170)
    plt.close(fig)
    print(f"저장: {path.relative_to(ROOT)}")


# ---------------------------------------------------------------- 그림 1
def fig1():
    df = pd.read_csv(RES / "pi_by_movie.csv", usecols=["title", "mean_rating", "PI"])
    r = df["PI"].corr(df["mean_rating"])
    coef = np.polyfit(df["mean_rating"], df["PI"], 2)

    fig, ax = plt.subplots(figsize=(8.4, 5.6))
    cmap = LinearSegmentedColormap.from_list("blue_seq", BLUE_RAMP)
    hb = ax.hexbin(df["mean_rating"], df["PI"], gridsize=34, cmap=cmap, mincnt=1,
                   norm=LogNorm(), linewidths=0.4, edgecolors=SURFACE)
    cb = fig.colorbar(hb, ax=ax, pad=0.02, fraction=0.04)
    cb.set_label("영화 수 (로그 눈금)", color=INK2)
    cb.outline.set_visible(False)
    cb.ax.tick_params(colors=MUTED, length=0)

    xs = np.linspace(df["mean_rating"].min(), df["mean_rating"].max(), 200)
    ax.plot(xs, np.polyval(coef, xs), color=INK, lw=1.8)
    ax.text(1.0, np.polyval(coef, 1.0) + 0.03, "2차 회귀선", color=INK, fontsize=9, ha="left")

    # 값이 가장 큰 두 영화만 직접 표시 (모든 점에 라벨을 붙이지 않음)
    for key, label, dx, dy in [("Santa with Muscles", "Santa with Muscles", 0.08, 0.0),
                               ("Room, The", "The Room", 0.08, 0.0)]:
        row = df[df["title"].str.contains(key, regex=False)].iloc[0]
        ax.scatter(row["mean_rating"], row["PI"], s=42, color=INK, edgecolor=SURFACE, linewidth=1.5, zorder=5)
        ax.text(row["mean_rating"] + dx, row["PI"] + dy, label, fontsize=9, color=INK, va="center")

    ax.set_xlabel("평균 평점")
    ax.set_ylabel("PI (호불호 분열 지수)")
    ax.set_xlim(0.9, 4.6)
    ax.set_title(f"평균 평점이 높을수록 PI는 낮아지는 경향 (상관계수 {r:.2f})", pad=12)
    fig.text(0.01, 0.01, f"평점 100개 이상 영화 {len(df):,}편", fontsize=8.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    save(fig, "fig1_pi_vs_mean.png")


# ---------------------------------------------------------------- 그림 2
def fig2():
    d = pd.read_csv(RES / "h3_regression.csv", encoding="utf-8-sig")
    d = d[d["분석"] == "A 구간별 PI 효과"]
    bins = ["2.5 미만", "2.5~3.0", "3.0~3.5", "3.5~4.0", "4.0 이상"]
    dvs = ["투표 수", "popularity"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 5.0), sharey=True)
    for ax, dv in zip(axes, dvs):
        s = d[d["종속변수"] == dv].set_index("그룹/항").loc[bins]
        x = np.arange(len(bins))
        ax.axhline(0, color=MUTED, lw=1.0, zorder=1)
        ax.vlines(x, s["CI하한"], s["CI상한"], color=DV_COLOR[dv], lw=1.8, zorder=2)
        ax.scatter(x, s["계수"], s=46, color=DV_COLOR[dv], edgecolor=SURFACE, linewidth=1.5, zorder=3)
        # 가장 큰 값, 그리고 음수인 가장 작은 값만 직접 표시 (0 기준선과 겹치는 값은 표시하지 않음)
        vals = s["계수"].values
        for i in {vals.argmax(), vals.argmin() if vals.min() < 0 else vals.argmax()}:
            ax.text(x[i] + 0.12, vals[i], f"{vals[i]:+.3f}", color=INK, fontsize=9, va="center")
        ax.set_xticks(x)
        ax.set_xticklabels([f"{b}\n({int(s.loc[b, 'N']):,}편)" for b in bins], fontsize=9)
        ax.set_xlim(-0.5, len(bins) - 0.5)
        ax.set_title(dv, color=INK, pad=8)
        ax.set_xlabel("영화의 평균 평점 구간")
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("PI 1표준편차 증가당 화제성 변화\n(log(1+화제성) 단위)")

    fig.suptitle("PI의 효과는 평균 평점이 낮은 영화에서 가장 크고, 평점이 높아질수록 줄어든다",
                 x=0.02, ha="left", fontsize=13, fontweight="bold", y=0.985)
    handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor=DV_COLOR[k], markeredgecolor=SURFACE,
                      markersize=8, label=k) for k in dvs]
    fig.legend(handles=handles, loc="upper right", ncol=2, frameon=False, bbox_to_anchor=(0.99, 0.985), labelcolor=INK2)
    fig.text(0.02, 0.01, "점 = 추정 계수, 세로선 = 95% 신뢰구간. 0보다 위면 PI가 높을수록 화제성이 크다. "
                         "통제변수: 평균 평점, 평점 수, 개봉 연도.", fontsize=8.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 0.93))
    save(fig, "fig2_h3_by_mean_bin.png")


# ---------------------------------------------------------------- 그림 3
def fig3():
    d = pd.read_csv(RES / "h2_regression.csv", encoding="utf-8-sig")
    d = d[d["분석"] == "B 장르별 PI 효과"]
    rows = [("Thriller(해석형)", "Thriller", True), ("Sci-Fi(해석형)", "Sci-Fi", True), ("Horror(해석형)", "Horror", True),
            ("Drama(비교군)", "Drama", False), ("Children(비교군)", "Children", False)]
    ypos = [5, 4, 3, 1.6, 0.6]          # 해석형 3개와 비교군 2개 사이에 간격을 둠
    dvs = ["투표 수", "popularity"]

    fig, axes = plt.subplots(1, 2, figsize=(10, 5.0), sharey=True)
    for ax, dv in zip(axes, dvs):
        s = d[d["종속변수"] == dv].set_index("그룹/항")
        ax.axvline(0, color=MUTED, lw=1.0, zorder=1)
        for (key, name, interp), y in zip(rows, ypos):
            r = s.loc[key]
            ax.hlines(y, r["CI하한"], r["CI상한"], color=DV_COLOR[dv], lw=1.8, zorder=2)
            # 해석형 = 채운 원, 비교군 = 속이 빈 원 (색이 아닌 모양으로도 구분)
            ax.scatter(r["계수"], y, s=54, zorder=3, linewidth=1.8,
                       facecolor=DV_COLOR[dv] if interp else SURFACE, edgecolor=DV_COLOR[dv])
        # 가장 눈에 띄는 값만 직접 표시 (점 위쪽 가운데, 0 기준선과 겹치지 않게)
        for key, y in [("Thriller(해석형)", 5), ("Drama(비교군)", 1.6)]:
            r = s.loc[key]
            ax.text(r["계수"], y + 0.22, f"{r['계수']:+.3f}", color=INK, fontsize=9, ha="center", va="bottom")
        ax.set_title(dv, pad=8)
        ax.set_xlabel("PI 1표준편차 증가당 화제성 변화\n(log(1+화제성) 단위)")
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(ypos)
    axes[0].set_yticklabels([f"{n}  ({int(d[(d['종속변수'] == '투표 수') & (d['그룹/항'] == k)]['N'].iloc[0]):,}편)"
                             for k, n, _ in rows])
    axes[0].set_ylim(-0.1, 5.8)
    axes[0].tick_params(axis="y", labelcolor=INK2, length=0)
    axes[1].tick_params(axis="y", length=0)

    fig.suptitle("장르별로 보면 PI의 효과는 스릴러에서 가장 뚜렷하다", x=0.02, ha="left", fontsize=13, fontweight="bold", y=0.985)
    handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor=INK2, markeredgecolor=INK2, markersize=8, label="해석형 장르"),
               Line2D([0], [0], marker="o", color="none", markerfacecolor=SURFACE, markeredgecolor=INK2, markersize=8, label="비교군 장르")]
    fig.legend(handles=handles, loc="upper right", ncol=2, frameon=False, bbox_to_anchor=(0.99, 0.985), labelcolor=INK2)
    fig.text(0.02, 0.01, "점 = 추정 계수, 가로선 = 95% 신뢰구간. 장르별로 따로 추정(평균 평점×PI는 통제하지 않음). "
                         "한 영화가 여러 장르에 속할 수 있음.", fontsize=8.5, color=MUTED)
    fig.tight_layout(rect=(0, 0.03, 1, 0.93))
    save(fig, "fig3_h2_by_genre.png")


def main():
    setup_style()
    fig1()
    fig2()
    fig3()


if __name__ == "__main__":
    main()
