"""Job Finder API 서버"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.crawlers import saramin, wanted, incruit, linkedin, remember, rallit, jumpit
# from backend.crawlers import jobkorea  # Playwright 의존성으로 임시 제외
from backend.crawlers.wanted import TAG_MAP as WANTED_TAG_MAP
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

# 크롤러 목록 (이름, 모듈)
CRAWLERS = [
    ("saramin", saramin),
    # ("jobkorea", jobkorea),  # Playwright 사용으로 느려서 임시 제외
    ("wanted", wanted),
    ("incruit", incruit),
    ("linkedin", linkedin),
    ("remember", remember),
    ("rallit", rallit),
    ("jumpit", jumpit),
]


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

    # 모든 크롤러에서 병렬 수집
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _run_crawler(name, crawler):
        if name == "wanted":
            tag_id = WANTED_TAG_MAP.get(category)
            return crawler.crawl(search_keyword, pages=crawl_pages, tag_id=tag_id)
        return crawler.crawl(search_keyword, pages=crawl_pages)

    all_postings = []
    with ThreadPoolExecutor(max_workers=len(CRAWLERS)) as pool:
        futures = {
            pool.submit(_run_crawler, name, crawler): name
            for name, crawler in CRAWLERS
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                all_postings.extend(future.result())
            except Exception as e:
                print(f"[{name}] 크롤링 실패: {e}")

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
