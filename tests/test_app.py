from pathlib import Path

from app import app, init_db


def make_client(tmp_path):
    db_path = tmp_path / "test.sqlite3"
    app.config["TESTING"] = True
    app.config["DATABASE"] = str(db_path)
    with app.app_context():
        init_db()
    return app.test_client()


def create_post(client, title="첫 글", content="내용"):
    return client.post(
        "/posts",
        data={"title": title, "content": content},
        follow_redirects=False,
    )


def create_many_posts(client, count):
    for i in range(1, count + 1):
        create_post(client, title=f"페이지테스트-{i}", content=f"내용-{i}")


def create_many_search_posts(client, count, keyword="키워드"):
    for i in range(1, count + 1):
        create_post(client, title=f"{keyword}-제목-{i}", content=f"{keyword} 내용-{i}")


def test_list_page_renders(tmp_path):
    client = make_client(tmp_path)
    response = client.get("/posts")
    body = response.data.decode("utf-8")

    assert response.status_code == 200
    assert "아직 게시글이 없습니다" in body
    assert "1 / 1" in body
    assert 'aria-disabled="true">[처음]</span>' in body
    assert 'aria-disabled="true">[이전]</span>' in body
    assert 'aria-disabled="true">[다음]</span>' in body
    assert 'aria-disabled="true">[마지막]</span>' in body


def test_pagination_shows_10_posts_per_page(tmp_path):
    client = make_client(tmp_path)
    create_many_posts(client, 25)

    page1 = client.get("/posts?page=1").data.decode("utf-8")
    page2 = client.get("/posts?page=2").data.decode("utf-8")
    page3 = client.get("/posts?page=3").data.decode("utf-8")

    assert "1 / 3" in page1
    assert "페이지테스트-25" in page1
    assert "페이지테스트-16" in page1
    assert "페이지테스트-15" not in page1

    assert "2 / 3" in page2
    assert "페이지테스트-15" in page2
    assert "페이지테스트-6" in page2
    assert "페이지테스트-16" not in page2

    assert "3 / 3" in page3
    assert "페이지테스트-5" in page3
    assert "페이지테스트-1" in page3
    assert "페이지테스트-6" not in page3


def test_pagination_prev_next_disable_state(tmp_path):
    client = make_client(tmp_path)
    create_many_posts(client, 25)

    first_page = client.get("/posts?page=1").data.decode("utf-8")
    last_page = client.get("/posts?page=3").data.decode("utf-8")

    assert 'aria-disabled="true">[처음]</span>' in first_page
    assert 'aria-disabled="true">[이전]</span>' in first_page
    assert 'href="/posts?page=2"' in first_page
    assert 'href="/posts?page=3"' in first_page

    assert 'href="/posts?page=1"' in last_page
    assert 'href="/posts?page=2"' in last_page
    assert 'aria-disabled="true">[다음]</span>' in last_page
    assert 'aria-disabled="true">[마지막]</span>' in last_page


def test_pagination_invalid_page_values_are_sanitized(tmp_path):
    client = make_client(tmp_path)
    create_many_posts(client, 25)

    invalid_text = client.get("/posts?page=abc").data.decode("utf-8")
    invalid_zero = client.get("/posts?page=0").data.decode("utf-8")
    invalid_negative = client.get("/posts?page=-3").data.decode("utf-8")
    too_large = client.get("/posts?page=9999").data.decode("utf-8")

    assert "1 / 3" in invalid_text
    assert "1 / 3" in invalid_zero
    assert "1 / 3" in invalid_negative
    assert "3 / 3" in too_large


def test_search_filters_by_title_or_content(tmp_path):
    client = make_client(tmp_path)
    create_post(client, title="사과 파이 레시피", content="디저트 만들기")
    create_post(client, title="요리 노트", content="오늘은 사과를 다졌다")
    create_post(client, title="축구 경기", content="스포츠 이야기")

    body = client.get("/posts?q=사과").data.decode("utf-8")

    assert "사과 파이 레시피" in body
    assert "요리 노트" in body
    assert "축구 경기" not in body


def test_search_no_result_message(tmp_path):
    client = make_client(tmp_path)
    create_post(client, title="테스트 글", content="내용")

    body = client.get("/posts?q=없는검색어").data.decode("utf-8")

    assert "검색 결과가 없습니다" in body
    assert "아직 게시글이 없습니다" not in body


