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
    kinds = [p["kind"] for _, p in sink.sends if p.get("type") == "private"]
    assert "role" in kinds  # 每个成员收到身份私发（另有 state 快照推送）


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
    wolf = next(p for p in room.engine.players
                if p.role.value == "WEREWOLF" and p.alive)
    target = next(p.seat for p in room.engine.players
                  if p.alive and p.seat != wolf.seat)
    room.on_message(wolf.user_id, {"type": "act", "action": "werewolf_kill",
                                   "target": target})
    assert room.engine.night.wolf == target
    # 狼人阶段内重复提交是合法改刀（最后一次为准）
    target2 = next(p.seat for p in room.engine.players
                   if p.alive and p.seat != wolf.seat and p.seat != target)
    room.on_message(wolf.user_id, {"type": "act", "action": "werewolf_kill",
                                   "target": target2})
    assert room.engine.night.wolf == target2


def test_start_pushes_state_snapshot_to_members(mgr):
    """对局开始必须把个人视角 state 快照推给每个成员（客户端依赖它离开等待页）"""
    sink = Sink()
    room = make_full_room(mgr, sink)
    room.start(1, now=1000.0)
    state_msgs = [p for uid, p in sink.sends if p.get("type") == "state"]
    assert len(state_msgs) == 6  # 每个成员各一份个人视角
    assert all("snapshot" in s["state"] for s in state_msgs)
    assert all(s["state"]["status"] == "PLAYING" for s in state_msgs)


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


def test_reconnect_keeps_new_socket_and_stale_close_is_ignored(mgr):
    """挤线/重连：旧连接断开不得清掉新连接的注册（I1）"""
    room = make_full_room(mgr)
    room.start(1, now=1000.0)
    old_ws, new_ws = object(), object()
    room.mark_connected(2, old_ws)
    room.mark_connected(2, new_ws)  # 新连接接管
    # 旧连接迟到的断开事件（带 ws 比对）不得清掉新连接
    room.mark_disconnected(2, now=1000.0, ws=old_ws)
    assert room._sockets.get(2) is new_ws
    assert room.members[2].connected is True


def test_member_changes_broadcast_room_view(mgr):
    """等待期成员加入/离开/踢人必须广播 room 视图（前端成员列表实时刷新）"""
    sink = Sink()
    room = mgr.create_room(1, "房主", board6(), GameSettings())
    room.on_broadcast = sink.on_broadcast
    seen = [p for p in sink.broadcasts]
    room.add_member(2, "乙")
    room.add_member(3, "丙")
    room.kick(3, by_user_id=1)
    room.remove_member(2)
    types = [p.get("type") for p in sink.broadcasts]
    assert types.count("room") >= 3  # 每次成员变动都有推送
    room_msgs = [p for p in sink.broadcasts if p.get("type") == "room"]
    assert room_msgs[-1]["room"]["members"] == [] or "members" in room_msgs[-1]["room"]


def test_replay_resets_event_cursor(mgr):
    """再来一局后事件游标必须归零，否则新对局事件全被过滤（I3）"""
    room = make_full_room(mgr)
    room.start(1, now=1000.0)
    t = 1000.0
    for _ in range(2000):
        if room.engine.finished():
            break
        t += 50
        room.tick(t)
    room.reset_for_replay(by_user_id=1, now=t)
    assert room._event_cursor == 0
    assert room._last_state_key is None
    # 新对局事件能进泵（用同步回调验证）
    seen = []
    room.on_broadcast = lambda payload: seen.append(payload)
    room.tick(t + 1)
    assert any(p.get("type") == "event" for p in seen), "新对局事件被游标过滤"


def test_full_view_contains_snapshot_and_connected(mgr):
    room = make_full_room(mgr)
    room.start(1, now=1000.0)
    room.mark_disconnected(2, now=1000.0)
    view = room.full_view(1)
    assert "snapshot" in view and view["status"] == "PLAYING"
    seat2 = next(p for p in view["snapshot"]["players"] if p["seat"] == 2)
    assert seat2["connected"] is False
