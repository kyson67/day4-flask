from pathlib import Path
import sqlite3

from flask import Flask, abort, g, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["DATABASE"] = str(Path(__file__).resolve().parent / "board.sqlite3")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exception: Exception | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    schema_path = Path(__file__).resolve().parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    db = get_db()
    db.executescript(schema_sql)
    db.commit()


def get_post_or_404(post_id: int) -> sqlite3.Row:
    post = get_db().execute(
        "SELECT id, title, content, created_at FROM posts WHERE id = ?",
        (post_id,),
    ).fetchone()
    if post is None:
        abort(404)
    return post


@app.get("/")
def home():
    return redirect(url_for("list_posts"))


@app.get("/posts")
def list_posts():
    per_page = 10
    raw_page = request.args.get("page", "1")
    q = request.args.get("q", "").strip()
    raw_sort = request.args.get("sort", "latest").strip().lower()

    sort_map = {
        "latest": "created_at DESC, id DESC",
        "oldest": "created_at ASC, id ASC",
        "title_asc": "title ASC, id ASC",
    }
    sort = raw_sort if raw_sort in sort_map else "latest"

    try:
        page = int(raw_page)
    except ValueError:
        page = 1

    if page < 1:
        page = 1

    db = get_db()

    where_clause = ""
    where_params: list[str] = []
    if q:
        where_clause = "WHERE title LIKE ? OR content LIKE ?"
        like_q = f"%{q}%"
        where_params = [like_q, like_q]

    total_count = db.execute(
        f"SELECT COUNT(*) FROM posts {where_clause}",
        where_params,
    ).fetchone()[0]
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page

    posts = db.execute(
        f"SELECT id, title, content, created_at FROM posts {where_clause} ORDER BY {sort_map[sort]} LIMIT ? OFFSET ?",
        (*where_params, per_page, offset),
    ).fetchall()

    return render_template(
        "posts/list.html",
        posts=posts,
        page=page,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
        prev_page=page - 1,
        next_page=page + 1,
        q=q,
        q_param=q or None,
        sort=sort,
        sort_param=sort if sort != "latest" else None,
    )


@app.get("/posts/new")
def new_post():
    return render_template(
        "posts/form.html",
        mode="create",
        post={"title": "", "content": ""},
        error=None,
    )


@app.post("/posts")
def create_post():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not title or not content:
        return (
            render_template(
                "posts/form.html",
                mode="create",
                post={"title": title, "content": content},
                error="제목과 내용을 입력해주세요.",
            ),
            400,
        )

    db = get_db()
    cursor = db.execute(
        "INSERT INTO posts (title, content) VALUES (?, ?)",
        (title, content),
    )
    db.commit()
    return redirect(url_for("post_detail", post_id=cursor.lastrowid))


@app.get("/posts/<int:post_id>")
def post_detail(post_id: int):
    post = get_post_or_404(post_id)
    return render_template("posts/detail.html", post=post)


@app.get("/posts/<int:post_id>/edit")
def edit_post(post_id: int):
    post = get_post_or_404(post_id)
    return render_template("posts/form.html", mode="edit", post=post, error=None)


@app.post("/posts/<int:post_id>/edit")
def update_post(post_id: int):
    post = get_post_or_404(post_id)
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not title or not content:
        return (
            render_template(
                "posts/form.html",
                mode="edit",
                post={"id": post_id, "title": title, "content": content},
                error="제목과 내용을 입력해주세요.",
            ),
            400,
        )

    db = get_db()
    db.execute(
        "UPDATE posts SET title = ?, content = ? WHERE id = ?",
        (title, content, post_id),
    )
    db.commit()
    return redirect(url_for("post_detail", post_id=post_id))


@app.post("/posts/<int:post_id>/delete")
def delete_post(post_id: int):
    get_post_or_404(post_id)
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    return redirect(url_for("list_posts"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True)
