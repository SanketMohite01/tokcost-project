import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def upsert_google_user(google_sub, email, bootstrap_role="user"):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE google_sub = %s", (google_sub,))
            existing = cur.fetchone()
            if existing:
                return existing
            cur.execute(
                """
                INSERT INTO users (google_sub, email, role)
                VALUES (%s, %s, %s)
                RETURNING *
                """,
                (google_sub, email, bootstrap_role),
            )
            return cur.fetchone()


def get_user_by_id(user_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cur.fetchone()


def list_users(limit=200):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, email, role, created_at
                FROM users
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def update_user_role(user_id, role):
    if role not in ("user", "admin"):
        raise ValueError("Invalid role")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE users SET role = %s
                WHERE id = %s
                RETURNING id, email, role, created_at
                """,
                (role, user_id),
            )
            return cur.fetchone()


def admin_stats():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM users")
            users = cur.fetchone()["c"]
            cur.execute(
                "SELECT COUNT(*) AS c FROM sessions WHERE deleted_at IS NULL"
            )
            active_sessions = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) AS c FROM sessions WHERE deleted_at IS NOT NULL")
            soft_deleted = cur.fetchone()["c"]
            return {
                "users": users,
                "active_sessions": active_sessions,
                "soft_deleted_sessions": soft_deleted,
            }


def save_session(
    owner_id,
    prompt_text,
    compressed_prompt=None,
    recommended_platform=None,
    summary=None,
    title=None,
    files=None,
    results=None,
    meta=None,
):
    files = files or []
    results = results or []
    title = title or prompt_text[:60]

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO sessions
                    (owner_id, title, prompt_text, compressed_prompt,
                     recommended_platform, summary, meta)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (owner_id, title, prompt_text, compressed_prompt,
                 recommended_platform, summary,
                 Jsonb(meta) if meta is not None else None),
            )
            session_id = cur.fetchone()["id"]

            for f in files:
                cur.execute(
                    """
                    INSERT INTO files
                        (session_id, filename, file_type, size_bytes, tokens)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (session_id, f["filename"], f["file_type"],
                     f.get("size_bytes"), Jsonb(f.get("tokens"))),
                )

            for r in results:
                cur.execute(
                    """
                    INSERT INTO results
                        (session_id, platform, input_tokens,
                         est_output_tokens, est_cost_usd)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (session_id, r["platform"], r["input_tokens"],
                     r.get("est_output_tokens"), r.get("est_cost_usd")),
                )

    return str(session_id)


def list_sessions(owner_id, limit=50):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, recommended_platform, created_at, pinned_at
                FROM sessions
                WHERE owner_id = %s AND deleted_at IS NULL
                ORDER BY pinned_at DESC NULLS LAST, created_at DESC
                LIMIT %s
                """,
                (owner_id, limit),
            )
            return cur.fetchall()


def get_session(session_id, owner_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM sessions
                WHERE id = %s AND owner_id = %s AND deleted_at IS NULL
                """,
                (session_id, owner_id),
            )
            session = cur.fetchone()
            if session is None:
                return None

            cur.execute(
                "SELECT filename, file_type, size_bytes, tokens "
                "FROM files WHERE session_id = %s",
                (session_id,),
            )
            session["files"] = cur.fetchall()

            cur.execute(
                "SELECT platform, input_tokens, est_output_tokens, est_cost_usd "
                "FROM results WHERE session_id = %s ORDER BY platform",
                (session_id,),
            )
            session["results"] = cur.fetchall()
            return session


def update_session_title(session_id, owner_id, title):
    title = (title or "").strip()
    if not title:
        raise ValueError("Title cannot be empty")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sessions SET title = %s
                WHERE id = %s AND owner_id = %s AND deleted_at IS NULL
                RETURNING id, title, pinned_at
                """,
                (title[:120], session_id, owner_id),
            )
            return cur.fetchone()


def update_session_pinned(session_id, owner_id, pinned):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if pinned:
                cur.execute(
                    """
                    UPDATE sessions SET pinned_at = now()
                    WHERE id = %s AND owner_id = %s AND deleted_at IS NULL
                    RETURNING id, title, pinned_at
                    """,
                    (session_id, owner_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE sessions SET pinned_at = NULL
                    WHERE id = %s AND owner_id = %s AND deleted_at IS NULL
                    RETURNING id, title, pinned_at
                    """,
                    (session_id, owner_id),
                )
            return cur.fetchone()


def soft_delete_session(session_id, owner_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE sessions SET deleted_at = now()
                WHERE id = %s AND owner_id = %s AND deleted_at IS NULL
                RETURNING id
                """,
                (session_id, owner_id),
            )
            return cur.fetchone() is not None
