import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def get_conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def save_session(
    owner_id,
    prompt_text,
    compressed_prompt=None,
    recommended_platform=None,
    summary=None,
    title=None,
    files=None,
    results=None,
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
                     recommended_platform, summary)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (owner_id, title, prompt_text, compressed_prompt,
                 recommended_platform, summary),
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
                SELECT id, title, recommended_platform, created_at
                FROM sessions
                WHERE owner_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (owner_id, limit),
            )
            return cur.fetchall()


def get_session(session_id, owner_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM sessions WHERE id = %s AND owner_id = %s",
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


def delete_session(session_id, owner_id):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM sessions WHERE id = %s AND owner_id = %s RETURNING id",
                (session_id, owner_id),
            )
            return cur.fetchone() is not None