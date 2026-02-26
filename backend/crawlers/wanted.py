"""원티드 채용 공고 크롤러 (API 기반)"""

import requests
try:
    from crawlers.saramin import JobPosting
except ImportError:
    from backend.crawlers.saramin import JobPosting

BASE_URL = "https://www.wanted.co.kr/api/v4/jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

# 원티드 직군 태그 매핑
TAG_MAP = {
    "frontend": 669,
    "backend": 872,
    "fullstack": 873,
    "android": 677,
    "ios": 678,
    "devops": 674,
}


def crawl(keyword: str, pages: int = 1, tag_id: int | None = None) -> list[JobPosting]:
    """원티드에서 채용 공고를 가져옴

    Args:
        keyword: 검색 키워드 (제목 필터링용)
        pages: 페이지 수 (1페이지 = 20개)
        tag_id: 원티드 직군 태그 ID (없으면 전체)
    """
    results = []
    limit = 20

    for pg in range(pages):
        params = {
            "country": "kr",
            "locations": "all",
            "years": -1,
            "limit": limit,
            "offset": pg * limit,
        }
        if tag_id:
            params["tag_type_ids"] = tag_id

        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        jobs = resp.json().get("data", [])
        if not jobs:
            break

        for job in jobs:
            posting = _parse_job(job)
            # 키워드가 제목에 포함된 것만 필터
            if keyword and keyword.lower() not in posting.title.lower():
                continue
            results.append(posting)

    return results


def _parse_job(job: dict) -> JobPosting:
    company = job.get("company", {}).get("name", "N/A")
    position = job.get("position", "N/A")
    job_id = job.get("id", "")
    link = f"https://www.wanted.co.kr/wd/{job_id}"
    location = job.get("address", {}).get("location", "")
    district = job.get("address", {}).get("district", "")

    conditions = []
    if location:
        conditions.append(f"{location} {district}".strip())

    return JobPosting(
        company=company,
        title=position,
        link=link,
        conditions=conditions,
        keywords=[],  # 원티드 API는 skill_tags가 비어있음
        source="wanted",
    )


if __name__ == "__main__":
    # 프론트엔드 태그로 조회 후 퍼블리셔 키워드 필터
    postings = crawl("퍼블리셔", pages=3, tag_id=TAG_MAP.get("frontend"))
    print(f"원티드 - '퍼블리셔' 검색 결과: {len(postings)}개\n")
    for p in postings[:5]:
        print(f"[{p.company}] {p.title}")
        print(f"  조건: {', '.join(p.conditions)}")
        print(f"  링크: {p.link}")
        print()

    # 태그 없이 전체에서 검색
    postings2 = crawl("퍼블리셔", pages=5)
    print(f"원티드 - 전체에서 '퍼블리셔' 검색: {len(postings2)}개\n")
    for p in postings2[:5]:
        print(f"[{p.company}] {p.title}")
        print()
