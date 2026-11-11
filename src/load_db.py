"""
CSV 3종(PI·장르·TMDB)을 SQLite DB에 적재

- 입력: results/pi_by_movie.csv, results/pi_adjusted_compare.csv,
        results/movie_genre_dummies.csv, data/tmdb_movies.csv
- 출력: data/movies.db  (data/는 Git 제외)
- 테이블 구조는 sql/01_create_tables.sql에 정의
- 다시 실행하면 테이블을 지우고 새로 만든다 (CSV가 바뀌었을 때 갱신용)

실행 방법 (프로젝트 폴더에서):
    python -X utf8 src/load_db.py
"""

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "movies.db"
SCHEMA_PATH = ROOT / "sql" / "01_create_tables.sql"

PI_CSV = ROOT / "results" / "pi_by_movie.csv"
ADJ_CSV = ROOT / "results" / "pi_adjusted_compare.csv"
GENRE_CSV = ROOT / "results" / "movie_genre_dummies.csv"
TMDB_CSV = ROOT / "data" / "tmdb_movies.csv"


def main():
    pi = pd.read_csv(PI_CSV, dtype={"tmdbId": "Int64"})
    adj = pd.read_csv(ADJ_CSV, usecols=["movieId", "PI_B", "PI_C"])
    genres = pd.read_csv(GENRE_CSV)
    tmdb = pd.read_csv(TMDB_CSV)

    # tmdb: 같은 tmdbId가 두 번 수집된 경우가 있어 하나만 남김 (기본키 중복 방지)
    n_dup = int(tmdb["tmdbId"].duplicated().sum())
    tmdb = tmdb.drop_duplicates("tmdbId")

    # movies: 제목 끝 "(1995)"에서 개봉 연도 추출 (없으면 결측)
    pi["year"] = pd.to_numeric(pi["title"].str.extract(r"\((\d{4})\)\s*$")[0], errors="coerce").astype("Int64")
    movies = pi[["movieId", "title", "year", "genres", "tmdbId"]]

    # pi_stats: PI + 보정 PI 결합
    pi_stats = pi[["movieId", "n_ratings", "mean_rating", "std_rating", "PI"]].merge(adj, on="movieId", how="left")

    # genres: 열 이름의 하이픈 제거 (SQL에서 따옴표 없이 쓰려고)
    genres = genres.rename(columns=lambda c: c.replace("-", "")).rename(columns={"both": "both_groups"})
    genres["both_groups"] = genres["both_groups"].astype(int)

    if DB_PATH.exists():
        DB_PATH.unlink()
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    con.execute("PRAGMA foreign_keys = ON")

    # 부모 테이블부터 적재
    for name, df in [("tmdb", tmdb), ("movies", movies), ("pi_stats", pi_stats), ("genres", genres)]:
        df.to_sql(name, con, if_exists="append", index=False)
        print(f"  {name:9s} {len(df):>6,}행 적재")
    con.commit()

    print(f"\n(참고) tmdb에서 중복 tmdbId {n_dup}행 제거")
    print("외래키 위반:", con.execute("PRAGMA foreign_key_check").fetchall() or "없음")
    n = con.execute("SELECT COUNT(*) FROM analysis_base").fetchone()[0]
    print(f"분석용 뷰(analysis_base) 행 수: {n:,}")
    con.close()
    print(f"\n저장 완료: {DB_PATH}")


if __name__ == "__main__":
    main()
