"""Job Finder API 서버"""

import json
import os

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

try:
    from crawlers.saramin import JobPosting
    from filter_engine import filter_postings, load_categories
except ImportError:
    from backend.crawlers.saramin import JobPosting
    from backend.filter_engine import filter_postings, load_categories

app = FastAPI(title="Job Finder API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://d1ujto181dgh1n.cloudfront.net",
        "https://job-finder.hrsong.com",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Step Functions 클라이언트 (Lambda 환경에서만 활성화)
SFN_ARN = os.environ.get("CRAWL_STATE_MACHINE_ARN", "")
try:
    import boto3
    sfn_client = boto3.client("stepfunctions") if SFN_ARN else None
except ImportError:
    sfn_client = None


def _crawl_via_step_functions(keyword: str, category: str, pages: int) -> list[JobPosting]:
    """Step Functions로 병렬 크롤링 실행 (동기)"""
    resp = sfn_client.start_sync_execution(
        stateMachineArn=SFN_ARN,
        input=json.dumps({"keyword": keyword, "category": category, "pages": pages}),
    )
    if resp["status"] != "SUCCEEDED":
        print(f"Step Functions 실패: {resp.get('error')}")
        return []

    output = json.loads(resp["output"])
    postings = []
    # Parallel State 결과는 각 브랜치 결과의 리스트
    for branch_result in output:
        for p in branch_result.get("postings", []):
            postings.append(JobPosting(**p))
    return postings


def _crawl_via_threads(keyword: str, category: str, pages: int) -> list[JobPosting]:
    """로컬 개발용: ThreadPoolExecutor로 병렬 크롤링"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    try:
        from crawlers import saramin, wanted, incruit, linkedin, remember, rallit, jumpit
        from crawlers.wanted import TAG_MAP as WANTED_TAG_MAP
    except ImportError:
        from backend.crawlers import saramin, wanted, incruit, linkedin, remember, rallit, jumpit
        from backend.crawlers.wanted import TAG_MAP as WANTED_TAG_MAP

    crawlers = [
        ("saramin", saramin), ("wanted", wanted), ("incruit", incruit),
        ("linkedin", linkedin), ("remember", remember), ("rallit", rallit), ("jumpit", jumpit),
    ]

    def _run(name, crawler):
        if name == "wanted":
            return crawler.crawl(keyword, pages=pages, tag_id=WANTED_TAG_MAP.get(category))
        return crawler.crawl(keyword, pages=pages)

    postings = []
    with ThreadPoolExecutor(max_workers=len(crawlers)) as pool:
        futures = {pool.submit(_run, n, c): n for n, c in crawlers}
        for f in as_completed(futures):
            try:
                postings.extend(f.result())
            except Exception as e:
                print(f"[{futures[f]}] 크롤링 실패: {e}")
    return postings


@app.get("/api/categories")
def get_categories():
    """직군 목록 반환"""
    categories = load_categories()
    return [
        {"id": k, "name": v["name"], "core_keywords": v["core_keywords"], "auxiliary_keywords": v["auxiliary_keywords"]}
        for k, v in categories.items()
    ]


@app.get("/api/jobs")
def get_jobs(
    category: str = Query(..., description="직군 ID (예: publisher)"),
    keyword: str | None = Query(None, description="검색 키워드 (없으면 직군명으로 검색)"),
    location: str | None = Query(None, description="지역 필터 (예: 서울)"),
    allowed_keywords: list[str] | None = Query(None, description="허용 키워드 목록 (없으면 전체)"),
    matched_page: int = Query(1, ge=1, description="매칭 공고 페이지"),
    excluded_page: int = Query(1, ge=1, description="제외 공고 페이지"),
    page_size: int = Query(20, ge=1, le=500, description="페이지당 공고 수"),
    crawl_pages: int = Query(1, ge=1, le=5, description="크롤링 페이지 수"),
):
    """7개 사이트에서 공고 수집 + 필터링 + 페이지네이션 결과 반환"""
    categories = load_categories()
    if category not in categories:
        return {"error": f"존재하지 않는 직군: {category}"}

    search_keyword = keyword or categories[category]["name"]

    # Lambda 환경이면 Step Functions, 로컬이면 ThreadPoolExecutor
    if sfn_client and SFN_ARN:
        all_postings = _crawl_via_step_functions(search_keyword, category, crawl_pages)
    else:
        all_postings = _crawl_via_threads(search_keyword, category, crawl_pages)

    # 필터링
    results = filter_postings(all_postings, category, location=location, allowed_keywords=allowed_keywords)

    matched_all = _round_robin([r for r in results if r.matched], len(results))
    excluded_all = _round_robin([r for r in results if not r.matched], len(results))

    # 페이지네이션 적용
    def _paginate(items, pg, sz):
        start = (pg - 1) * sz
        return items[start:start + sz]

    matched_items = _paginate(matched_all, matched_page, page_size)
    excluded_items = _paginate(excluded_all, excluded_page, page_size)

    return {
        "matched_count": len(matched_all),
        "excluded_count": len(excluded_all),
        "page_size": page_size,
        "matched_page": matched_page,
        "matched_total_pages": max(1, (len(matched_all) + page_size - 1) // page_size),
        "excluded_page": excluded_page,
        "excluded_total_pages": max(1, (len(excluded_all) + page_size - 1) // page_size),
        "matched": [_to_dict(r) for r in matched_items],
        "excluded": [_to_dict(r) for r in excluded_items],
    }


def _round_robin(items: list, limit: int) -> list:
    """사이트별로 번갈아 가며 골고루 선택"""
    from collections import defaultdict
    by_source = defaultdict(list)
    for item in items:
        by_source[item.posting.source].append(item)

    result = []
    queues = list(by_source.values())
    idx = 0
    while len(result) < limit and queues:
        queue = queues[idx % len(queues)]
        if queue:
            result.append(queue.pop(0))
        else:
            queues.pop(idx % len(queues))
            continue
        idx += 1
    return result


def _to_dict(r) -> dict:
    return {
        "source": r.posting.source,
        "company": r.posting.company,
        "title": r.posting.title,
        "link": r.posting.link,
        "conditions": r.posting.conditions,
        "keywords": r.posting.keywords,
        "matched_keywords": r.matched_keywords,
        "excluded_keywords": r.excluded_keywords,
    }
