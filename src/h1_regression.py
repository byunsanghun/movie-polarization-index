"""
H1 검증: 평균 평점과 평점 수를 통제해도 PI가 높을수록 화제성이 큰가?

모델 (OLS, 이분산에 강한 HC3 표준오차):
    log(1+화제성) ~ PI(표준화) + 평균 평점 + log(1+평점 수) + 개봉 연도
- 화제성(종속변수): TMDB vote_count, TMDB popularity  (둘 다 log(1+x) 변환)
- 통제변수는 MovieLens 출처(평균 평점·평점 수), 종속변수는 TMDB 출처 → 출처가 겹치지 않음
- PI는 표준화(평균 0, 표준편차 1)해서 "PI가 1 표준편차 높을 때"의 효과로 읽는다
- 민감도 분석: 원래 PI 대신 보정 PI(B 구조 보정, C 잔차)로 같은 모델을 돌려 비교

입력: data/movies.db 의 analysis_base 뷰
출력: 콘솔 + results/h1_regression.csv

실행 방법 (프로젝트 폴더에서):
    python -X utf8 src/h1_regression.py
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "movies.db"
OUT_PATH = ROOT / "results" / "h1_regression.csv"


def zscore(s):
    return (s - s.mean()) / s.std()


def main():
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT movieId, title, year, n_ratings, mean_rating, PI, PI_B, PI_C, "
                     "vote_count, popularity FROM analysis_base", con)
    con.close()

    n0 = len(df)
    df = df.dropna(subset=["year"]).copy()          # 연도를 못 뽑은 영화 제외
    print(f"분석 대상 {len(df):,}편 (연도 결측 {n0 - len(df)}편 제외)")

    # 변수 만들기
    df["log_vote"] = np.log1p(df["vote_count"])
    df["log_pop"] = np.log1p(df["popularity"])
    df["log_n"] = np.log1p(df["n_ratings"])
    for c in ["PI", "PI_B", "PI_C"]:
        df[f"{c}_z"] = zscore(df[c])

    controls = "mean_rating + log_n + year"
    results = []

    def run(label, dv, pi_var):
        m = smf.ols(f"{dv} ~ {pi_var} + {controls}", data=df).fit(cov_type="HC3")
        b, se, p = m.params[pi_var], m.bse[pi_var], m.pvalues[pi_var]
        lo, hi = m.conf_int().loc[pi_var]
        results.append({"모델": label, "종속변수": dv, "PI변수": pi_var, "PI계수": round(b, 4),
                        "표준오차": round(se, 4), "p값": p, "CI하한": round(lo, 4), "CI상한": round(hi, 4),
                        "약_변화율(%)": round((np.exp(b) - 1) * 100, 1), "R2": round(m.rsquared, 3), "N": int(m.nobs)})
        return m

    # 메인 모델 + 종속변수 2종
    m_vote = run("메인(투표 수)", "log_vote", "PI_z")
    m_pop = run("메인(popularity)", "log_pop", "PI_z")

    # 민감도: 보정 PI
    run("민감도 B 구조 보정(투표 수)", "log_vote", "PI_B_z")
    run("민감도 C 잔차(투표 수)", "log_vote", "PI_C_z")
    run("민감도 B 구조 보정(popularity)", "log_pop", "PI_B_z")
    run("민감도 C 잔차(popularity)", "log_pop", "PI_C_z")

    print("\n===== 메인 모델: log(1+투표 수) =====")
    print(m_vote.summary().tables[1])
    print(f"R² = {m_vote.rsquared:.3f}")

    # 다중공선성 점검 (VIF: 보통 5~10 넘으면 주의)
    X = df[["PI_z", "mean_rating", "log_n", "year"]].assign(const=1.0)
    vif = {c: round(variance_inflation_factor(X.values, i), 2) for i, c in enumerate(X.columns) if c != "const"}
    print("\n[VIF] (5~10 이상이면 변수끼리 너무 겹침)", vif)

    out = pd.DataFrame(results)
    out["p값"] = out["p값"].map(lambda v: f"{v:.2e}")
    print("\n===== PI 계수 요약 (PI 1표준편차 증가 시 log(1+화제성) 변화) =====")
    print(out.to_string(index=False))

    out.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
