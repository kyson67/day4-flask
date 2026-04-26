import sys

import requests
from bs4 import BeautifulSoup

RSS_URL = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
MAX_ITEMS = 10


def fetch_rss(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; NewsRSSCrawler/1.0)"
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.text


def parse_items(xml_text: str, limit: int = 10):
    soup = BeautifulSoup(xml_text, "xml")
    items = soup.find_all("item")[:limit]

    results = []
    for item in items:
        title = item.title.get_text(strip=True) if item.title else "제목 없음"
        link = item.link.get_text(strip=True) if item.link else "링크 없음"
        pub_date = item.pubDate.get_text(strip=True) if item.pubDate else "발행시간 없음"

        raw_description = item.description.get_text(strip=True) if item.description else ""
        summary = BeautifulSoup(raw_description, "html.parser").get_text(" ", strip=True)
        if not summary:
            summary = "요약 없음"

        results.append(
            {
                "title": title,
                "summary": summary,
                "link": link,
                "published_at": pub_date,
            }
        )

    return results


def print_items(items):
    print("=" * 80)
    print(f"뉴스 {len(items)}건")
    print("=" * 80)

    for i, news in enumerate(items, start=1):
        print(f"[{i}] {news['title']}")
        print(f"- 요약: {news['summary']}")
        print(f"- 링크: {news['link']}")
        print(f"- 발행: {news['published_at']}")
        print("-" * 80)


if __name__ == "__main__":
    
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    try:
        xml_text = fetch_rss(RSS_URL)
        news_items = parse_items(xml_text, limit=MAX_ITEMS)
        print_items(news_items)
    except requests.RequestException as e:
        print(f"RSS 요청 중 오류가 발생했습니다: {e}")
