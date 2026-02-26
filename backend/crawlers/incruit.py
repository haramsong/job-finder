"""인크루트 채용 공고 크롤러"""

import requests
from bs4 import BeautifulSoup
try:
    from crawlers.saramin import JobPosting
except ImportError:
    from backend.crawlers.saramin import JobPosting

BASE_URL = "https://search.incruit.com/list/search.asp"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def crawl(keyword: str, pages: int = 1) -> list[JobPosting]:
    """인크루트에서 키워드로 채용 공고를 검색하여 반환"""
    results = []

    for page in range(1, pages + 1):
        params = {"col": "job", "kw": keyword, "page": page}
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for item in soup.select(".c_col"):
            posting = _parse_item(item)
            if posting:
                results.append(posting)

    return results


def _parse_item(item) -> JobPosting | None:
    title_el = item.select_one(".cell_mid .cl_top a")
    company_el = item.select_one(".cell_first .cl_top a")
    if not title_el:
        return None

    title = title_el.get_text(strip=True)
    company = company_el.get_text(strip=True) if company_el else "N/A"
    link = title_el.get("href", "")
    conditions = [
        el.get_text(strip=True)
        for el in item.select(".cell_mid .cl_md span")
    ]

    return JobPosting(
        company=company,
        title=title,
        link=link,
        conditions=conditions,
        keywords=[],  # 인크루트는 직무 키워드 태그 없음
        source="incruit",
    )


if __name__ == "__main__":
    postings = crawl("퍼블리셔", pages=1)
    print(f"총 {len(postings)}개 공고 수집\n")
    for p in postings[:5]:
        print(f"[{p.company}] {p.title}")
        print(f"  조건: {' | '.join(p.conditions)}")
        print(f"  링크: {p.link[:80]}")
        print()
