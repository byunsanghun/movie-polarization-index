-- 테이블 생성문 (SQLite)
-- 기준 번호: movieId(MovieLens), tmdbId(TMDB)
-- 적재 순서: tmdb -> movies -> pi_stats, genres  (외래키 때문에 부모 테이블이 먼저)

PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS analysis_base;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS pi_stats;
DROP TABLE IF EXISTS movies;
DROP TABLE IF EXISTS tmdb;

-- TMDB 화제성 지표 (수집일 기준 값이라 fetched_at을 함께 보관)
CREATE TABLE tmdb (
    tmdbId        INTEGER PRIMARY KEY,
    status        TEXT NOT NULL CHECK (status IN ('ok', 'not_found')),
    popularity    REAL,
    vote_count    INTEGER,
    vote_average  REAL,
    fetched_at    TEXT NOT NULL
);

-- 영화 기본 정보
CREATE TABLE movies (
    movieId  INTEGER PRIMARY KEY,
    title    TEXT NOT NULL,
    year     INTEGER,                       -- title의 "(1995)"에서 추출, 없으면 NULL
    genres   TEXT,                          -- 원본 "Action|Sci-Fi" 문자열
    tmdbId   INTEGER REFERENCES tmdb(tmdbId)  -- 결측이면 NULL
);

-- PI 및 보정 PI (MIN_RATINGS=100 기준)
CREATE TABLE pi_stats (
    movieId      INTEGER PRIMARY KEY REFERENCES movies(movieId),
    n_ratings    INTEGER NOT NULL,
    mean_rating  REAL NOT NULL,
    std_rating   REAL NOT NULL,
    PI           REAL NOT NULL,             -- std / 2.25
    PI_B         REAL,                      -- 구조 보정 (민감도 분석용)
    PI_C         REAL                       -- 평균 회귀 잔차 (민감도 분석용)
);

-- 장르 더미 (영화 하나가 여러 장르면 여러 열이 1)
CREATE TABLE genres (
    movieId         INTEGER PRIMARY KEY REFERENCES movies(movieId),
    g_Action        INTEGER, g_Adventure   INTEGER, g_Animation INTEGER,
    g_Children      INTEGER, g_Comedy      INTEGER, g_Crime     INTEGER,
    g_Documentary   INTEGER, g_Drama       INTEGER, g_Fantasy   INTEGER,
    g_FilmNoir      INTEGER, g_Horror      INTEGER, g_IMAX      INTEGER,
    g_Musical       INTEGER, g_Mystery     INTEGER, g_Romance   INTEGER,
    g_SciFi         INTEGER, g_Thriller    INTEGER, g_War       INTEGER,
    g_Western       INTEGER,
    is_interpret    INTEGER NOT NULL,       -- Thriller/Sci-Fi/Horror 중 하나라도 포함
    is_compare      INTEGER NOT NULL,       -- Drama/Children 중 하나라도 포함
    both_groups     INTEGER NOT NULL,       -- 두 그룹 모두 포함 (방식 A에서 제외)
    group_A         INTEGER                 -- 1=해석형 단독, 0=비교군 단독, NULL=제외
);

CREATE INDEX idx_movies_tmdb ON movies(tmdbId);

-- 분석용 결합 뷰: 회귀(H1~H4)에서 바로 읽을 한 장짜리 표
-- TMDB에서 정상 수집된(status='ok') 영화만 포함
CREATE VIEW analysis_base AS
SELECT
    m.movieId, m.title, m.year,
    p.n_ratings, p.mean_rating, p.std_rating, p.PI, p.PI_B, p.PI_C,
    t.popularity, t.vote_count, t.vote_average, t.fetched_at,
    g.*
FROM movies m
JOIN pi_stats p ON p.movieId = m.movieId
JOIN tmdb     t ON t.tmdbId  = m.tmdbId AND t.status = 'ok'
JOIN genres   g ON g.movieId = m.movieId;
