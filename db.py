"""Neon PostgreSQL storage for the single-user TXT reader."""
import os
import uuid
from contextlib import contextmanager

import psycopg

MAX_BYTES = 3 * 1024 * 1024


@contextmanager
def connection():
    url = os.getenv('DATABASE_URL')
    if not url:
        raise RuntimeError('Render DATABASE_URL 환경변수가 없습니다.')
    with psycopg.connect(url, connect_timeout=10) as conn:
        yield conn


def ensure_schema():
    with connection() as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id UUID PRIMARY KEY,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                reading_position DOUBLE PRECISION NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)


def list_books():
    with connection() as conn, conn.cursor() as cur:
        cur.execute('SELECT id::text, filename, updated_at FROM documents ORDER BY updated_at DESC')
        return cur.fetchall()


def get_book(book_id):
    with connection() as conn, conn.cursor() as cur:
        cur.execute('SELECT id::text, filename, content, reading_position FROM documents WHERE id = %s', (book_id,))
        return cur.fetchone()


def save_book(book_id, name, content):
    name = name.strip()
    if not name:
        raise ValueError('File Name을 입력하세요.')
    if len(content.encode('utf-8')) > MAX_BYTES:
        raise ValueError('TXT 내용은 최대 3MB까지 저장 가능합니다.')
    with connection() as conn, conn.cursor() as cur:
        if book_id:
            cur.execute('UPDATE documents SET filename=%s, content=%s, updated_at=now() WHERE id=%s',
                        (name, content, book_id))
            if cur.rowcount != 1:
                raise ValueError('수정할 문서를 찾을 수 없습니다.')
            return book_id
        new_id = str(uuid.uuid4())
        cur.execute('INSERT INTO documents(id, filename, content) VALUES (%s,%s,%s)',
                    (new_id, name, content))
        return new_id


def delete_book(book_id):
    with connection() as conn, conn.cursor() as cur:
        cur.execute('DELETE FROM documents WHERE id = %s', (book_id,))
        return cur.rowcount == 1
