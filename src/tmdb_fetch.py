"""
TMDB 화제성 지표 수집 스크립트

- 입력: results/pi_by_movie.csv (tmdbId 사용), .env (TMDB_API_KEY)
- 출력: data/tmdb_movies.csv  (data/는 Git 제외)
- 수집 항목: popularity, vote_count, vote_average (+ 수집 날짜)
- 중간 저장: 이미 받은 영화는 건너뛰므로, 끊겨도 다시 실행하면 이어서 진행된다.

실행 방법 (프로젝트 폴더에서):
    python src/tmdb_fetch.py --limit 5     # 시험 호출 (5편만)
    python src/tmdb_fetch.py               # 전체 수집
"""

import argparse
import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# ===== 설정 =====
ROOT = Path(__file__).resolve().parent.parent
PI_PATH = ROOT / "results" / "pi_by_movie.csv"
OUT_PATH = ROOT / "data" / "tmdb_movies.csv"
API_URL = "https://api.themoviedb.org/3/movie/{}"
SLEEP_SEC = 0.05          # 호출 사이 간격 (TMDB 제한을 넘지 않게)
SAVE_EVERY = 200          # 이만큼 받을 때마다 파일에 저장
MAX_RETRY = 3
COLUMNS = ["tmdbId", "status", "popularity", "vote_count", "vote_average", "fetched_at"]


def fetch_one(session, api_key, tmdb_id):
    """영화 1편 조회. 성공하면 dict, 영화가 없으면(404) status='not_found'."""
    for attempt in range(MAX_RETRY):
        try:
            r = session.get(API_URL.format(tmdb_id), params={"api_key": api_key}, timeout=15)
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
            continue

        if r.status_code == 200:
            j = r.json()
            return {
                "tmdbId": tmdb_id, "status": "ok",
                "popularity": j.get("popularity"),
                "vote_count": j.get("vote_count"),
                "vote_average": j.get("vote_average"),
                "fetched_at": date.today().isoformat(),
            }
        if r.status_code == 404:
            return {"tmdbId": tmdb_id, "status": "not_found", "popularity": None,
                    "vote_count": None, "vote_average": None,
                    "fetched_at": date.today().isoformat()}
        if r.status_code == 429:  # 너무 빨리 요청함 → 기다렸다 재시도
            time.sleep(int(r.headers.get("Retry-After", 5)))
            continue
        if r.status_code == 401:
            raise SystemExit("API 키가 거절됐어요(401). .env의 TMDB_API_KEY를 확인하세요.")
        time.sleep(2 * (attempt + 1))
    return None  # 재시도 모두 실패 → 저장하지 않아서 다음 실행 때 다시 시도됨


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="시험용: 앞에서 N편만")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        raise SystemExit(".env에 TMDB_API_KEY가 없어요.")

    # 1. 수집 대상: PI 계산된 영화의 tmdbId (결측은 제외하고 개수만 알림)
    pi = pd.read_csv(PI_PATH, usecols=["movieId", "tmdbId"], dtype={"tmdbId": "Int64"})
    missing = pi["tmdbId"].isna().sum()
    ids = pi["tmdbId"].dropna().astype(int).tolist()
    print(f"대상 영화 {len(pi):,}편 (tmdbId 결측 {missing}편 제외 → 수집 대상 {len(ids):,}편)")

    # 2. 이미 받은 영화는 건너뛰기
    OUT_PATH.parent.mkdir(exist_ok=True)
    if OUT_PATH.exists():
        done_df = pd.read_csv(OUT_PATH)
        done = set(done_df["tmdbId"])
        rows = done_df.to_dict("records")
    else:
        done, rows = set(), []
    todo = [i for i in ids if i not in done]
    if args.limit:
        todo = todo[: args.limit]
    print(f"이미 수집 {len(done):,}편 / 이번에 수집 {len(todo):,}편")

    # 3. 수집
    session = requests.Session()
    failed = 0
    for n, tmdb_id in enumerate(todo, 1):
        row = fetch_one(session, api_key, tmdb_id)
        if row is None:
            failed += 1
        else:
            rows.append(row)
        if n % SAVE_EVERY == 0:
            pd.DataFrame(rows, columns=COLUMNS).to_csv(OUT_PATH, index=False)
            print(f"  {n:,}/{len(todo):,} 저장")
        time.sleep(SLEEP_SEC)

    pd.DataFrame(rows, columns=COLUMNS).to_csv(OUT_PATH, index=False)

    # 4. 요약
    out = pd.DataFrame(rows, columns=COLUMNS)
    print(f"\n저장 완료: {OUT_PATH}")
    print(f"  성공 {int((out['status'] == 'ok').sum()):,} / TMDB에 없음 {int((out['status'] == 'not_found').sum()):,} / 실패(재실행 필요) {failed}")
    if len(out):
        print(out.tail(5).to_string(index=False))


if __name__ == "__main__":
    main()
