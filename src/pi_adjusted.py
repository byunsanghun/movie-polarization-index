"""
평균 평점의 영향을 보정한 PI 비교 스크립트

문제: 평점이 0.5~5.0으로 막혀 있어서, 평균이 양 끝(1점대·5점 근처)이면
      표준편차가 구조적으로 작아질 수밖에 없다. 즉 PI가 '평균'의 영향을 받는다.
방법 3가지를 비교한다 (pi.py는 건드리지 않음):
  A. 원래 PI           = std / 2.25
  B. 구조 보정 PI      = std / sqrt((평균-0.5) * (5.0-평균))
                         (그 평균에서 가능한 최대 표준편차로 나눔)
  C. 잔차 PI           = PI를 평균·평균²로 회귀한 뒤 남는 부분 (평균으로 설명되는 부분 제거)
  D. 구간 내 백분위 PI = 평균 구간(0.5점 단위) 안에서의 PI 순위(0~1)

입력: results/pi_by_movie.csv
출력: 콘솔 비교표 + results/pi_adjusted_compare.csv

실행 방법 (프로젝트 폴더에서):
    python -X utf8 src/pi_adjusted.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_PATH = ROOT / "results" / "pi_by_movie.csv"
OUT_PATH = ROOT / "results" / "pi_adjusted_compare.csv"
LOW, HIGH = 0.5, 5.0       # 평점 범위
TOP_N = 10


def main():
    df = pd.read_csv(IN_PATH)
    m = df["mean_rating"]

    # A. 원래 PI
    df["PI_A"] = df["PI"]

    # B. 구조 보정: 평균 m에서 가능한 최대 표준편차 = sqrt((m-LOW)(HIGH-m))
    df["max_std_at_mean"] = np.sqrt((m - LOW) * (HIGH - m))
    df["PI_B"] = (df["std_rating"] / df["max_std_at_mean"]).round(4)

    # C. 잔차: PI ~ mean + mean^2 (2차 회귀) 후 남는 부분
    coef = np.polyfit(m, df["PI"], deg=2)
    df["PI_C"] = (df["PI"] - np.polyval(coef, m)).round(4)

    # D. 평균 구간 안에서의 백분위
    df["mean_bin"] = pd.cut(m, bins=np.arange(0.5, 5.5, 0.5))
    df["PI_D"] = df.groupby("mean_bin", observed=True)["PI"].rank(pct=True).round(4)

    # ---- 1. 평균 구간별 PI (진단) ----
    print("[진단] 평균 평점 구간별 원래 PI")
    diag = (df.groupby("mean_bin", observed=True)
              .agg(영화수=("PI", "size"), PI평균=("PI", "mean"), PI최대=("PI", "max"))
              .round(3))
    print(diag.to_string())

    # ---- 2. 방법별: 평균과의 상관 ----
    print("\n[평균 평점과의 상관계수] (0에 가까울수록 평균 영향이 작음)")
    corr = pd.DataFrame({
        "방법": ["A 원래 PI", "B 구조 보정", "C 잔차", "D 구간 백분위"],
        "상관(평균)": [df[c].corr(m).round(3) for c in ["PI_A", "PI_B", "PI_C", "PI_D"]],
        "상관(2차항)": [df[c].corr((m - m.mean()) ** 2).round(3) for c in ["PI_A", "PI_B", "PI_C", "PI_D"]],
    })
    print(corr.to_string(index=False))

    # ---- 3. 방법별 TOP 10 ----
    tops = {}
    for key, name in [("PI_A", "A 원래 PI"), ("PI_B", "B 구조 보정"),
                      ("PI_C", "C 잔차"), ("PI_D", "D 구간 백분위")]:
        top = df.sort_values(key, ascending=False).head(TOP_N)
        tops[key] = set(top["movieId"])
        print(f"\n[{name}] TOP {TOP_N}")
        print(top[["title", "n_ratings", "mean_rating", key]].to_string(index=False))

    # ---- 4. TOP 10 겹침 / 순위 상관 ----
    print("\n[원래 PI TOP10과 겹치는 편수]")
    for key in ["PI_B", "PI_C", "PI_D"]:
        print(f"  {key}: {len(tops['PI_A'] & tops[key])}편")
    print("\n[원래 PI와의 순위 상관 (스피어만)]")
    for key in ["PI_B", "PI_C", "PI_D"]:
        # 스피어만 = 순위끼리의 피어슨 상관 (scipy 없이 계산)
        print(f"  {key}: {df['PI_A'].rank().corr(df[key].rank()):.3f}")

    n_over = int((df["PI_B"] > 1).sum())
    print(f"\nPI_B가 1을 넘는 영화: {n_over}편 (표본 표준편차라 소폭 초과 가능)")

    df.drop(columns=["mean_bin"]).to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
