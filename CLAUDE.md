# 프로젝트 안내 (Claude Code용)

## 프로젝트 개요
- 이름: 호불호 분열 지수(PI)와 콘텐츠 화제성 분석 — "평균 평점의 함정"
- 지산학 캡스톤멘토링(2026-2학기) 팀 프로젝트이자 빅데이터 과목 프로젝트
- 핵심 아이디어: 평균 평점이 같아도 "모두 3점"인 영화와 "절반 5점, 절반 1점"인 영화는 다르다.
  이 호불호 갈림 정도(PI)를 수치화하고, 화제성(TMDB popularity·투표 수)과의 관계를 분석한다.
- 포트폴리오용으로 GitHub에 공개 관리 중 (저장소: byunsanghun/movie-polarization-index)

## 팀 / 역할
- 상훈: 데이터 확보, 전처리, PI 계산 코드, DB 적재 (백엔드·DB 개발자 지망)
- 동훈: 시각화, 발표 자료 (results/pi_by_movie.csv를 받아 작업)

## 데이터
- MovieLens 25M (data/ml-25m/): ratings.csv(약 2,500만 건), movies.csv, links.csv 등
- TMDB API: popularity, vote_count 등 화제성 지표 (links.csv의 tmdbId로 결합) — 아직 수집 전
- 원본 데이터는 용량·재배포 금지 때문에 GitHub에 올리지 않음 (.gitignore에 data/)

## 지표 정의
- PI = 영화별 평점 표준편차 / 2.25 (0.5~5.0 범위의 최대 표준편차로 정규화, 0~1)
- 평점 수 MIN_RATINGS(현재 50) 이상인 영화만 사용
- 보조 지표 후보: 극단 평점 비율, 정규화 엔트로피

## 가설 (4개)
| # | 구분 | 가설 | 근거 | 검증 방법 | 예상 |
|---|---|---|---|---|---|
| H1 | 메인 | 평균 평점과 평점 수를 통제해도 PI가 높을수록 화제성(투표 수, 태그 수)이 크다 | 의견이 갈리면 논쟁과 공유가 늘어난다 | 다중회귀에서 PI 계수의 유의성 | 양(+)의 관계 |
| H2 | 장르 | 스릴러·SF·호러에서는 PI의 효과가 드라마·가족물보다 크다 | 해석 여지가 큰 장르일수록 해석 논쟁이 많다 | PI × 장르 상호작용 | 장르별 효과 크기 차이 |
| H3 | 비선형 | 평균 평점과 화제성의 관계는 선형이 아니라 PI가 높은 구간에서만 양(+)이다 | 평균만으로는 화제성을 설명하지 못한다 | 평균 평점 구간별 PI 효과 비교, 2차항 | 구간별 차이 |
| H4 | 교란 | PI와 화제성 관계의 상당 부분은 '인기 작품일수록 다양한 이용자가 평가한다'는 효과 때문이다 | 평가자가 다양할수록 분산이 커진다 | 평점 수 통제 전후 계수 변화 | 계수 감소 |

## 진행 상황
- [x] MovieLens 25M 다운로드, 프로젝트 폴더 구조 정리, GitHub 연결
- [x] src/pi.py 작성 및 실행 → 13,176편 PI 산출, results/pi_by_movie.csv 생성
      (TOP: Santa with Muscles, The Room, God's Not Dead, Manos 등 컬트·논쟁작)
- [ ] MIN_RATINGS 50 vs 100 비교 (표본 작은 영화가 상위권에 섞임)
- [ ] 평균 평점 영향을 보정한 PI 검토 (평균이 중간일수록 표준편차가 커질 수 있는 구조)
- [ ] TMDB API 키 발급 → 화제성 데이터 수집·결합
- [ ] SQLite/PostgreSQL에 테이블 적재 + SQL 분석 쿼리 (DB 개발자 포트폴리오 포인트)
- [ ] 가설 검증, 시각화, README 정리

## 폴더 구조
- src/      분석 코드 (pi.py)
- sql/      테이블 생성·분석 쿼리
- data/     원본 데이터 (Git 제외)
- results/  산출물·그래프

## 작업 규칙
- 사용자는 Git·Python 초보. 설명은 한국어로, 짧게, 비유와 표 위주로.
- 코드를 바꾸면 무엇을 왜 바꿨는지 한두 줄로 설명할 것 (면접에서 설명할 수 있어야 함).
- API 키는 반드시 .env에만 저장하고 절대 커밋하지 않기.
- data/ 원본은 커밋 금지. 커밋 메시지는 한국어로 실제 변경 내용을 정확히.
- 실제로 계산하지 않은 수치는 지어내지 않기.

- 커밋 메시지에 Co-Authored-By 등 AI 표기 넣지 않기 

## 데이터 구조 (MovieLens 25M)
| 파일 | 컬럼 | 비고 |
|---|---|---|
| ratings.csv | userId, movieId, rating, timestamp | 약 2,500만 행. rating은 0.5~5.0, 0.5 단위 |
| movies.csv | movieId, title, genres | title에 "(1995)" 식으로 연도 포함. genres는 "Action\|Sci-Fi"처럼 \| 구분, 없으면 "(no genres listed)" |
| links.csv | movieId, imdbId, tmdbId | tmdbId 결측 있음 → TMDB 결합 시 처리 |
| tags.csv | userId, movieId, tag, timestamp | H1의 "태그 수" 계산용 |

- 25M은 고정 스냅샷(최종 분석용). 코드 테스트는 ml-latest-small로 해도 됨(DATA_DIR만 변경)
- ratings.csv는 크므로 usecols, dtype(int32/float32) 지정해서 읽기

## 변수 정의 (가설 검증용)
- PI: 위 지표 정의 참고 (results/pi_by_movie.csv)
- 화제성(종속변수): TMDB vote_count, TMDB popularity, MovieLens 태그 수
- 통제변수: 평균 평점(mean_rating), MovieLens 평점 수(n_ratings), 개봉 연도
- 주의: 화제성과 통제변수에 같은 출처의 '평점 수'를 겹쳐 쓰지 않기
- 개수형 변수(투표 수, 태그 수, 평점 수)는 치우침이 커서 log(1+x) 변환 검토

## 가설별 구현 메모
- H1: 다중회귀 (statsmodels OLS). 화제성 ~ PI + 평균 평점 + log(평점 수) + 연도
- H2: 장르 그룹 — 해석형: Thriller, Sci-Fi, Horror / 비교군: Drama, Children
  (영화 하나가 여러 장르일 수 있음 → 더미 변수로 처리). PI × 장르 상호작용항
- H3: 평균 평점 구간별로 나눠 PI 효과 비교 + 평균 평점 2차항
- H4: 평점 수를 넣기 전/후 PI 계수 변화 비교

## 지금까지 결과 (실제 실행 기준)
- 평점 25,000,095건 → 평점 50개 이상 영화 13,176편 PI 산출
- PI 최고: Santa with Muscles (0.7745), The Room (0.7400) 등 컬트·종교/정치 논쟁작
- PI 최저: Hawaii (1966) (0.2424)
- 관찰: PI 상위권 영화는 평균 평점이 2점대에 몰림 → 평균의 영향 보정 필요

## 기타 맥락
- 지산학 캡스톤멘토링 주차별 보고서(HWP)를 매주 제출 중. 4주차까지 완료
- 분석 결과는 보고서에 쓸 수 있게 "무엇을 했고, 수치가 어떻게 나왔는지" 짧게 요약해 줄 것
- TMDB 데이터 사용 시 README에 TMDB 출처 표기 필요