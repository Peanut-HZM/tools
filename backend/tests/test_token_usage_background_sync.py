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


def test_order_users_for_round_prioritizes_pending_user():
    """字典序最后的 pending 用户不能被 sorted()[:max_users] 截断饿死。"""
    all_users = ["0196", "026a", "029d", "317e"]

    ordered = bg._order_users_for_round(all_users, {"317e"}, max_users=3)

    assert "317e" in ordered
    assert len(ordered) == 3
    assert ordered[0] == "317e"


def test_order_users_for_round_rotates_rest_users(monkeypatch):
    """名额不足时其余用户按轮转补位，长期每个用户都会被覆盖。"""
    from itertools import count

    monkeypatch.setattr(bg, "_discovery_rotation", count())
    all_users = ["u1", "u2", "u3", "u4"]

    rounds = [
        bg._order_users_for_round(all_users, set(), max_users=2)
        for _ in range(4)
    ]

    assert rounds[0] == ["u1", "u2"]
    assert rounds[1] == ["u2", "u3"]
    assert rounds[2] == ["u3", "u4"]
    assert rounds[3] == ["u4", "u1"]
    covered = {u for round_users in rounds for u in round_users}
    assert covered == set(all_users)


def test_order_users_for_round_edge_cases():
    assert bg._order_users_for_round([], set(), max_users=3) == []
    assert bg._order_users_for_round(["u1", "u2"], {"u1"}, max_users=0) == []
    # pending 占满全部名额
    assert bg._order_users_for_round(["u1", "u2"], {"u1", "u2"}, max_users=2) == [
        "u1",
        "u2",
    ]
    # rest 为空时只返回 pending
    assert bg._order_users_for_round(["u1"], {"u1"}, max_users=3) == ["u1"]
