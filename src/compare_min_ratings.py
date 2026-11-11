"""
MIN_RATINGS(최소 평점 수) 기준을 바꿔가며 PI TOP 10이 어떻게 달라지는지 비교

- pi.py는 건드리지 않고, 같은 방식(표준편차 / 2.25)으로 따로 계산한다.
- 평점은 한 번만 읽고 집계한 뒤, 기준값만 바꿔 걸러낸다.
- 출력: 콘솔 비교표 + results/top10_by_min_ratings.csv

실행 방법 (프로젝트 폴더에서):
    python src/compare_min_ratings.py
"""

from pathlib import Path

import pandas as pd

# ===== 설정 =====
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "ml-25m"          # 테스트할 땐 "ml-latest-small"로 변경
OUT_DIR = ROOT / "results"
THRESHOLDS = [50, 100, 200]                  # 비교할 MIN_RATINGS 값들
MAX_STD = 2.25
TOP_N = 10


def main():
    OUT_DIR.mkdir(exist_ok=True)

    # 1. 평점 1회 읽기 + 영화별 집계 (기준값과 무관한 부분이라 한 번만)
    print("평점 데이터 불러오는 중...")
    ratings = pd.read_csv(
        DATA_DIR / "ratings.csv",
        usecols=["movieId", "rating"],
        dtype={"movieId": "int32", "rating": "float32"},
    )
    stats = (
        ratings.groupby("movieId")["rating"]
        .agg(n_ratings="count", mean_rating="mean", std_rating="std")
        .reset_index()
    )
    stats["PI"] = (stats["std_rating"] / MAX_STD).round(4)
    stats["mean_rating"] = stats["mean_rating"].round(3)

    movies = pd.read_csv(DATA_DIR / "movies.csv")
    stats = stats.merge(movies[["movieId", "title"]], on="movieId", how="left")

    # 2. 기준값별 TOP 10 추출
    tops = {}
    rows = []
    for t in THRESHOLDS:
        sub = stats[stats["n_ratings"] >= t].sort_values("PI", ascending=False)
        top = sub.head(TOP_N).reset_index(drop=True)
        tops[t] = top
        print(f"\n[MIN_RATINGS={t}] 대상 영화 {len(sub):,}편")
        print(top[["title", "n_ratings", "mean_rating", "PI"]].to_string())
        for rank, r in top.iterrows():
            rows.append({"min_ratings": t, "rank": rank + 1, "title": r["title"],
                         "n_ratings": r["n_ratings"], "mean_rating": r["mean_rating"],
                         "PI": r["PI"]})

    # 3. 기준 간 겹치는 영화 수 / 평점 수 중앙값
    print("\n[기준별 요약]")
    summary = []
    for t in THRESHOLDS:
        top = tops[t]
        summary.append({
            "MIN_RATINGS": t,
            "TOP10 평점수 중앙값": int(top["n_ratings"].median()),
            "TOP10 평균평점 평균": round(top["mean_rating"].mean(), 2),
            "50 기준과 겹치는 편수": len(set(top["movieId"]) & set(tops[THRESHOLDS[0]]["movieId"])),
        })
    print(pd.DataFrame(summary).to_string(index=False))

    out_path = OUT_DIR / "top10_by_min_ratings.csv"
    pd.DataFrame(rows).to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {out_path}")


if __name__ == "__main__":
    main()
