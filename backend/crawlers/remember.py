"""리멤버 채용 공고 크롤러 (API 기반)"""

import requests
try:
    from crawlers.saramin import JobPosting
except ImportError:
    from backend.crawlers.saramin import JobPosting

BASE_URL = "https://career-api.rememberapp.co.kr/job_postings/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def crawl(keyword: str, pages: int = 1) -> list[JobPosting]:
    """리멤버에서 키워드로 채용 공고를 검색하여 반환"""
    results = []

    for page in range(1, pages + 1):
        body = {
            "search": {
                "include_applied_job_posting": False,
                "leader_position": False,
                "organization_type": "all",
                "application_type": "all",
                "keywords": [keyword],
            },
            "sort": "starts_at_desc",
            "ai_new_model": False,
            "page": page,
            "per": 30,
            "new_function_score": False,
        }
        resp = requests.post(BASE_URL, json=body, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        data = resp.json().get("data", [])
        if not data:
            break

        for job in data:
            posting = _parse_job(job)
            if posting:
                results.append(posting)

    return results


def _parse_job(job: dict) -> JobPosting | None:
    title = job.get("title", "")
    if not title:
        return None

    # 회사명: 제목에서 [] 안의 텍스트 추출, 없으면 N/A
    company_name = "N/A"
    if "[" in title and "]" in title:
        company_name = title[title.index("[") + 1:title.index("]")]

    job_id = job.get("id", "")
    link = f"https://career.rememberapp.co.kr/jobs/{job_id}"

    # 지역 정보
    addr = job.get("normalized_address") or {}
    location = addr.get("level1", "")
    district = addr.get("level2", "")
    conditions = [f"{location} {district}".strip()] if location else []

    # 자격요건에서 키워드 추출
    keywords = []
    qualifications = job.get("qualifications", "") or ""
    job_desc = job.get("job_description", "") or ""
    text = qualifications + " " + job_desc
    # 주요 기술 키워드 매칭
    tech_terms = [
        "HTML", "CSS", "JavaScript", "React", "Vue", "Angular", "TypeScript",
        "Node.js", "Python", "Java", "Spring", "Django", "FastAPI",
        "Figma", "Photoshop", "Illustrator", "XD", "Sketch",
        "웹표준", "웹접근성", "반응형", "퍼블리셔", "퍼블리싱",
        "jQuery", "SCSS", "SASS", "Bootstrap", "Git",
        "Docker", "Kubernetes", "AWS", "MySQL", "PostgreSQL",
        "Swift", "Kotlin", "Android", "iOS", "Flutter",
    ]
    for term in tech_terms:
        if term.lower() in text.lower() and term not in keywords:
            keywords.append(term)

    return JobPosting(
        company=company_name,
        title=title,
        link=link,
        conditions=conditions,
        keywords=keywords,
        source="remember",
    )


if __name__ == "__main__":
    postings = crawl("퍼블리셔", pages=1)
    print(f"총 {len(postings)}개 공고 수집\n")
    for p in postings[:5]:
        print(f"[{p.company}] {p.title}")
        print(f"  조건: {', '.join(p.conditions)}")
        print(f"  키워드: {', '.join(p.keywords)}")
        print(f"  링크: {p.link}")
        print()
