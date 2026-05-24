"""Token Usage 后台同步服务单元测试。"""

from app.services import token_usage_background_sync as bg


def test_pending_user_registry_deduplicates_user_ids():
    bg.clear_pending_sync_users()

    bg.register_pending_sync_user("user-1")
    bg.register_pending_sync_user("user-1")
    bg.register_pending_sync_user("user-2")

    assert bg.get_pending_sync_users() == {"user-1", "user-2"}


def test_register_pending_sync_user_ignores_empty_and_system_users():
    bg.clear_pending_sync_users()

    bg.register_pending_sync_user("")
    bg.register_pending_sync_user(None)
    bg.register_pending_sync_user("system")
    bg.register_pending_sync_user("user-3")

    assert bg.get_pending_sync_users() == {"user-3"}


def test_run_background_sync_once_syncs_pending_user(monkeypatch):
    bg.clear_pending_sync_users()
    bg.register_pending_sync_user("user-1")

    events = []

    monkeypatch.setattr(bg, "_discover_token_usage_user_ids", lambda max_users: ["user-1"])
    monkeypatch.setattr(
        bg,
        "acquire_refresh_lock",
        lambda user_id, owner: {
            "acquired": True,
            "locked": False,
            "owner": owner,
            "ttl_seconds": 120,
        },
    )
    monkeypatch.setattr(
        bg,
        "release_refresh_lock",
        lambda user_id, owner: events.append(("release", user_id)),
    )
    monkeypatch.setattr(
        bg,
        "sync_token_usage",
        lambda user_id, days: {"total_records": 3, "errors": []},
    )
    monkeypatch.setattr(
        bg,
        "invalidate_user_query_cache",
        lambda user_id: events.append(("invalidate", user_id)),
    )

    result = bg.run_background_sync_once(days=90, max_users=50)

    assert result["synced_users"] == ["user-1"]
    assert result["failed_users"] == []
    assert ("invalidate", "user-1") in events
    assert ("release", "user-1") in events


def test_run_background_sync_once_skips_locked_user(monkeypatch):
    bg.clear_pending_sync_users()
    bg.register_pending_sync_user("user-locked")

    monkeypatch.setattr(
        bg,
        "_discover_token_usage_user_ids",
        lambda max_users: ["user-locked"],
    )
    monkeypatch.setattr(
        bg,
        "acquire_refresh_lock",
        lambda user_id, owner: {
            "acquired": False,
            "locked": True,
            "owner": "other",
            "ttl_seconds": 60,
        },
    )

    result = bg.run_background_sync_once(days=90, max_users=50)

    assert result["synced_users"] == []
    assert result["skipped_users"] == ["user-locked"]
