"""狼人杀游戏路由：HTTP + WebSocket（统一 prefix /api/games/werewolf）

WS 协议与对局推送见 spec §5.4；房间运行时状态在内存（RoomManager），
仅对局结算落库（record.py）。
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from app.routes.auth import get_current_user_id
from app.schemas.werewolf import CreateRoomRequest, KickRequest, UpdateConfigRequest
from app.services.auth_service import get_auth_service
from app.services.werewolf.boards import PRESET_BOARDS, GameSettings, validate_board
from app.services.werewolf.engine import EngineError
from app.services.werewolf.manager import RoomManager
from app.services.werewolf.record import save_game_record
from app.services.werewolf.room import GameRoom

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/games/werewolf", tags=["werewolf"])
manager = RoomManager()   # 本模块单例；main.py lifespan 启动 run() 任务

SETTINGS_META = {
    "speech_seconds": {"label": "发言时长(秒)", "options": [30, 60, 90, 120]},
    "witch_self_rescue": {"label": "女巫自救", "options": [
        {"value": "never", "label": "不可自救"},
        {"value": "first_night", "label": "仅首夜可自救"},
        {"value": "always", "label": "随时可自救"}]},
    "witch_guard_conflict": {"label": "奶穿规则(守+救同夜死亡)",
                             "options": [True, False]},
}


# ---------- 辅助 ----------
def _get_room_or_404(room_id: str) -> GameRoom:
    room = manager.get(str(room_id))
    if room is None:
        raise HTTPException(status_code=404, detail="房间不存在或已解散")
    return room


def _resolve_board(payload: CreateRoomRequest) -> dict:
    if payload.board_id:
        board = next((b for b in PRESET_BOARDS if b["id"] == payload.board_id), None)
        if board is None:
            raise HTTPException(status_code=422, detail="未知板子")
        return board
    if payload.custom_roles:
        errors, _ = validate_board(payload.custom_roles)
        if errors:
            raise HTTPException(status_code=422, detail="；".join(errors))
        total = sum(payload.custom_roles.values())
        return {"id": "custom", "name": payload.board_name or "自定义局",
                "player_count": total, "roles": payload.custom_roles}
    raise HTTPException(status_code=422, detail="必须选择预置板子或自定义角色")


def _build_settings(speech: int, self_rescue: str, conflict: bool) -> GameSettings:
    return GameSettings(speech_seconds=speech, witch_self_rescue=self_rescue,
                        witch_guard_conflict=conflict)


def _nickname_of(user_id: str) -> str:
    """用昵称展示优于内部 ID（AGENTS.md：内部 ID 不展示在前端）"""
    try:
        from app.config.database import get_pooled_db_connection, release_db_connection
        conn = get_pooled_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT username FROM users WHERE user_id = %s",
                            (str(user_id),))
                row = cur.fetchone()
                return row[0] if row else f"玩家{user_id}"
        finally:
            release_db_connection(conn)
    except Exception:  # noqa: BLE001  昵称查询失败时兜底，不阻断建房/加入
        return f"玩家{user_id}"


async def _pump(room: GameRoom) -> None:
    """结算推送与落库（事件/私发由 room._pump 同步回调完成）"""
    if room.engine is None:
        return
    if room.engine.finished() and room.status == "RESULT" and not room.record_saved:
        room.record_saved = True
        try:
            save_game_record(room.build_record_summary())
        except Exception:
            logger.exception("[werewolf] 落库失败 room=%s", room.room_id)
        await room.on_broadcast({
            "type": "game_over",
            "winner": room.engine.winner(),
            "reveal": room.engine.reveal(),
        })


async def _maybe_close_room(room: GameRoom) -> None:
    if not room.members:
        manager.remove(room.room_id)


# ---------- HTTP ----------
@router.get("/boards")
async def get_boards(user_id: str = Depends(get_current_user_id)):
    return {"boards": PRESET_BOARDS, "presets": SETTINGS_META}


@router.post("/rooms")
async def create_room(payload: CreateRoomRequest,
                      user_id: str = Depends(get_current_user_id)):
    board = _resolve_board(payload)
    settings = _build_settings(payload.speech_seconds, payload.witch_self_rescue,
                               payload.witch_guard_conflict)
    room = manager.create_room(int(user_id), _nickname_of(user_id), board, settings)
    room.on_broadcast = _make_broadcast(room)
    room.on_send = _make_sender(room)
    room.on_finished = _make_finished(room)
    return {"room_id": room.room_id}


def _make_finished(room: GameRoom):
    """对局结束钩子：结算落库 + 广播 game_over（在管理循环的同步上下文触发）"""
    def _finished() -> None:
        if room.record_saved:
            return
        room.record_saved = True
        async def _finish_job():
            try:
                save_game_record(room.build_record_summary())
            except Exception:
                logger.exception("[werewolf] 落库失败 room=%s", room.room_id)
            await room.on_broadcast({
                "type": "game_over",
                "winner": room.engine.winner(),
                "reveal": room.engine.reveal(),
            })
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_finish_job())
        except RuntimeError:
            # 无事件循环（单元测试）：同步记录回调
            room.on_broadcast({"type": "game_over",
                               "winner": room.engine.winner(),
                               "reveal": room.engine.reveal()})
    return _finished


def _make_broadcast(room: GameRoom):
    def _broadcast(payload: dict) -> None:
        for uid in list(room._sockets):
            _dispatch(room, uid, payload)
    return _broadcast


def _make_sender(room: GameRoom):
    def _send(uid: int, payload: dict) -> None:
        _dispatch(room, uid, payload)
    return _send


def _dispatch(room: GameRoom, uid: int, payload: dict) -> None:
    """在事件循环内异步投递给目标用户的 WebSocket"""
    ws = room._sockets.get(uid)
    if ws is None:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    async def _send():
        try:
            await ws.send_text(json.dumps(payload, ensure_ascii=False))
        except Exception:  # noqa: BLE001  单连接推送失败不阻断广播
            logger.warning("[werewolf] 推送失败 room=%s user=%s", room.room_id, uid)
    loop.create_task(_send())


@router.post("/rooms/{room_id}/join")
async def join_room(room_id: str, user_id: str = Depends(get_current_user_id)):
    room = _get_room_or_404(room_id)
    try:
        room.add_member(int(user_id), _nickname_of(user_id))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"ok": True}


@router.post("/rooms/{room_id}/leave")
async def leave_room(room_id: str, user_id: str = Depends(get_current_user_id)):
    room = _get_room_or_404(room_id)
    room.remove_member(int(user_id))
    await _maybe_close_room(room)
    return {"ok": True}


@router.post("/rooms/{room_id}/kick")
async def kick_room(room_id: str, payload: KickRequest,
                    user_id: str = Depends(get_current_user_id)):
    room = _get_room_or_404(room_id)
    try:
        room.kick(int(payload.user_id), int(user_id))
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {"ok": True}


@router.post("/rooms/{room_id}/config")
async def update_config(room_id: str, payload: UpdateConfigRequest,
                        user_id: str = Depends(get_current_user_id)):
    room = _get_room_or_404(room_id)
    board = None
    if payload.board_id:
        board = next((b for b in PRESET_BOARDS if b["id"] == payload.board_id), None)
        if board is None:
            raise HTTPException(status_code=422, detail="未知板子")
    elif payload.custom_roles:
        errors, _ = validate_board(payload.custom_roles)
        if errors:
            raise HTTPException(status_code=422, detail="；".join(errors))
        board = {"id": "custom", "name": payload.board_name or "自定义局",
                 "player_count": sum(payload.custom_roles.values()),
                 "roles": payload.custom_roles}
    settings = GameSettings(
        speech_seconds=payload.speech_seconds or room.settings.speech_seconds,
        witch_self_rescue=payload.witch_self_rescue or room.settings.witch_self_rescue,
        witch_guard_conflict=(payload.witch_guard_conflict
                              if payload.witch_guard_conflict is not None
                              else room.settings.witch_guard_conflict),
    )
    try:
        room.update_config(board, settings, int(user_id))
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {"ok": True}


@router.post("/rooms/{room_id}/start")
async def start_room(room_id: str, user_id: str = Depends(get_current_user_id)):
    room = _get_room_or_404(room_id)
    try:
        room.start(int(user_id), now=time.time())
    except ValueError as e:
        msg = str(e)
        raise HTTPException(status_code=400 if ("至少" in msg or "人数" in msg) else 403,
                            detail=msg)
    await _pump(room)
    return {"ok": True}


@router.post("/rooms/{room_id}/replay")
async def replay_room(room_id: str, user_id: str = Depends(get_current_user_id)):
    room = _get_room_or_404(room_id)
    try:
        room.reset_for_replay(int(user_id), now=time.time())
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    await _pump(room)
    return {"ok": True}


@router.post("/rooms/{room_id}/dismiss")
async def dismiss_room(room_id: str, user_id: str = Depends(get_current_user_id)):
    room = _get_room_or_404(room_id)
    if int(user_id) != room.host_id:
        raise HTTPException(status_code=403, detail="只有房主可以解散房间")
    manager.remove(room.room_id)
    room.on_broadcast({"type": "room_closed", "reason": "房主解散了房间"})
    return {"ok": True}


@router.get("/rooms/{room_id}")
async def room_snapshot(room_id: str, user_id: str = Depends(get_current_user_id)):
    room = _get_room_or_404(room_id)
    return room.full_view(int(user_id))


# ---------- WebSocket ----------
def _verify_ws_token(token: str) -> str:
    """WS 认证：token 查询参数（小程序 Taro 全局 socket 无法带 header，沿用 openclaw_ws 先例）"""
    try:
        token_data = get_auth_service().verify_token_data(token)
        return token_data.user_id
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


async def room_ws(websocket: WebSocket) -> None:
    # 以纯 Starlette WebSocketRoute 挂载（见 main.py），参数从 scope 自取
    scope = websocket.scope
    room_id = scope.get("path_params", {}).get("room_id", "")
    from urllib.parse import parse_qs
    token = parse_qs(scope.get("query_string", b"").decode()).get("token", [""])[0]
    try:
        user_id = int(_verify_ws_token(token))
    except HTTPException:
        await websocket.close(code=4401)
        return
    room = manager.get(str(room_id))
    if room is None or user_id not in room.members:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    room.mark_connected(user_id, websocket)
    logger.info("[werewolf] WS 接入 room=%s user=%s", room_id, user_id)
    try:
        await _safe_send(websocket, {"type": "hello", "state": room.full_view(user_id)})
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await _safe_send(websocket, {"type": "error", "code": "BAD_JSON",
                                             "message": "消息格式错误"})
                continue
            if data.get("type") == "ping":
                await _safe_send(websocket, {"type": "pong"})
                continue
            if data.get("type") == "sync":
                await _safe_send(websocket, {"type": "state",
                                             "state": room.full_view(user_id)})
                continue
            try:
                room.on_message(user_id, data)
            except EngineError as e:
                await _safe_send(websocket, {"type": "error", "code": e.code,
                                             "message": e.message})
    except (WebSocketDisconnect, RuntimeError):
        logger.info("[werewolf] WS 断开 room=%s user=%s", room_id, user_id)
    except Exception:
        logger.exception("[werewolf] WS 异常断开 room=%s user=%s", room_id, user_id)
    finally:
        room.mark_disconnected(user_id, time.time())
        m = room.members.get(user_id)
        room.on_broadcast({"type": "event",
                           "text": f"{(m.nickname if m else user_id)} 与服务器断开连接"})


async def _safe_send(websocket: WebSocket, payload: dict) -> None:
    """单连接发送；连接已关闭等异常静默（广播由 _dispatch 各自容错）"""
    try:
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001  对端已断开，发送失败不影响主流程
        logger.debug("[werewolf] WS 发送失败: %s", e)
