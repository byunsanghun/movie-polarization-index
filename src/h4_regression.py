"""
H4 검증: PI와 화제성의 관계 중 상당 부분은 '평점 수(인기)' 효과 때문인가?

방법: 평점 수(log)를 모델에 넣기 전/후로 PI 계수가 얼마나 변하는지 비교
    M0: log(1+화제성) ~ PI
    M1: log(1+화제성) ~ PI + 평균 평점 + 연도                 (평점 수 없음)
    M2: log(1+화제성) ~ PI + 평균 평점 + 연도 + log(1+평점 수)  (H1 메인 모델)
- M1 → M2 의 PI 계수 변화가 '평점 수를 통제한 효과'
- 변화량의 불확실성은 부트스트랩(영화를 중복 허용해 다시 뽑기 반복)으로 신뢰구간을 구한다.
- PI는 표준화(1 표준편차 단위)

입력: data/movies.db 의 analysis_base 뷰
출력: 콘솔 + results/h4_regression.csv

실행 방법 (프로젝트 폴더에서):
    python -X utf8 src/h4_regression.py
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "movies.db"
OUT_PATH = ROOT / "results" / "h4_regression.csv"
N_BOOT = 500
SEED = 42

FORMULAS = {
    "M0 PI만": "{dv} ~ PI_z",
    "M1 평균·연도 통제 (평점 수 없음)": "{dv} ~ PI_z + mean_rating + year",
    "M2 + 평점 수 통제": "{dv} ~ PI_z + mean_rating + year + log_n",
}


def prep():
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT year, n_ratings, mean_rating, PI, vote_count, popularity FROM analysis_base", con)
    con.close()
    df = df.dropna(subset=["year"]).copy()
    df["log_vote"] = np.log1p(df["vote_count"])
    df["log_pop"] = np.log1p(df["popularity"])
    df["log_n"] = np.log1p(df["n_ratings"])
    df["PI_z"] = (df["PI"] - df["PI"].mean()) / df["PI"].std()
    return df


def pi_coef(df, dv, key):
    return smf.ols(FORMULAS[key].format(dv=dv), data=df).fit().params["PI_z"]


def main():
    df = prep()
    print(f"분석 대상 {len(df):,}편")
    print(f"PI와 log(평점 수)의 상관: {df['PI_z'].corr(df['log_n']):.3f}")

    rng = np.random.default_rng(SEED)
    k1, k2 = "M1 평균·연도 통제 (평점 수 없음)", "M2 + 평점 수 통제"
    rows = []
    for dv, name in [("log_vote", "투표 수"), ("log_pop", "popularity")]:
        coefs = {}
        for key in FORMULAS:
            m = smf.ols(FORMULAS[key].format(dv=dv), data=df).fit(cov_type="HC3")
            coefs[key] = m.params["PI_z"]
            rows.append({"종속변수": name, "모델": key, "PI계수": round(m.params["PI_z"], 4),
                         "표준오차": round(m.bse["PI_z"], 4), "p값": f"{m.pvalues['PI_z']:.2e}",
                         "R2": round(m.rsquared, 3), "N": int(m.nobs)})

        # 부트스트랩: M1→M2 계수 변화량(M2 - M1)의 신뢰구간
        diffs = []
        for _ in range(N_BOOT):
            s = df.sample(len(df), replace=True, random_state=int(rng.integers(1 << 31)))
            diffs.append(pi_coef(s, dv, k2) - pi_coef(s, dv, k1))
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        d = coefs[k2] - coefs[k1]
        print(f"\n[{name}] 평점 수 통제 전후 PI 계수: {coefs[k1]:+.4f} → {coefs[k2]:+.4f}  "
              f"(변화 {d:+.4f}, 95% 부트스트랩 CI [{lo:+.4f}, {hi:+.4f}])")
        rows.append({"종속변수": name, "모델": "변화량 (M2 - M1)", "PI계수": round(d, 4),
                     "표준오차": "", "p값": f"CI[{lo:+.4f}, {hi:+.4f}]", "R2": "", "N": ""})

    out = pd.DataFrame(rows)
    print("\n===== PI 계수 변화 요약 =====")
    print(out.to_string(index=False))
    out.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