def test_search_results_keep_pagination_and_query_links(tmp_path):
    client = make_client(tmp_path)
    create_many_search_posts(client, 25, keyword="키워드")

    page1 = client.get("/posts?q=키워드&page=1").data.decode("utf-8")
    page2 = client.get("/posts?q=키워드&page=2").data.decode("utf-8")
    page3 = client.get("/posts?q=키워드&page=3").data.decode("utf-8")

    assert "1 / 3" in page1
    assert "2 / 3" in page2
    assert "3 / 3" in page3

    assert 'href="/posts?page=2&amp;q=%ED%82%A4%EC%9B%8C%EB%93%9C"' in page1
    assert 'href="/posts?page=3&amp;q=%ED%82%A4%EC%9B%8C%EB%93%9C"' in page1
    assert 'href="/posts?page=1&amp;q=%ED%82%A4%EC%9B%8C%EB%93%9C"' in page3


def test_sort_dropdown_exists_and_auto_submits(tmp_path):
    client = make_client(tmp_path)
    body = client.get("/posts").data.decode("utf-8")

    assert 'name="sort"' in body
    assert 'onchange="this.form.submit()"' in body
    assert "최신순" in body
    assert "오래된순" in body
    assert "제목순 (가나다)" in body


def test_sort_oldest_and_invalid_fallback(tmp_path):
    client = make_client(tmp_path)
    create_post(client, title="첫번째", content="1")
    create_post(client, title="두번째", content="2")

    oldest = client.get("/posts?sort=oldest").data.decode("utf-8")
    invalid = client.get("/posts?sort=not-valid").data.decode("utf-8")

    assert oldest.index("첫번째") < oldest.index("두번째")
    assert invalid.index("두번째") < invalid.index("첫번째")


def test_sort_title_asc_orders_korean_titles(tmp_path):
    client = make_client(tmp_path)
    create_post(client, title="다", content="3")
    create_post(client, title="가", content="1")
    create_post(client, title="나", content="2")

    body = client.get("/posts?sort=title_asc").data.decode("utf-8")

    assert body.index("가") < body.index("나") < body.index("다")


def test_sort_is_preserved_with_search_and_pagination_links(tmp_path):
    client = make_client(tmp_path)
    create_many_search_posts(client, 25, keyword="키워드")

    page1 = client.get("/posts?q=키워드&sort=oldest&page=1").data.decode("utf-8")

    assert "1 / 3" in page1
    assert 'href="/posts?page=2&amp;q=%ED%82%A4%EC%9B%8C%EB%93%9C&amp;sort=oldest"' in page1
    assert 'href="/posts?page=3&amp;q=%ED%82%A4%EC%9B%8C%EB%93%9C&amp;sort=oldest"' in page1


def test_create_and_detail_render(tmp_path):
    client = make_client(tmp_path)

    create_response = create_post(client, title="테스트 제목", content="테스트 내용")
    assert create_response.status_code == 302

    detail_url = create_response.headers["Location"]
    detail_response = client.get(detail_url)
    body = detail_response.data.decode("utf-8")

    assert detail_response.status_code == 200
    assert "테스트 제목" in body
    assert "테스트 내용" in body
    assert "[수정]" in body
    assert "[삭제]" in body
    assert "정말 삭제할까요?" in body


def test_edit_reuses_form_and_updates_post(tmp_path):
    client = make_client(tmp_path)

    create_response = create_post(client, title="원래 제목", content="원래 내용")
    detail_url = create_response.headers["Location"]

    detail_response = client.get(detail_url)
    assert detail_response.status_code == 200

    post_id = Path(detail_url).name

    edit_get = client.get(f"/posts/{post_id}/edit")
    assert edit_get.status_code == 200
    assert "글 수정" in edit_get.data.decode("utf-8")

    edit_post = client.post(
        f"/posts/{post_id}/edit",
        data={"title": "수정 제목", "content": "수정 내용"},
        follow_redirects=True,
    )
    body = edit_post.data.decode("utf-8")

    assert edit_post.status_code == 200
    assert "수정 제목" in body
    assert "수정 내용" in body


def test_delete_post(tmp_path):
    client = make_client(tmp_path)

    create_response = create_post(client, title="삭제 대상", content="삭제할 내용")
    post_id = Path(create_response.headers["Location"]).name

    delete_response = client.post(f"/posts/{post_id}/delete", follow_redirects=True)
    body = delete_response.data.decode("utf-8")

    assert delete_response.status_code == 200
    assert "삭제 대상" not in body


def test_missing_post_returns_404(tmp_path):
    client = make_client(tmp_path)

    assert client.get("/posts/9999").status_code == 404
    assert client.get("/posts/9999/edit").status_code == 404
    assert client.post("/posts/9999/edit", data={"title": "x", "content": "y"}).status_code == 404
    assert client.post("/posts/9999/delete").status_code == 404
