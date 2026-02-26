"""점핏 채용 공고 크롤러 (REST API)"""

import re
import requests
try:
    from crawlers.saramin import JobPosting
except ImportError:
    from backend.crawlers.saramin import JobPosting

API_URL = "https://jumpit-api.saramin.co.kr/api/positions"

# 직군 → 지역 태그 매핑
LOCATION_TAG = {
    "서울": 101000, "경기": 102000, "인천": 108000, "부산": 106000,
    "대구": 104000, "광주": 103000, "대전": 105000, "울산": 107000,
    "세종": 118000, "강원": 109000, "충북": 114000, "충남": 115000,
    "전북": 113000, "전남": 112000, "경북": 111000, "경남": 110000, "제주": 116000,
}


def crawl(keyword: str, pages: int = 1, location: str | None = None) -> list[JobPosting]:
    """점핏에서 키워드로 채용 공고 검색"""
    results = []

    for page in range(1, pages + 1):
        params = {"keyword": keyword, "sort": "relation", "page": page}
        if location and location in LOCATION_TAG:
            params["locationTag"] = LOCATION_TAG[location]

        resp = requests.get(API_URL, params=params, timeout=10)
        data = resp.json().get("result", {})

        for p in data.get("positions", []):
            # 제목에서 <span> 태그 제거
            title = re.sub(r"<[^>]+>", "", p.get("title", ""))
            conditions = p.get("locations", [])
            # 경력
            min_c = p.get("minCareer")
            max_c = p.get("maxCareer")
            if min_c is not None and max_c and max_c > min_c:
                conditions.append(f"경력 {min_c}~{max_c}년")
            elif min_c == 0 and max_c == 0:
                conditions.append("신입")
            elif min_c:
                conditions.append(f"경력 {min_c}년↑")
            results.append(JobPosting(
                company=p.get("companyName", ""),
                title=title,
                link=f"https://www.jumpit.co.kr/position/{p['id']}",
                conditions=conditions,
                keywords=p.get("techStacks", []),
                source="jumpit",
            ))

    return results
