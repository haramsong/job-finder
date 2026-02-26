"""직군별 공고 필터링 엔진"""

import json
import re
from pathlib import Path
from dataclasses import dataclass

try:
    from crawlers.saramin import JobPosting
except ImportError:
    from backend.crawlers.saramin import JobPosting

# 마스터 데이터 로드
DATA_PATH = Path(__file__).parent / "data" / "job_categories.json"


@dataclass
class FilterResult:
    """필터링 결과"""
    posting: JobPosting
    matched: bool          # 직군에 맞는 공고인지
    matched_keywords: list[str]   # 매칭된 키워드
    excluded_keywords: list[str]  # 범위 밖 키워드


def load_categories() -> dict:
    """job_categories.json 로드"""
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)["job_categories"]


# 사이트 공통 분류 태그 및 기업 유형 (필터링에서 무시)
IGNORE_KEYWORDS = {
    "웹개발", "서버개발", "앱개발", "개발", "개발자", "엔지니어",
    "프론트엔드", "백엔드", "풀스택", "소프트웨어",
    "it", "si", "sm", "sw", "솔루션", "기타",
    "saas", "b2b", "b2c", "erp", "crm", "scm",
    "스타트업", "중소기업", "대기업", "외국계", "공기업",
    "정규직", "계약직", "인턴", "프리랜서", "파견",
    "신입", "경력", "경력무관",
    "network", "네트워크", "서버", "server", "cloud", "web", "mobile", "app",
    "database", "db", "api", "system", "security", "data",
}


def filter_postings(
    postings: list[JobPosting],
    category_id: str,
    location: str | None = None,
    allowed_keywords: list[str] | None = None,
) -> list[FilterResult]:
    """공고 목록을 직군 기준으로 필터링

    Args:
        postings: 크롤링된 공고 목록
        category_id: 직군 ID (예: "publisher", "frontend")
        location: 지역 필터 (예: "서울", "경기"). None이면 전체
        allowed_keywords: 허용할 키워드 목록. None이면 직군 기본값 사용

    Returns:
        FilterResult 리스트 (matched=True인 것만 직군에 맞는 공고)
    """
    categories = load_categories()
    category = categories[category_id]

    if allowed_keywords is not None:
        # 프론트에서 선택한 키워드 + 직군명/별칭은 항상 허용
        allowed = {
            kw.lower()
            for kw in (
                [category["name"]]
                + category.get("aliases", [])
                + allowed_keywords
            )
        }
    else:
        # 기본: 직군명 + 별칭 + 핵심 + 보조 전부 허용
        allowed = {
            kw.lower()
            for kw in (
                [category["name"]]
                + category.get("aliases", [])
                + category["core_keywords"]
                + category["auxiliary_keywords"]
            )
        }

    # 제목 필터용 키워드 (대소문자 무시)
    title_keywords = [kw.lower() for kw in category.get("title_keywords", [category["name"]])]

    results = []
    for posting in postings:
        # 제목에 직군 관련 키워드가 하나도 없으면 아예 제외
        title_lower = posting.title.lower()
        if not any(tk in title_lower for tk in title_keywords):
            continue

        # 지역 필터
        if location and not _match_location(location, posting.conditions):
            continue

        matched_kw = []
        excluded_kw = []

        for kw in posting.keywords:
            kw_lower = kw.lower()
            # 공통 분류 태그는 무시
            if kw_lower in IGNORE_KEYWORDS:
                continue
            # 허용 범위에 포함되는지 확인 (부분 매칭)
            if _is_allowed(kw_lower, allowed):
                matched_kw.append(kw)
            else:
                excluded_kw.append(kw)

        # 범위 밖 키워드가 없으면 매칭
        results.append(FilterResult(
            posting=posting,
            matched=len(excluded_kw) == 0,
            matched_keywords=matched_kw,
            excluded_keywords=excluded_kw,
        ))

    return results


# 지역명 한영 매핑
LOCATION_MAP = {
    "서울": ["서울", "seoul"],
    "경기": ["경기", "gyeonggi"],
    "인천": ["인천", "incheon"],
    "부산": ["부산", "busan"],
    "대구": ["대구", "daegu"],
    "대전": ["대전", "daejeon"],
    "광주": ["광주", "gwangju"],
    "울산": ["울산", "ulsan"],
    "세종": ["세종", "sejong"],
    "강원": ["강원", "gangwon"],
    "충북": ["충북", "chungbuk"],
    "충남": ["충남", "chungnam"],
    "전북": ["전북", "jeonbuk"],
    "전남": ["전남", "jeonnam"],
    "경북": ["경북", "gyeongbuk"],
    "경남": ["경남", "gyeongnam"],
    "제주": ["제주", "jeju"],
}


def _match_location(location: str, conditions: list[str]) -> bool:
    """지역 필터 매칭 (한영 모두 지원)"""
    variants = LOCATION_MAP.get(location, [location])
    for cond in conditions:
        cond_lower = cond.lower()
        if any(v.lower() in cond_lower for v in variants):
            return True
    return False


def _normalize(s: str) -> str:
    """비교용 정규화: 공백, 특수문자 제거 + 소문자"""
    return re.sub(r'[\s\-_./]', '', s).lower()


def _is_allowed(keyword: str, allowed_set: set[str]) -> bool:
    """키워드가 허용 범위에 포함되는지 확인 (부분 매칭 지원)"""
    if keyword in allowed_set:
        return True
    kw_norm = _normalize(keyword)
    for allowed_kw in allowed_set:
        if allowed_kw in keyword or keyword in allowed_kw:
            return True
        # 정규화 후 비교 (REST API vs restapi 등)
        aw_norm = _normalize(allowed_kw)
        if aw_norm in kw_norm or kw_norm in aw_norm:
            return True
    return False


# 직접 실행 시 테스트
if __name__ == "__main__":
    from backend.crawlers.saramin import crawl

    print("=== 퍼블리셔 공고 필터링 테스트 (서울) ===\n")
    postings = crawl("퍼블리셔", pages=1)
    results = filter_postings(postings, "publisher", location="서울")

    matched = [r for r in results if r.matched]
    excluded = [r for r in results if not r.matched]

    print(f"전체: {len(results)}개 | ✅ 매칭: {len(matched)}개 | ❌ 제외: {len(excluded)}개\n")

    print("--- ✅ 매칭된 공고 (상위 5개) ---")
    for r in matched[:5]:
        print(f"  [{r.posting.company}] {r.posting.title}")
        print(f"    키워드: {', '.join(r.posting.keywords)}")
        print()

    print("--- ❌ 제외된 공고 (상위 5개) ---")
    for r in excluded[:5]:
        print(f"  [{r.posting.company}] {r.posting.title}")
        print(f"    키워드: {', '.join(r.posting.keywords)}")
        print(f"    ⚠ 범위 밖: {', '.join(r.excluded_keywords)}")
        print(f"    링크: {r.posting.link}")
        print()
