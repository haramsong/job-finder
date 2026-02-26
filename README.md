# 🔍 Job Finder

여러 구인구직 사이트의 채용 공고를 한 곳에서 검색하고, 직군별 실제 요구사항을 분석하여 직군과 맞지 않는 공고를 자동으로 필터링해주는 서비스입니다.

## 왜 만들었나?

- "퍼블리셔" 공고인데 React, Vue를 요구하거나, "백엔드" 공고인데 PM 업무를 포함하는 등 **직군명과 실제 요구 기술이 불일치**하는 경우가 많습니다
- 사람인, 원티드, 인크루트 등 **여러 사이트를 일일이 확인**해야 하는 번거로움이 있습니다
- Job Finder는 이 문제를 해결하기 위해 공고를 수집하고, 직군별 키워드 기반으로 매칭/제외를 자동 판별합니다

## 주요 기능

- **멀티 사이트 통합 검색**: 7개 사이트에서 동시에 공고를 수집 (Step Functions 병렬 크롤링)
- **직군별 키워드 필터링**: 핵심/보조 키워드 기반으로 매칭 여부 자동 판별
- **제목 기반 사전 필터**: 공고 제목에 직군 관련 키워드가 없으면 아예 제외
- **키워드 커스터마이징**: 핵심/보조 키워드를 칩(Chip) UI로 개별 선택/해제 가능
- **지역 필터**: 서울, 경기 등 지역별 필터링
- **제외 공고 확인**: 탈락 사유 키워드를 빨간색으로 강조 표시
- **반응형 UI**: 데스크톱은 페이지네이션, 모바일은 무한 스크롤
- **PWA**: 모바일 홈 화면 추가, 오프라인 정적 자산 캐시

## 지원 크롤링 사이트

| 사이트 | 방식 | 상태 | conditions 정보 |
|--------|------|------|-----------------|
| 사람인 | HTML 크롤링 | ✅ 활성 | 지역, 경력, 학력, 고용형태 |
| 원티드 | JSON API | ✅ 활성 | 지역, 경력 |
| 인크루트 | HTML 크롤링 | ✅ 활성 | 지역, 경력, 학력, 고용형태 |
| 링크드인 | HTML 크롤링 | ✅ 활성 | 지역 |
| 리멤버 | REST API | ✅ 활성 | 지역, 경력, 학력 |
| 랠릿 | REST API | ✅ 활성 | 지역 |
| 점핏 | REST API | ✅ 활성 | 지역, 경력 |
| 잡코리아 | Playwright (CSR) | ⏸️ 임시 제외 (속도 이슈) | - |

## 지원 직군 (11개)

퍼블리셔, 프론트엔드, 백엔드, 웹디자이너, 풀스택, 안드로이드, iOS, DevOps, 보안 엔지니어, 시스템 엔지니어, 클라우드 엔지니어

## 프로젝트 구조

```
job-finder/
├── backend/                  # FastAPI 백엔드 (Lambda)
│   ├── main.py               # API 서버 (Mangum으로 Lambda 래핑)
│   ├── handler.py            # Lambda 핸들러 (API)
│   ├── crawl_handler.py      # Lambda 핸들러 (크롤러)
│   ├── filter_engine.py      # 키워드 매칭 필터링 엔진
│   ├── data/
│   │   └── job_categories.json  # 직군별 키워드 마스터 데이터
│   └── crawlers/             # 사이트별 크롤러
│       ├── saramin.py
│       ├── wanted.py
│       ├── incruit.py
│       ├── linkedin.py
│       ├── remember.py
│       ├── rallit.py
│       └── jumpit.py
├── frontend/                 # Next.js 프론트엔드 (정적 빌드, PWA)
│   └── src/app/page.tsx      # 메인 페이지
├── statemachine/
│   └── crawl.asl.json        # Step Functions 상태 머신 정의
├── template.yaml             # SAM 템플릿
├── samconfig.toml            # SAM 배포 설정
└── .github/workflows/
    └── deploy-frontend.yml   # 프론트엔드 CI/CD
```

## 기술 스택

| 영역 | 기술 |
|------|------|
| 프론트엔드 | Next.js 16, TypeScript, Tailwind CSS 4, PWA |
| 백엔드 | Python 3.12, FastAPI, Mangum |
| 데이터 수집 | requests, BeautifulSoup, REST API |
| 인프라 | API Gateway (HTTP API), Lambda (arm64), Step Functions (Express) |
| 배포 | S3 + CloudFront (프론트), SAM (백엔드) |
| CI/CD | GitHub Actions (OIDC + assume role chaining) |

## 배포 구성

| 구성 요소 | 리소스 |
|-----------|--------|
| 프론트엔드 | S3 + CloudFront → job-finder.hrsong.com |
| 백엔드 API | API Gateway + Lambda (FastAPI + Mangum) |
| 크롤링 | Step Functions (Express) → 사이트별 Lambda 병렬 실행 |
| API URL 관리 | AWS Parameter Store (/job-finder/api-url) |
| DNS | Route53 → CloudFront (A Alias) |
| 인증서 | ACM *.hrsong.com (us-east-1) |

## 실행 방법

### 백엔드 (로컬)

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

로컬에서는 Step Functions 대신 ThreadPoolExecutor로 병렬 크롤링합니다.

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

### 배포

```bash
sam build && sam deploy
```

## 필터링 방식

1. **제목 필터**: 공고 제목에 직군 관련 키워드(`title_keywords`)가 포함되어야 결과에 노출
2. **키워드 매칭**: 공고의 요구 기술을 핵심(`core`) + 보조(`auxiliary`) 키워드와 비교
3. **매칭 판정**: 허용 범위 밖 키워드가 없으면 매칭, 있으면 제외
4. **사이트 균형**: 라운드 로빈으로 여러 사이트의 공고를 골고루 표시

## API

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/categories` | 직군 목록 + 키워드 반환 |
| `GET /api/jobs?category=publisher&location=서울` | 공고 검색 + 필터링 |

## 라이선스

MIT
