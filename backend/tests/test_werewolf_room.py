"""房间管理：加入/离开/满员/开始/断线托管/重连/落库汇总"""
import pytest

from app.services.werewolf.boards import PRESET_BOARDS, GameSettings
from app.services.werewolf.manager import RoomManager


@pytest.fixture()
def mgr():
    return RoomManager()


def board6():
    return next(b for b in PRESET_BOARDS if b["player_count"] == 6)


class Sink:
    """记录所有广播/私发的假连接层"""

    def __init__(self):
        self.broadcasts = []
        self.sends = []

    def on_broadcast(self, payload):
        self.broadcasts.append(payload)

    def on_send(self, user_id, payload):
        self.sends.append((user_id, payload))


def make_full_room(mgr, sink=None):
    room = mgr.create_room(1, "房主", board6(), GameSettings())
    if sink:
        room.on_broadcast = sink.on_broadcast
        room.on_send = sink.on_send
    for uid in range(2, 7):
        room.add_member(uid, f"玩家{uid}")
    return room


def test_create_and_join_capacity(mgr):
    room = make_full_room(mgr)
    with pytest.raises(ValueError):
        room.add_member(99, "多余人")  # 满员
    room.remove_member(3)
    room.add_member(99, "补位")  # 离开后可再进


def test_only_waiting_can_join(mgr):
    room = make_full_room(mgr)
    room.start(1, now=1000.0)
    with pytest.raises(ValueError):
        room.add_member(77, "迟到者")
    assert room.status == "PLAYING"


def test_host_only_start(mgr):
    room = make_full_room(mgr)
    with pytest.raises(ValueError):
        room.start(2, now=1000.0)  # 非房主


def test_start_deals_roles_and_sends_private(mgr):
    sink = Sink()
    room = make_full_room(mgr, sink)
    room.start(1, now=1000.0)
    kinds = [p["kind"] for _, p in sink.sends]
    assert "role" in kinds  # 每个成员收到身份私发


def test_disconnect_grace_then_escaped(mgr):
    room = make_full_room(mgr)
    room.start(1, now=1000.0)
    room.mark_disconnected(2, now=1000.0)
    room.tick(1000.0 + 30)
    assert not room.engine.players[1].escaped  # 30s 内保留
    room.tick(1000.0 + 61)
    assert room.engine.players[1].escaped      # 60s 后托管
    room.mark_connected(2, ws=None)
    assert room.engine.players[1].escaped      # 托管到结束（spec §5.6）


def test_room_message_routes_to_engine(mgr):
    room = make_full_room(mgr)
    room.start(1, now=1000.0)
    # 找到存活狼发刀
    wolf = [p for p in room.engine.players if p.role.value == "WEREWOLF" and p.alive][0]
    target = [p.seat for p in room.engine.players if p.alive and p.seat != wolf.seat][0]
    room.on_message(wolf.user_id, {"type": "act", "action": "werewolf_kill",
                                   "target": target})
    assert room.engine.night.wolf == target
    with pytest.raises(Exception):
        room.on_message(wolf.user_id, {"type": "act", "action": "werewolf_kill",
                                       "target": target})  # 重复行动被引擎拒绝


def test_record_summary_after_finish(mgr):
    room = make_full_room(mgr)
    room.start(1, now=1000.0)
    # 全员超时推进至终局（狼随机刀 → 最终分出胜负）
    t = 1000.0
    for _ in range(2000):
        if room.engine.finished():
            break
        t += 50
        room.tick(t)
    assert room.engine.finished()
    summary = room.build_record_summary()
    assert summary["player_count"] == 6 and summary["winner"] in ("VILLAGER", "WEREWOLF")
    assert len(summary["players"]) == 6
    assert all(p["role"] for p in summary["players"])


def test_replay_resets_engine(mgr):
    room = make_full_room(mgr)
    room.start(1, now=1000.0)
    t = 1000.0
    for _ in range(2000):
        if room.engine.finished():
            break
        t += 50
        room.tick(t)
    room.reset_for_replay(by_user_id=1, now=t)
    assert room.status == "PLAYING" and room.engine.day == 1 and not room.engine.finished()
    with pytest.raises(ValueError):
        room.reset_for_replay(by_user_id=2, now=t)  # 仅房主


def test_kick_host_only_waiting_only(mgr):
    room = make_full_room(mgr)
    room.kick(3, by_user_id=1)
    assert 3 not in room.members
    with pytest.raises(ValueError):
        room.kick(4, by_user_id=2)  # 非房主
    with pytest.raises(ValueError):
        room.kick(1, by_user_id=1)  # 不能踢自己


def test_full_view_contains_snapshot_and_connected(mgr):
    room = make_full_room(mgr)
    room.start(1, now=1000.0)
    room.mark_disconnected(2, now=1000.0)
    view = room.full_view(1)
    assert "snapshot" in view and view["status"] == "PLAYING"
    seat2 = next(p for p in view["snapshot"]["players"] if p["seat"] == 2)
    assert seat2["connected"] is False
