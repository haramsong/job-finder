"""사람인 채용 공고 크롤러"""

import time
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict


@dataclass
class JobPosting:
    """채용 공고 데이터"""
    company: str
    title: str
    link: str
    conditions: list[str]  # 지역, 경력, 학력, 고용형태
    keywords: list[str]    # 직무 키워드
    source: str = "saramin"


BASE_URL = "https://www.saramin.co.kr/zf_user/search/recruit"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.saramin.co.kr/",
}


def crawl(keyword: str, pages: int = 1) -> list[JobPosting]:
    """사람인에서 키워드로 채용 공고를 검색하여 반환

    Args:
        keyword: 검색 키워드 (예: "퍼블리셔")
        pages: 크롤링할 페이지 수

    Returns:
        JobPosting 리스트
    """
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for page in range(1, pages + 1):
        if page > 1:
            time.sleep(1)  # 페이지 간 딜레이

        params = {
            "searchType": "search",
            "searchword": keyword,
            "recruitPage": page,
            "recruitSort": "relation",
            "recruitPageCount": 40,
        }

        resp = session.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".item_recruit")

        for item in items:
            posting = _parse_item(item)
            if posting:
                results.append(posting)

    return results


def _parse_item(item) -> JobPosting | None:
    """공고 항목 하나를 파싱"""
    # 회사명
    company_el = item.select_one(".corp_name a")
    if not company_el:
        return None
    company = company_el.get_text(strip=True)

    # 제목 & 링크
    title_el = item.select_one(".job_tit a")
    if not title_el:
        return None
    title = title_el.get_text(strip=True)
    link = "https://www.saramin.co.kr" + title_el.get("href", "")

    # 조건 (지역, 경력, 학력, 고용형태)
    conditions = [
        el.get_text(strip=True)
        for el in item.select(".job_condition span")
    ]

    # 직무 키워드
    keywords = [
        el.get_text(strip=True)
        for el in item.select(".job_sector a, .job_sector span")
        if el.get_text(strip=True) and "등록일" not in el.get_text() and "수정일" not in el.get_text()
    ]

    return JobPosting(
        company=company,
        title=title,
        link=link,
        conditions=conditions,
        keywords=keywords,
    )


# 직접 실행 시 테스트
if __name__ == "__main__":
    import json

    postings = crawl("퍼블리셔", pages=1)
    print(f"총 {len(postings)}개 공고 수집\n")

    for p in postings[:5]:
        print(f"[{p.company}] {p.title}")
        print(f"  조건: {' | '.join(p.conditions)}")
        print(f"  키워드: {', '.join(p.keywords)}")
        print(f"  링크: {p.link}")
        print()
