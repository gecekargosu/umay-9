"""Tests for UMAY Post-it system."""
import os
import sys
import time
import uuid

import pytest

# Ensure project root is on path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.postit_store import (
    create_postit,
    get_postit,
    list_postits,
    update_postit,
    delete_postit,
    hide_postit,
    show_postit,
    toggle_pin,
    save_position,
    save_size,
    search_postits,
    get_stats,
    init_db,
)


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_postits.db"
    monkeypatch.setattr("core.postit_store.DB_PATH", test_db)
    monkeypatch.setattr("core.postit_store._local", type("Local", (), {"conn": None})())
    init_db()
    yield


class TestCreatePostit:
    def test_create_basic(self):
        postit = create_postit(title="Test", content="Hello world")
        assert postit is not None
        assert postit["title"] == "Test"
        assert postit["content"] == "Hello world"
        assert postit["id"] is not None
        assert postit["visible"] == 1
        assert postit["pinned"] == 1

    def test_create_with_color(self):
        postit = create_postit(title="Color", content="Red note", color="#FF0000")
        assert postit["color"] == "#FF0000"

    def test_create_with_position(self):
        postit = create_postit(title="Pos", content="Moved", x=500, y=300)
        assert postit["x"] == 500
        assert postit["y"] == 300

    def test_create_with_source(self):
        postit = create_postit(
            title="Source", content="From Chrome",
            source_app="Chrome", source_url="https://example.com"
        )
        assert postit["source_app"] == "Chrome"
        assert postit["source_url"] == "https://example.com"

    def test_create_empty_content(self):
        postit = create_postit(content="")
        assert postit["content"] == ""


class TestGetPostit:
    def test_get_existing(self):
        created = create_postit(title="Get me", content="Exists")
        fetched = get_postit(created["id"])
        assert fetched is not None
        assert fetched["title"] == "Get me"

    def test_get_nonexistent(self):
        result = get_postit("nonexistent-id")
        assert result is None


class TestListPostits:
    def test_list_empty(self):
        postits = list_postits()
        assert postits == []

    def test_list_multiple(self):
        create_postit(title="A", content="1")
        create_postit(title="B", content="2")
        create_postit(title="C", content="3")
        postits = list_postits()
        assert len(postits) == 3

    def test_list_visible_only(self):
        p1 = create_postit(title="Visible", content="1")
        p2 = create_postit(title="Hidden", content="2")
        hide_postit(p2["id"])
        visible = list_postits(visible_only=True)
        assert len(visible) == 1
        assert visible[0]["title"] == "Visible"


class TestUpdatePostit:
    def test_update_title(self):
        postit = create_postit(title="Old", content="Content")
        updated = update_postit(postit["id"], title="New")
        assert updated["title"] == "New"
        assert updated["content"] == "Content"

    def test_update_content(self):
        postit = create_postit(title="Title", content="Old content")
        updated = update_postit(postit["id"], content="New content")
        assert updated["content"] == "New content"

    def test_update_color(self):
        postit = create_postit(title="C", content="X")
        updated = update_postit(postit["id"], color="#00FF00")
        assert updated["color"] == "#00FF00"

    def test_update_nonexistent(self):
        result = update_postit("bad-id", title="X")
        assert result is None

    def test_updated_at_changes(self):
        postit = create_postit(title="T", content="C")
        old_time = postit["updated_at"]
        time.sleep(0.01)
        updated = update_postit(postit["id"], title="T2")
        assert updated["updated_at"] >= old_time


class TestDeletePostit:
    def test_delete_existing(self):
        postit = create_postit(title="Delete me", content="Bye")
        deleted = delete_postit(postit["id"])
        assert deleted is True
        assert get_postit(postit["id"]) is None

    def test_delete_nonexistent(self):
        deleted = delete_postit("nonexistent")
        assert deleted is False


class TestHideShow:
    def test_hide(self):
        postit = create_postit(title="H", content="X")
        hidden = hide_postit(postit["id"])
        assert hidden["visible"] == 0
        # Should not appear in visible-only list
        visible = list_postits(visible_only=True)
        assert all(p["id"] != postit["id"] for p in visible)

    def test_show(self):
        postit = create_postit(title="S", content="X")
        hide_postit(postit["id"])
        shown = show_postit(postit["id"])
        assert shown["visible"] == 1


class TestPin:
    def test_toggle_pin(self):
        postit = create_postit(title="P", content="X")
        assert postit["pinned"] == 1
        unpinned = toggle_pin(postit["id"])
        assert unpinned["pinned"] == 0
        repinned = toggle_pin(postit["id"])
        assert repinned["pinned"] == 1


class TestPosition:
    def test_save_position(self):
        postit = create_postit(title="Move", content="X")
        moved = save_position(postit["id"], x=999, y=888)
        assert moved["x"] == 999
        assert moved["y"] == 888

    def test_save_size(self):
        postit = create_postit(title="Resize", content="X")
        resized = save_size(postit["id"], width=500, height=400)
        assert resized["width"] == 500
        assert resized["height"] == 400


