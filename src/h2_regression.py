"""
H2 검증: 스릴러·SF·호러에서는 PI의 효과가 드라마·가족물보다 큰가? (PI × 장르 상호작용)

세 가지 방법 (종속변수: log(1+투표 수), log(1+popularity)):
  A. 그룹 비교   : 해석형 단독(Thriller/Sci-Fi/Horror) vs 비교군 단독(Drama/Children),
                   두 그룹에 모두 속하거나 어디에도 속하지 않는 영화는 제외
                   모델: PI + 그룹 + PI×그룹 + 통제변수.  핵심은 PI×그룹 계수(양(+)이면 H2 지지)
  A2. A + 'PI × 평균 평점' 통제 : H3에서 PI 효과가 평균 평점에 따라 달라졌으므로,
                   장르 차이가 평균 평점 차이 때문이 아닌지 확인
  B. 장르별 개별 : 장르(Thriller, Sci-Fi, Horror, Drama, Children) 영화만 따로 뽑아 PI 효과를 각각 추정
- 통제변수: 평균 평점, log(1+평점 수), 개봉 연도.  PI는 전체 표본 기준 표준화(1 표준편차 단위)
- 표준오차는 HC3

입력: data/movies.db 의 analysis_base 뷰
출력: 콘솔 + results/h2_regression.csv

실행 방법 (프로젝트 폴더에서):
    python -X utf8 src/h2_regression.py
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "movies.db"
OUT_PATH = ROOT / "results" / "h2_regression.csv"

DVS = [("log_vote", "투표 수"), ("log_pop", "popularity")]
GENRES = [("g_Thriller", "Thriller(해석형)"), ("g_SciFi", "Sci-Fi(해석형)"), ("g_Horror", "Horror(해석형)"),
          ("g_Drama", "Drama(비교군)"), ("g_Children", "Children(비교군)")]
CONTROLS = "mean_rating + log_n + year"


def prep():
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM analysis_base", con)
    con.close()
    df = df.dropna(subset=["year"]).copy()
    df["log_vote"] = np.log1p(df["vote_count"])
    df["log_pop"] = np.log1p(df["popularity"])
    df["log_n"] = np.log1p(df["n_ratings"])
    df["PI_z"] = (df["PI"] - df["PI"].mean()) / df["PI"].std()
    df["mean_c"] = df["mean_rating"] - df["mean_rating"].mean()
    return df


def fmt(m, term, part, dv_name, label, n):
    lo, hi = m.conf_int().loc[term]
    return {"분석": part, "종속변수": dv_name, "그룹/항": label, "계수": round(m.params[term], 4),
            "표준오차": round(m.bse[term], 4), "p값": f"{m.pvalues[term]:.2e}",
            "CI하한": round(lo, 4), "CI상한": round(hi, 4), "N": n}


def main():
    df = prep()
    print(f"분석 대상 {len(df):,}편")

    rows = []
    a = df[df["group_A"].notna()].copy()
    a["group_A"] = a["group_A"].astype(int)
    print(f"방식 A 표본: {len(a):,}편 (해석형 단독 {int((a['group_A'] == 1).sum()):,} / 비교군 단독 {int((a['group_A'] == 0).sum()):,})")

    for dv, dv_name in DVS:
        # A. 그룹 비교
        m = smf.ols(f"{dv} ~ PI_z * group_A + {CONTROLS}", data=a).fit(cov_type="HC3")
        rows.append(fmt(m, "PI_z", "A 그룹 비교", dv_name, "PI 효과(비교군 단독)", len(a)))
        rows.append(fmt(m, "PI_z:group_A", "A 그룹 비교", dv_name, "PI×해석형 (차이, H2 핵심)", len(a)))

        # A2. PI × 평균 평점 통제 추가
        m2 = smf.ols(f"{dv} ~ PI_z * group_A + PI_z:mean_c + {CONTROLS}", data=a).fit(cov_type="HC3")
        rows.append(fmt(m2, "PI_z:group_A", "A2 +PI×평균평점 통제", dv_name, "PI×해석형 (차이, H2 핵심)", len(a)))

        # B. 장르별 개별 PI 효과
        for col, label in GENRES:
            sub = df[df[col] == 1]
            mg = smf.ols(f"{dv} ~ PI_z + {CONTROLS}", data=sub).fit(cov_type="HC3")
            rows.append(fmt(mg, "PI_z", "B 장르별 PI 효과", dv_name, label, len(sub)))

    out = pd.DataFrame(rows)
    for part in out["분석"].unique():
        print(f"\n===== {part} =====")
        print(out[out["분석"] == part].drop(columns="분석").to_string(index=False))

    out.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
