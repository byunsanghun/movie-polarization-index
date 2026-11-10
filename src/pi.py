"""
PI(호불호 분열 지수) 계산 스크립트

- 입력: data/ml-25m/ratings.csv, movies.csv, links.csv
- 출력: results/pi_by_movie.csv
- PI = 평점 표준편차 / 2.25  (0.5~5.0 평점 범위의 최대 표준편차로 나눠 0~1로 정규화)

실행 방법 (프로젝트 폴더에서):
    python src/pi.py
"""

from pathlib import Path

import pandas as pd

# ===== 설정 =====
ROOT = Path(__file__).resolve().parent.parent   # 프로젝트 최상위 폴더
DATA_DIR = ROOT / "data" / "ml-25m"             # 테스트할 땐 "ml-latest-small"로 변경
OUT_DIR = ROOT / "results"
MIN_RATINGS = 50                                # 평점 수가 이보다 적은 영화는 제외
MAX_STD = 2.25                                  # 0.5~5.0 범위에서 가능한 최대 표준편차


def main():
    OUT_DIR.mkdir(exist_ok=True)

    # 1. 평점 불러오기 (필요한 열만, 작은 자료형으로 → 메모리 절약)
    print("평점 데이터 불러오는 중... (25M은 1~2분 걸릴 수 있어요)")
    ratings = pd.read_csv(
        DATA_DIR / "ratings.csv",
        usecols=["movieId", "rating"],
        dtype={"movieId": "int32", "rating": "float32"},
    )
    print(f"  평점 {len(ratings):,}건")

    # 2. 영화별 평점 수 · 평균 · 표준편차 집계
    stats = (
        ratings.groupby("movieId")["rating"]
        .agg(n_ratings="count", mean_rating="mean", std_rating="std")
        .reset_index()
    )

    # 3. 평점 수가 적은 영화 제외
    stats = stats[stats["n_ratings"] >= MIN_RATINGS].copy()
    print(f"  평점 {MIN_RATINGS}개 이상 영화 {len(stats):,}편")

    # 4. PI 계산
    stats["PI"] = (stats["std_rating"] / MAX_STD).round(4)
    stats["mean_rating"] = stats["mean_rating"].round(3)
    stats["std_rating"] = stats["std_rating"].round(3)

    # 5. 영화 제목·장르, tmdbId 결합
    movies = pd.read_csv(DATA_DIR / "movies.csv")
    links = pd.read_csv(DATA_DIR / "links.csv", dtype={"tmdbId": "Int64"})
    result = (
        stats.merge(movies, on="movieId", how="left")
        .merge(links[["movieId", "tmdbId"]], on="movieId", how="left")
        .sort_values("PI", ascending=False)
    )

    # 6. 저장 (엑셀에서 한글 안 깨지게 utf-8-sig)
    out_path = OUT_DIR / "pi_by_movie.csv"
    result.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {out_path}")

    # 7. 미리보기
    cols = ["title", "n_ratings", "mean_rating", "PI"]
    print("\n[호불호가 가장 갈리는 영화 TOP 10]")
    print(result[cols].head(10).to_string(index=False))
    print("\n[반응이 가장 한결같은 영화 TOP 10]")
    print(result[cols].tail(10).iloc[::-1].to_string(index=False))


if __name__ == "__main__":
    main()
