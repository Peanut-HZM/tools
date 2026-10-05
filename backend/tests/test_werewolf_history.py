"""引擎公开历史（对局过程回放数据）验收"""
from app.services.werewolf.engine import Phase
from app.services.werewolf.roles import Role
from tests.werewolf_helpers import DriveHelper, make_engine, seats_with_role

ROLES6 = {Role.WEREWOLF: 2, Role.SEER: 1, Role.WITCH: 1, Role.VILLAGER: 2}


def play_to_day_vote(seed=42):
    """夜1 狼刀 3 号 → 推进到白天（停在发言阶段，供测试逐个发言）"""
    eng = make_engine(ROLES6, seed=seed)
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, 1000.0)
    d = DriveHelper(eng)
    d.run_to(Phase.DAY_SPEECH)
    return eng, d


def test_public_history_contains_events_speeches_votes():
    eng, d = play_to_day_vote()
    # 白天发言一轮 + 投票放逐 2 号（play_to_day_vote 已停在发言阶段）
    # 依次发言（队列顺序提交；发言结束进入投票后停止）
    for seat in list(eng._speech_queue):
        if eng.phase != Phase.DAY_SPEECH:
            break
        eng.submit_speech(eng.players[seat - 1].user_id, f"{seat} 号发言", d.t)
    for p in eng.players:
        if not p.alive:
            continue
        if p.seat == 2:
            eng.submit_action(p.user_id, "vote", None, d.t)
        else:
            eng.submit_action(p.user_id, "vote", 2, d.t)
    # 遗言跳过到下一夜
    d.to_next_night()

    h = eng.public_history()
    # 事件：开局/天黑/天亮死讯/发言提示/放逐
    texts = [e["text"] for e in h["events"]]
    assert any("对局开始" in t for t in texts)
    assert any("3 号" in t and "死亡" in t for t in texts)
    assert any("2 号被投票放逐" in t for t in texts)
    # 发言：6 条（含死者之外全员）
    assert len(h["speeches"]) == 5
    assert h["speeches"][0]["seat"] == eng._speech_queue[0]
    # 票型历史：day1 放逐 2 号
    assert len(h["votes"]) == 1
    assert h["votes"][0]["day"] == 1
    assert h["votes"][0]["exiled"] == 2
    assert {"voter": 1, "target": 2} in h["votes"][0]["detail"]
    # 时间线：按发生顺序交错——发言必须出现在其对应天亮的死讯事件之后
    tl = h["timeline"]
    seqs = [e["seq"] for e in tl]
    assert seqs == sorted(seqs) and len(seqs) > 10
    kinds = {id(e): e["kind"] for e in tl}
    dawn_idx = next(i for i, e in enumerate(tl)
                    if e["kind"] == "event" and "死亡" in (e.get("text") or ""))
    first_speech_idx = next(i for i, e in enumerate(tl) if e["kind"] == "speech")
    assert first_speech_idx > dawn_idx, "发言应出现在天亮死讯之后（交错排序）"
    vote_idx = next(i for i, e in enumerate(tl) if e["kind"] == "vote")
    assert vote_idx > first_speech_idx, "投票应出现在发言之后"


def test_public_history_excludes_private_info():
    """公开历史不得包含任何私有信息（刀口指令/查验结果原文/女巫视角）"""
    eng, d = play_to_day_vote()
    d.to_next_night()
    h = eng.public_history()
    import json
    blob = json.dumps(h, ensure_ascii=False)
    for forbidden in ("werewolf_kill", "seer_check", "witch_save", "witch_poison",
                      "witch_victim", "seer_result", "mates"):
        assert forbidden not in blob, f"公开历史泄露私有字段: {forbidden}"


def test_vote_history_includes_pk_and_second_tie():
    eng = make_engine(ROLES6, seed=7)
    d = DriveHelper(eng)
    wolf = eng.players[seats_with_role(eng, Role.WEREWOLF)[0] - 1]
    eng.submit_action(wolf.user_id, "werewolf_kill", 3, 1000.0)
    d.run_to(Phase.DAY_VOTE)
    for p in eng.players:
        if not p.alive or p.seat == 3:
            continue
        if p.seat == 4:
            eng.submit_action(p.user_id, "vote", 1, d.t)
        elif p.seat == 5:
            eng.submit_action(p.user_id, "vote", 2, d.t)
        else:
            eng.submit_action(p.user_id, "vote", None, d.t)
    assert eng.phase == Phase.PK_SPEECH
    d.run_to(Phase.DAY_VOTE_PK)
    non_pk = [p for p in eng.players if p.alive and p.seat not in (1, 2)]
    for p, t in zip(non_pk, [1, 2, None]):
        eng.submit_action(p.user_id, "vote_pk", t, d.t)
    d.to_next_night()
    h = eng.public_history()
    assert len(h["votes"]) == 2
    assert h["votes"][0]["kind"] == "vote" and h["votes"][0]["exiled"] is None  # 平票未出
    assert h["votes"][1]["kind"] == "vote_pk" and h["votes"][1]["exiled"] is None
