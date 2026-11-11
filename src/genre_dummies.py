"""
H2 준비: 장르 더미 변수 생성 + 장르별 영화 수 확인

- 입력: results/pi_by_movie.csv (genres 열은 "Action|Sci-Fi" 형태)
- 출력: 콘솔 표 + results/movie_genre_dummies.csv (movieId + 장르 더미 + 그룹 더미)
- 해석형 = Thriller / Sci-Fi / Horror 중 하나라도 포함
  비교군 = Drama / Children 중 하나라도 포함
  두 그룹에 모두 속한 영화는 그룹 비교(방식 A)에서 제외하기 위해 따로 표시한다.

실행 방법 (프로젝트 폴더에서):
    python -X utf8 src/genre_dummies.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN_PATH = ROOT / "results" / "pi_by_movie.csv"
OUT_PATH = ROOT / "results" / "movie_genre_dummies.csv"

INTERPRET = ["Thriller", "Sci-Fi", "Horror"]   # 해석형
COMPARE = ["Drama", "Children"]                # 비교군


def main():
    df = pd.read_csv(IN_PATH, usecols=["movieId", "title", "genres", "PI", "n_ratings"])

    # 1. 장르 문자열 → 리스트 → 장르별 0/1 열
    df["genre_list"] = df["genres"].str.split("|")
    all_genres = sorted({g for gs in df["genre_list"] for g in gs} - {"(no genres listed)"})
    for g in all_genres:
        df[f"g_{g}"] = df["genre_list"].apply(lambda gs, g=g: int(g in gs))

    # 2. 그룹 더미
    df["is_interpret"] = df[[f"g_{g}" for g in INTERPRET]].max(axis=1)
    df["is_compare"] = df[[f"g_{g}" for g in COMPARE]].max(axis=1)
    df["both"] = df["is_interpret"] & df["is_compare"]
    # 방식 A에서 쓸 그룹: 해석형 단독=1, 비교군 단독=0, 나머지(겹침·둘 다 아님)=결측
    df["group_A"] = pd.NA
    df.loc[(df["is_interpret"] == 1) & (df["is_compare"] == 0), "group_A"] = 1
    df.loc[(df["is_interpret"] == 0) & (df["is_compare"] == 1), "group_A"] = 0

    total = len(df)
    print(f"전체 영화 {total:,}편, 장르 {len(all_genres)}종 "
          f"((no genres listed) {int((df['genres'] == '(no genres listed)').sum())}편)")

    # 3. 장르별 영화 수 + PI 평균
    rows = []
    for g in all_genres:
        sub = df[df[f"g_{g}"] == 1]
        rows.append({"장르": g, "영화수": len(sub), "비율(%)": round(100 * len(sub) / total, 1),
                     "PI평균": round(sub["PI"].mean(), 3),
                     "대상": "해석형" if g in INTERPRET else ("비교군" if g in COMPARE else "")})
    gtab = pd.DataFrame(rows).sort_values("영화수", ascending=False)
    print("\n[장르별 영화 수 · PI 평균] (한 영화가 여러 장르에 중복 집계됨)")
    print(gtab.to_string(index=False))

    # 4. 그룹 구성 (방식 A)
    n_i = int((df["is_interpret"] == 1).sum())
    n_c = int((df["is_compare"] == 1).sum())
    n_both = int(df["both"].sum())
    n_i_only = int((df["group_A"] == 1).sum())
    n_c_only = int((df["group_A"] == 0).sum())
    n_none = total - n_i - n_c + n_both
    print("\n[방식 A: 해석형 vs 비교군]")
    print(pd.DataFrame({
        "구분": ["해석형(포함)", "비교군(포함)", "둘 다 속함(제외)", "해석형 단독 → 1", "비교군 단독 → 0", "둘 다 아님(제외)"],
        "영화수": [n_i, n_c, n_both, n_i_only, n_c_only, n_none],
    }).to_string(index=False))
    print(f"\n방식 A 실제 분석 표본: {n_i_only + n_c_only:,}편 ({100 * (n_i_only + n_c_only) / total:.1f}%)")

    a = df[df["group_A"].notna()]
    print("\n[방식 A 그룹별 PI 평균]")
    print(a.groupby("group_A")["PI"].agg(["size", "mean"]).round(3).rename(
        index={0: "비교군 단독", 1: "해석형 단독"}, columns={"size": "영화수", "mean": "PI평균"}).to_string())

    # 5. 저장
    keep = ["movieId"] + [f"g_{g}" for g in all_genres] + ["is_interpret", "is_compare", "both", "group_A"]
    df[keep].to_csv(OUT_PATH, index=False)
    print(f"\n저장 완료: {OUT_PATH}")


if __name__ == "__main__":
    main()
