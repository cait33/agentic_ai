"""Persistent work items (Session 2 dry run): create, list, mark done, delete.

Schema: db/migrations/001_work_items.sql (idempotent).
Apply it explicitly with:   python -m src.app.work_items --migrate
Tests call ensure_schema() themselves before using the API.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg
from fastapi import APIRouter, HTTPException, Response, status
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from src.app.settings import get_settings

MIGRATION = Path(__file__).resolve().parents[2] / "db" / "migrations" / "001_work_items.sql"

router = APIRouter(prefix="/work-items", tags=["work-items"])


class WorkItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)


class WorkItem(BaseModel):
    id: int
    title: str
    description: str
    done: bool
    created_at: datetime
    done_at: datetime | None = None


# --------------------------------------------------------------------------- #
# Repository
# --------------------------------------------------------------------------- #
def _connect() -> psycopg.Connection:
    return psycopg.connect(get_settings().database_url, connect_timeout=3, row_factory=dict_row)


def ensure_schema() -> None:
    with _connect() as conn:
        conn.execute(MIGRATION.read_text(encoding="utf-8"))


def create_item(data: WorkItemCreate) -> dict[str, Any]:
    with _connect() as conn:
        return conn.execute(
            "INSERT INTO work_items (title, description) VALUES (%s, %s) RETURNING *",
            (data.title.strip(), data.description),
        ).fetchone()


def list_items() -> list[dict[str, Any]]:
    with _connect() as conn:
        return conn.execute("SELECT * FROM work_items ORDER BY id").fetchall()


def mark_done(item_id: int) -> dict[str, Any] | None:
    with _connect() as conn:
        return conn.execute(
            "UPDATE work_items SET done = TRUE, done_at = COALESCE(done_at, now()) WHERE id = %s RETURNING *",
            (item_id,),
        ).fetchone()


def delete_item(item_id: int) -> bool:
    with _connect() as conn:
        return conn.execute("DELETE FROM work_items WHERE id = %s", (item_id,)).rowcount == 1


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
def _db_call(fn, *args):
    try:
        return fn(*args)
    except psycopg.OperationalError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc


@router.post("", response_model=WorkItem, status_code=status.HTTP_201_CREATED)
def create_work_item(body: WorkItemCreate) -> dict[str, Any]:
    if not body.title.strip():
        raise HTTPException(status_code=422, detail="title must not be blank")
    return _db_call(create_item, body)


@router.get("", response_model=list[WorkItem])
def list_work_items() -> list[dict[str, Any]]:
    return _db_call(list_items)


@router.patch("/{item_id}/done", response_model=WorkItem)
def complete_work_item(item_id: int) -> dict[str, Any]:
    row = _db_call(mark_done, item_id)
    if row is None:
        raise HTTPException(status_code=404, detail="work item not found")
    return row


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_item(item_id: int) -> Response:
    if not _db_call(delete_item, item_id):
        raise HTTPException(status_code=404, detail="work item not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate", action="store_true", help="Apply the work_items schema")
    if parser.parse_args().migrate:
        ensure_schema()
        print("work_items schema applied")
