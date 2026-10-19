"""API + persistence tests for work items against a real PostgreSQL.

Locally: docker compose up -d db  (tests are skipped if the DB is not reachable).
In CI the course workflow provides PostgreSQL, so these tests always run there.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest
from fastapi.testclient import TestClient

from src.app.main import app
from src.app.settings import get_settings
from src.app.work_items import ensure_schema


def _db_available() -> bool:
    try:
        with psycopg.connect(get_settings().database_url, connect_timeout=2):
            return True
    except psycopg.OperationalError:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL not reachable")


@pytest.fixture(scope="module")
def client():
    ensure_schema()  # tests initialise their own schema before calling the API
    return TestClient(app)


@pytest.fixture
def title():
    return f"test-item-{uuid.uuid4()}"


def test_create_and_list_persists_in_postgres(client, title) -> None:
    created = client.post("/work-items", json={"title": title, "description": "dry run"})
    assert created.status_code == 201
    body = created.json()
    assert body["title"] == title
    assert body["done"] is False

    # Read straight from the database to prove persistence.
    with psycopg.connect(get_settings().database_url) as conn:
        row = conn.execute("SELECT title FROM work_items WHERE id = %s", (body["id"],)).fetchone()
    assert row[0] == title

    listed = client.get("/work-items")
    assert listed.status_code == 200
    assert any(item["id"] == body["id"] for item in listed.json())
    client.delete(f"/work-items/{body['id']}")


def test_mark_done(client, title) -> None:
    item_id = client.post("/work-items", json={"title": title}).json()["id"]

    done = client.patch(f"/work-items/{item_id}/done")
    assert done.status_code == 200
    assert done.json()["done"] is True
    assert done.json()["done_at"] is not None
    client.delete(f"/work-items/{item_id}")


def test_delete(client, title) -> None:
    item_id = client.post("/work-items", json={"title": title}).json()["id"]

    assert client.delete(f"/work-items/{item_id}").status_code == 204
    assert all(item["id"] != item_id for item in client.get("/work-items").json())


def test_unknown_item_returns_404(client) -> None:
    assert client.patch("/work-items/999999999/done").status_code == 404
    assert client.delete("/work-items/999999999").status_code == 404


@pytest.mark.parametrize("payload", [{"title": ""}, {"title": "   "}, {}])
def test_invalid_title_is_rejected(client, payload) -> None:
    assert client.post("/work-items", json=payload).status_code == 422


def test_schema_migration_is_repeatable() -> None:
    ensure_schema()
    ensure_schema()
