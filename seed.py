import os
import sqlite3
from pathlib import Path

import requests

from crawler import RSS_URL, fetch_rss, parse_items


def get_db_path() -> Path:
    default_db_path = Path(__file__).resolve().parent / "board.sqlite3"
    return Path(os.environ.get("DATABASE_PATH", str(default_db_path)))


def init_db(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()


def insert_posts(conn: sqlite3.Connection, news_items: list[dict]) -> int:
    inserted_count = 0

    for item in news_items:
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()
        link = item.get("link", "").strip()
        published_at = item.get("published_at", "").strip()

        if not title:
            continue

        exists = conn.execute(
            "SELECT 1 FROM posts WHERE title = ? LIMIT 1",
            (title,),
        ).fetchone()
        if exists:
            continue

        content_lines = [summary or "요약 없음"]
        if link:
            content_lines.append(f"원문: {link}")
        if published_at:
            content_lines.append(f"발행: {published_at}")

        content = "\n".join(content_lines)

        conn.execute(
            "INSERT INTO posts (title, content) VALUES (?, ?)",
            (title, content),
        )
        inserted_count += 1

    conn.commit()
    return inserted_count


def main() -> None:
    xml_text = fetch_rss(RSS_URL)
    news_items = parse_items(xml_text, limit=10)

    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        init_db(conn)
        inserted_count = insert_posts(conn, news_items)

    print(f"{inserted_count}건 추가됨")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as e:
        print(f"RSS 요청 중 오류가 발생했습니다: {e}")
        raise
