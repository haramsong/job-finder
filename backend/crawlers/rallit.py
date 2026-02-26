"""랠릿 채용 공고 크롤러 (API 기반)"""

import requests
from backend.crawlers.saramin import JobPosting

BASE_URL = "https://b2c-api.rallit.com/client/api/v1/position"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

# 랠릿 지역 코드 매핑
REGION_MAP = {
    "서울": "SEOUL", "경기": "GYEONGGI", "인천": "INCHEON",
    "부산": "BUSAN", "대구": "DAEGU", "대전": "DAEJEON",
    "광주": "GWANGJU", "울산": "ULSAN", "세종": "SEJONG",
    "강원": "GANGWON", "제주": "JEJU",
}


def crawl(keyword: str, pages: int = 1) -> list[JobPosting]:
    """랠릿에서 키워드로 채용 공고를 검색하여 반환"""
    results = []

    for page in range(1, pages + 1):
        params = {
            "keyword": keyword,
            "pageNumber": page,
            "pageSize": 20,
            "isPublic": "false",
        }
        resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()

        items = resp.json().get("data", {}).get("items", [])
        if not items:
            break

        for item in items:
            results.append(_parse_item(item))

    return results


def _parse_item(item: dict) -> JobPosting:
    region = item.get("addressRegion", "")
    # 지역 코드를 한글로 변환
    region_kr = next((k for k, v in REGION_MAP.items() if v == region), region)

    return JobPosting(
        company=item.get("companyName", "N/A"),
        title=item.get("title", ""),
        link=item.get("url", f"https://www.rallit.com/positions/{item.get('id', '')}"),
        conditions=[region_kr] if region_kr else [],
        keywords=item.get("jobSkillKeywords", []),
        source="rallit",
    )


if __name__ == "__main__":
    postings = crawl("퍼블리셔", pages=1)
    print(f"총 {len(postings)}개 공고 수집\n")
    for p in postings[:5]:
        print(f"[{p.company}] {p.title}")
        print(f"  지역: {', '.join(p.conditions)}")
        print(f"  키워드: {', '.join(p.keywords)}")
        print(f"  링크: {p.link}")
        print()
