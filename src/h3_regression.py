"""
H3 검증: 평균 평점과 화제성의 관계는 선형이 아니라, PI가 높은 구간에서만 양(+)인가?

세 가지 방법으로 본다 (종속변수: log(1+투표 수), log(1+popularity)):
  A. 평균 평점 구간별로 나눠 PI 효과(계수)를 비교
  B. 전체 표본에서 평균 평점의 2차항, PI × 평균 평점 상호작용 검정
  C. PI 3분위(낮음/중간/높음)별로 나눠 '평균 평점'의 효과(기울기)를 비교  ← 가설 문장 그대로
- 모든 모델에 통제: 연도, log(1+평점 수) (A는 구간 안에서 평균 평점도 통제)
- PI는 전체 표본 기준 표준화(1 표준편차 단위)라서 구간끼리 계수를 비교할 수 있다
- 표준오차는 HC3

입력: data/movies.db 의 analysis_base 뷰
출력: 콘솔 + results/h3_regression.csv

실행 방법 (프로젝트 폴더에서):
    python -X utf8 src/h3_regression.py
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "movies.db"
OUT_PATH = ROOT / "results" / "h3_regression.csv"

# 평균 평점 구간: 양 끝은 영화가 적어서 묶음
BINS = [0, 2.5, 3.0, 3.5, 4.0, 5.1]
BIN_LABELS = ["2.5 미만", "2.5~3.0", "3.0~3.5", "3.5~4.0", "4.0 이상"]
DVS = [("log_vote", "투표 수"), ("log_pop", "popularity")]


def prep():
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT year, n_ratings, mean_rating, PI, vote_count, popularity FROM analysis_base", con)
    con.close()
    df = df.dropna(subset=["year"]).copy()
    df["log_vote"] = np.log1p(df["vote_count"])
    df["log_pop"] = np.log1p(df["popularity"])
    df["log_n"] = np.log1p(df["n_ratings"])
    df["PI_z"] = (df["PI"] - df["PI"].mean()) / df["PI"].std()
    df["mean_c"] = df["mean_rating"] - df["mean_rating"].mean()   # 평균 평점 중심화
    df["mean_c2"] = df["mean_c"] ** 2
    df["mean_bin"] = pd.cut(df["mean_rating"], bins=BINS, labels=BIN_LABELS, right=False)
    df["pi_tercile"] = pd.qcut(df["PI"], 3, labels=["PI 낮음", "PI 중간", "PI 높음"])
    return df


def row(part, dv_name, group, m, term, n):
    lo, hi = m.conf_int().loc[term]
    return {"분석": part, "종속변수": dv_name, "그룹/항": group, "계수": round(m.params[term], 4),
            "표준오차": round(m.bse[term], 4), "p값": f"{m.pvalues[term]:.2e}",
            "CI하한": round(lo, 4), "CI상한": round(hi, 4), "N": n}


def main():
    df = prep()
    print(f"분석 대상 {len(df):,}편, 평균 평점 평균 {df['mean_rating'].mean():.2f}")
    print("\n[구간별 영화 수]")
    print(df["mean_bin"].value_counts().sort_index().to_string())

    rows = []
    for dv, dv_name in DVS:
        # ---- A. 평균 평점 구간별 PI 효과 ----
        for lab in BIN_LABELS:
            sub = df[df["mean_bin"] == lab]
            m = smf.ols(f"{dv} ~ PI_z + mean_rating + year + log_n", data=sub).fit(cov_type="HC3")
            rows.append(row("A 구간별 PI 효과", dv_name, lab, m, "PI_z", len(sub)))

        # ---- B. 전체: 평균 평점 2차항 + PI×평균 상호작용 ----
        m = smf.ols(f"{dv} ~ PI_z + mean_c + mean_c2 + PI_z:mean_c + year + log_n", data=df).fit(cov_type="HC3")
        for term, lab in [("mean_c", "평균 평점(1차)"), ("mean_c2", "평균 평점²(2차항)"), ("PI_z:mean_c", "PI × 평균 평점")]:
            rows.append(row("B 2차항·상호작용", dv_name, lab, m, term, len(df)))

        # ---- C. PI 3분위별 평균 평점의 효과 ----
        for lab in ["PI 낮음", "PI 중간", "PI 높음"]:
            sub = df[df["pi_tercile"] == lab]
            m = smf.ols(f"{dv} ~ mean_rating + year + log_n", data=sub).fit(cov_type="HC3")
            rows.append(row("C PI 3분위별 평균 평점 효과", dv_name, lab, m, "mean_rating", len(sub)))

    out = pd.DataFrame(rows)
    for part in out["분석"].unique():
        print(f"\n===== {part} =====")
        print(out[out["분석"] == part].drop(columns="분석").to_string(index=False))

    out.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
