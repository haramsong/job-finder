"""크롤러 Lambda 핸들러 - Step Functions에서 호출"""

from dataclasses import asdict
from crawlers import saramin, wanted, incruit, remember, rallit, jumpit
from crawlers.wanted import TAG_MAP as WANTED_TAG_MAP

CRAWLERS = {
    "saramin": saramin,
    "wanted": wanted,
    "incruit": incruit,
    "remember": remember,
    "rallit": rallit,
    "jumpit": jumpit,
}


def handler(event, context):
    """개별 크롤러 실행 후 결과 반환"""
    crawler_name = event["crawler"]
    keyword = event["keyword"]
    pages = event.get("pages", 1)
    category = event.get("category")

    crawler = CRAWLERS.get(crawler_name)
    if not crawler:
        return {"postings": [], "error": f"알 수 없는 크롤러: {crawler_name}"}

    try:
        if crawler_name == "wanted" and category:
            tag_id = WANTED_TAG_MAP.get(category)
            postings = crawler.crawl(keyword, pages=pages, tag_id=tag_id)
        else:
            postings = crawler.crawl(keyword, pages=pages)

        return {"postings": [asdict(p) for p in postings]}
    except Exception as e:
        print(f"[{crawler_name}] 크롤링 실패: {e}")
        return {"postings": [], "error": str(e)}