class TestSearch:
    def test_search_by_title(self):
        create_postit(title="Python学习笔记", content="Some content")
        create_postit(title="Meeting notes", content="Other content")
        results = search_postits("Python")
        assert len(results) == 1
        assert "Python" in results[0]["title"]

    def test_search_by_content(self):
        create_postit(title="Note", content="Important deadline is Friday")
        results = search_postits("deadline")
        assert len(results) == 1

    def test_search_no_results(self):
        create_postit(title="A", content="B")
        results = search_postits("nonexistent")
        assert len(results) == 0


class TestStats:
    def test_stats_empty(self):
        stats = get_stats()
        assert stats["total"] == 0
        assert stats["visible"] == 0
        assert stats["pinned"] == 0

    def test_stats_with_data(self):
        p1 = create_postit(title="A", content="1")
        p2 = create_postit(title="B", content="2")
        hide_postit(p2["id"])
        stats = get_stats()
        assert stats["total"] == 2
        assert stats["visible"] == 1


class TestMultiplePostits:
    def test_independent_postits(self):
        """Multiple Post-its should be independent."""
        posts = []
        for i in range(5):
            p = create_postit(title=f"Note {i}", content=f"Content {i}")
            posts.append(p)

        # All should exist
        for p in posts:
            assert get_postit(p["id"]) is not None

        # Delete one, others should remain
        delete_postit(posts[0]["id"])
        assert get_postit(posts[0]["id"]) is None
        for p in posts[1:]:
            assert get_postit(p["id"]) is not None

    def test_position_independence(self):
        """Each Post-it should have its own position."""
        p1 = create_postit(title="A", content="1", x=100, y=100)
        p2 = create_postit(title="B", content="2", x=500, y=500)
        save_position(p1["id"], x=200, y=200)
        refreshed1 = get_postit(p1["id"])
        refreshed2 = get_postit(p2["id"])
        assert refreshed1["x"] == 200
        assert refreshed2["x"] == 500


class TestPersistence:
    def test_data_survives_reconnect(self):
        """Data should persist across database connections."""
        postit = create_postit(title="Persist", content="This should last")
        # Force new connection
        import core.postit_store as store
        store._local.conn = None
        fetched = get_postit(postit["id"])
        assert fetched is not None
        assert fetched["title"] == "Persist"


class TestAPI:
    """Test the Flask API endpoints."""

    @pytest.fixture
    def client(self):
        from ui.panel_server import app
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    def test_list_postits(self, client):
        resp = client.get("/api/postits")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "postits" in data
        assert "stats" in data

    def test_create_postit(self, client):
        resp = client.post("/api/postits", json={
            "title": "API Test", "content": "Created via API"
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["postit"]["title"] == "API Test"

    def test_get_postit(self, client):
        create_resp = client.post("/api/postits", json={"title": "T", "content": "C"})
        postit_id = create_resp.get_json()["postit"]["id"]
        resp = client.get(f"/api/postits/{postit_id}")
        assert resp.status_code == 200
        assert resp.get_json()["postit"]["title"] == "T"

    def test_update_postit(self, client):
        create_resp = client.post("/api/postits", json={"title": "Old", "content": "C"})
        postit_id = create_resp.get_json()["postit"]["id"]
        resp = client.put(f"/api/postits/{postit_id}", json={"title": "New"})
        assert resp.status_code == 200
        assert resp.get_json()["postit"]["title"] == "New"

    def test_delete_postit(self, client):
        create_resp = client.post("/api/postits", json={"title": "Del", "content": "C"})
        postit_id = create_resp.get_json()["postit"]["id"]
        resp = client.delete(f"/api/postits/{postit_id}")
        assert resp.status_code == 200
        assert resp.get_json()["deleted"] is True

    def test_hide_show(self, client):
        create_resp = client.post("/api/postits", json={"title": "H", "content": "C"})
        postit_id = create_resp.get_json()["postit"]["id"]
        resp = client.post(f"/api/postits/{postit_id}/hide")
        assert resp.status_code == 200
        assert resp.get_json()["postit"]["visible"] == 0
        resp = client.post(f"/api/postits/{postit_id}/show")
        assert resp.status_code == 200
        assert resp.get_json()["postit"]["visible"] == 1

    def test_quick_create(self, client):
        resp = client.post("/api/postits/quick", json={
            "content": "Quick note from clipboard"
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert "Quick note" in data["postit"]["title"]

    def test_quick_create_empty(self, client):
        resp = client.post("/api/postits/quick", json={"content": ""})
        assert resp.status_code == 400

    def test_search(self, client):
        client.post("/api/postits", json={"title": "Python Note", "content": "Learn Python"})
        resp = client.get("/api/postits/search?q=Python")
        assert resp.status_code == 200
        assert len(resp.get_json()["postits"]) == 1
