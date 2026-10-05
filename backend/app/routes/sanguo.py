"""三国杀游戏路由：HTTP + WebSocket（prefix /api/games/sanguo）"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import (APIRouter, Depends, HTTPException, WebSocket,
                     WebSocketDisconnect)

from app.routes.auth import get_current_user_id
from app.services.auth_service import get_auth_service
from app.services.sanguo.engine import EngineError
from app.services.sanguo.manager import manager
from app.services.sanguo.record import save_game_record
from app.services.sanguo.record import get_record as query_record
from app.services.sanguo.record import list_records as query_records
from app.services.sanguo.heroes import HEROES
from app.services.sanguo.room import SanguoRoom

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/games/sanguo", tags=["sanguo"])


def _nickname_of(user_id: str) -> str:
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
    except Exception:  # noqa: BLE001  昵称查询失败时兜底
        return f"玩家{user_id}"


def _get_room_or_404(room_id: str) -> SanguoRoom:
    room = manager.get(str(room_id))
    if room is None:
        raise HTTPException(status_code=404, detail="房间不存在或已解散")
    return room


def _make_broadcast(room: SanguoRoom):
    def _broadcast(payload: dict) -> None:
        for uid in list(room._sockets):
            _dispatch(room, uid, payload)
    return _broadcast


def _make_sender(room: SanguoRoom):
    def _send(uid: int, payload: dict) -> None:
        _dispatch(room, uid, payload)
    return _send


def _dispatch(room: SanguoRoom, uid: int, payload: dict) -> None:
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
        except Exception as e:  # noqa: BLE001
            logger.warning("[sanguo] 推送失败 room=%s user=%s err=%s",
                           room.room_id, uid, e)
    loop.create_task(_send())


def _make_finished(room: SanguoRoom):
    def _finished() -> None:
        if room.record_saved:
            return
        room.record_saved = True

        async def _finish_job():
            try:
                save_game_record(room.build_record_summary())
            except Exception:
                logger.exception("[sanguo] 落库失败 room=%s", room.room_id)
            await room.on_broadcast({
                "type": "game_over",
                "winner": room.engine.winner(),
            })
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_finish_job())
        except RuntimeError:
            room.on_broadcast({"type": "game_over", "winner": room.engine.winner()})
    return _finished


def _verify_ws_token(token: str) -> str:
    try:
        token_data = get_auth_service().verify_token_data(token)
        return token_data.user_id
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


async def _safe_send(websocket, payload: dict) -> None:
    try:
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001  对端已断开
        logger.debug("[sanguo] WS 发送失败: %s", e)


# ---------- HTTP ----------
@router.get("/heroes")
async def get_heroes(user_id: str = Depends(get_current_user_id)):
    return {"heroes": [{"key": h.key, "name": h.name, "kingdom": h.kingdom.value,
                        "max_hp": h.max_hp, "skills": list(h.skills),
                        "gender": h.gender}
                       for h in HEROES.values()]}


@router.post("/rooms")
async def create_room(user_id: str = Depends(get_current_user_id)):
    room = manager.create_room(int(user_id), _nickname_of(user_id), list(HEROES.values()))
    room.on_broadcast = _make_broadcast(room)
    room.on_send = _make_sender(room)
    room.on_finished = _make_finished(room)
    return {"room_id": room.room_id}


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
    if not room.members:
        manager.remove(room.room_id)
    return {"ok": True}


@router.post("/rooms/{room_id}/kick")
async def kick_room(room_id: str, body: dict, user_id: str = Depends(get_current_user_id)):
    room = _get_room_or_404(room_id)
    try:
        room.kick(int(body.get("user_id")), int(user_id))
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
        raise HTTPException(status_code=400 if ("至少" in msg or "人数" in msg or "满" in msg) else 403,
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
    if int(user_id) not in room.members:
        raise HTTPException(status_code=403, detail="你不是该房间成员")
    return room.full_view(int(user_id))


@router.get("/records")
async def records_list(limit: int = 20, offset: int = 0,
                       user_id: str = Depends(get_current_user_id)):
    return query_records(limit=limit, offset=offset)


@router.get("/records/{record_id}")
async def record_detail(record_id: int, user_id: str = Depends(get_current_user_id)):
    data = query_record(record_id)
    if data is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return data


async def _pump(room: SanguoRoom) -> None:
    if room.engine is None:
        return
    if room.engine.finished() and room.status == "RESULT" and not room.record_saved:
        room.record_saved = True
        try:
            save_game_record(room.build_record_summary())
        except Exception:
            logger.exception("[sanguo] 落库失败 room=%s", room.room_id)
        await room.on_broadcast({"type": "game_over", "winner": room.engine.winner()})


# ---------- WebSocket（直接挂载，绕过 _IncludedRouter 对 WS 的分发缺陷） ----------
async def sanguo_room_ws(websocket) -> None:
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
    logger.info("[sanguo] WS 接入 room=%s user=%s", room_id, user_id)
    try:
        await _safe_send(websocket, {"type": "hello", "state": room.full_view(user_id)})
        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=60)
            except asyncio.TimeoutError:
                logger.info("[sanguo] WS 心跳超时 room=%s user=%s", room_id, user_id)
                break
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
        logger.info("[sanguo] WS 断开 room=%s user=%s", room_id, user_id)
    except Exception:  # noqa: BLE001  连接层异常统一按断开处理
        logger.exception("[sanguo] WS 异常断开 room=%s user=%s", room_id, user_id)
    finally:
        room.mark_disconnected(user_id, time.time(), ws=websocket)
        m = room.members.get(user_id)
        room.on_broadcast({"type": "event",
                           "text": f"{(m.nickname if m else user_id)} 与服务器断开连接"})
