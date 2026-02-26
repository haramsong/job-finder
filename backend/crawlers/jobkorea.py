"""잡코리아 채용 공고 크롤러 (Playwright 기반)"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
try:
    from crawlers.saramin import JobPosting
except ImportError:
    from backend.crawlers.saramin import JobPosting


BASE_URL = "https://www.jobkorea.co.kr/Search/"


def crawl(keyword: str, pages: int = 1) -> list[JobPosting]:
    """잡코리아에서 키워드로 채용 공고를 검색하여 반환"""
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        for pg in range(1, pages + 1):
            url = f"{BASE_URL}?stext={keyword}&tabType=recruit&Page_No={pg}"
            page.goto(url, timeout=15000)
            page.wait_for_timeout(5000)

            html = page.content()
            postings = _parse_page(html)
            results.extend(postings)

        browser.close()

    return results


def _parse_page(html: str) -> list[JobPosting]:
    """페이지 HTML에서 공고 파싱"""
    soup = BeautifulSoup(html, "html.parser")
    postings = []

    # 공고 링크 수집 (중복 제거)
    seen_urls = set()
    job_links = soup.find_all("a", href=lambda h: h and "/Recruit/GI_Read/" in h)

    for link in job_links:
        href = link["href"]
        text = link.get_text(strip=True)

        # URL 기준 중복 제거
        base_url = href.split("?")[0]
        if base_url in seen_urls or not text:
            continue

        # 제목이 있는 링크 (회사명 링크는 짧은 경우가 많음)
        parent_class = " ".join(link.parent.get("class", []))

        if "mb_space" in parent_class:
            # 제목 링크
            title = text
            company = _find_company(link, href, soup)
            keywords = _find_keywords(link)

            seen_urls.add(base_url)
            postings.append(JobPosting(
                company=company,
                title=title,
                link=href,
                conditions=[],
                keywords=keywords,
                source="jobkorea",
            ))

    return postings


def _find_company(title_link, href: str, soup) -> str:
    """제목 링크 근처에서 회사명 찾기"""
    # 같은 href를 가진 다른 링크 중 회사명 찾기
    for a in soup.find_all("a", href=href):
        if a != title_link:
            text = a.get_text(strip=True)
            if text and len(text) < 50:
                return text
    return "N/A"


def _find_keywords(title_link) -> list[str]:
    """제목 링크 근처에서 직무 키워드 찾기"""
    container = title_link.parent
    if container:
        container = container.parent
    if not container:
        return []

    # 노이즈 키워드 제외
    noise = {"스크랩", "즉시 지원", "•", "합격축하금", "경력", "신입", "신입·경력"}

    keywords = []
    for span in container.find_all("span"):
        text = span.get_text(strip=True)
        if not text or len(text) > 30:
            continue
        if "등록" in text or "마감" in text or "만원" in text:
            continue
        if text.startswith("경력") or text.startswith("신입"):
            continue
        # 쉼표로 구분된 키워드 분리
        for kw in text.split(","):
            kw = kw.strip()
            if kw and kw not in noise and kw not in keywords:
                keywords.append(kw)
    return keywords


if __name__ == "__main__":
    postings = crawl("퍼블리셔", pages=1)
    print(f"총 {len(postings)}개 공고 수집\n")

    for p in postings[:5]:
        print(f"[{p.company}] {p.title}")
        print(f"  키워드: {', '.join(p.keywords)}")
        print(f"  링크: {p.link}")
        print()
