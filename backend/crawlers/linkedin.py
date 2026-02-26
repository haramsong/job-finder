"""링크드인 채용 공고 크롤러"""

import requests
from bs4 import BeautifulSoup
try:
    from crawlers.saramin import JobPosting
except ImportError:
    from backend.crawlers.saramin import JobPosting

BASE_URL = "https://www.linkedin.com/jobs/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def crawl(keyword: str, pages: int = 1) -> list[JobPosting]:
    """링크드인에서 키워드로 채용 공고를 검색하여 반환

    참고: 비로그인 시 공고 수가 제한됨 (약 3개)
    """
    results = []

    for page in range(pages):
        params = {
            "keywords": keyword,
            "location": "South Korea",
            "start": page * 25,
        }
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for card in soup.select(".base-card"):
            posting = _parse_card(card)
            if posting:
                results.append(posting)

    return results


def _parse_card(card) -> JobPosting | None:
    title_el = card.select_one(".base-search-card__title")
    company_el = card.select_one(".base-search-card__subtitle")
    location_el = card.select_one(".job-search-card__location")
    link_el = card.select_one("a")

    if not title_el:
        return None

    title = title_el.get_text(strip=True)
    company = company_el.get_text(strip=True) if company_el else "N/A"
    location = location_el.get_text(strip=True) if location_el else ""
    link = link_el.get("href", "") if link_el else ""

    conditions = [location] if location else []

    return JobPosting(
        company=company,
        title=title,
        link=link,
        conditions=conditions,
        keywords=[],  # 링크드인은 검색 결과에서 키워드 태그 없음
        source="linkedin",
    )


if __name__ == "__main__":
    postings = crawl("퍼블리셔", pages=1)
    print(f"총 {len(postings)}개 공고 수집\n")
    for p in postings[:5]:
        print(f"[{p.company}] {p.title}")
        print(f"  지역: {', '.join(p.conditions)}")
        print(f"  링크: {p.link[:80]}")
        print()
