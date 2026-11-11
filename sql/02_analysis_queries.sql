-- 분석 쿼리 모음 (SQLite). 대상: analysis_base 뷰 (TMDB 정상 수집 영화)
-- 실행 예: sqlite3 data/movies.db < sql/02_analysis_queries.sql

-- [Q1] 결합 결과 확인: 전체 대비 분석 가능한 영화 수, 연도 결측
SELECT
    (SELECT COUNT(*) FROM movies)                        AS 전체영화,
    (SELECT COUNT(*) FROM analysis_base)                 AS 분석가능,
    (SELECT COUNT(*) FROM analysis_base WHERE year IS NULL) AS 연도결측;

-- [Q2] PI 5분위(NTILE)별 화제성 평균: PI가 높을수록 투표 수가 많은지 1차 확인
--      ※ 평균 평점·평점 수를 통제하지 않은 단순 비교 (통제는 H1 회귀에서)
SELECT
    pi_quintile                         AS PI분위_5가높음,
    COUNT(*)                            AS 영화수,
    ROUND(AVG(PI), 3)                   AS PI평균,
    ROUND(AVG(mean_rating), 2)          AS 평균평점평균,
    ROUND(AVG(vote_count), 0)           AS 투표수평균,
    ROUND(AVG(popularity), 2)           AS popularity평균
FROM (
    SELECT *, NTILE(5) OVER (ORDER BY PI) AS pi_quintile
    FROM analysis_base
)
GROUP BY pi_quintile
ORDER BY pi_quintile;

-- [Q3] H2 방식 A: 해석형 단독 vs 비교군 단독 (겹침·둘 다 아님은 group_A가 NULL이라 제외)
SELECT
    CASE group_A WHEN 1 THEN '해석형 단독' ELSE '비교군 단독' END AS 그룹,
    COUNT(*)                   AS 영화수,
    ROUND(AVG(PI), 3)          AS PI평균,
    ROUND(AVG(vote_count), 0)  AS 투표수평균
FROM analysis_base
WHERE group_A IS NOT NULL
GROUP BY group_A;

-- [Q4] 장르별 영화 수 · PI 평균 · 투표 수 평균 (UNION ALL로 장르 열을 행으로 펼침)
SELECT 장르, COUNT(*) AS 영화수, ROUND(AVG(PI), 3) AS PI평균, ROUND(AVG(vote_count), 0) AS 투표수평균
FROM (
    SELECT 'Thriller' AS 장르, PI, vote_count FROM analysis_base WHERE g_Thriller = 1
    UNION ALL SELECT 'SciFi',    PI, vote_count FROM analysis_base WHERE g_SciFi    = 1
    UNION ALL SELECT 'Horror',   PI, vote_count FROM analysis_base WHERE g_Horror   = 1
    UNION ALL SELECT 'Drama',    PI, vote_count FROM analysis_base WHERE g_Drama    = 1
    UNION ALL SELECT 'Children', PI, vote_count FROM analysis_base WHERE g_Children = 1
)
GROUP BY 장르
ORDER BY 영화수 DESC;

-- [Q5] PI 상위 10편과 화제성 (컬트·논쟁작이 실제로 화제성이 큰지 눈으로 확인)
SELECT title, year, n_ratings, mean_rating, PI, vote_count, ROUND(popularity, 2) AS popularity
FROM analysis_base
ORDER BY PI DESC
LIMIT 10;
