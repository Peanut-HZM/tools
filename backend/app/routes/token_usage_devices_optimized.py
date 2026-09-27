@router.get("/devices")
async def get_user_devices(
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """获取当前用户的设备列表（含指纹类型和 canonical_id）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    # 尝试从 Redis 缓存读取（5分钟缓存，设备列表变化频率低）
    from app.services.token_usage_cache import get_redis_client
    import json
    
    client = get_redis_client()
    cache_key = f"devices:{user_id}"
    
    if client:
        try:
            cached_data = client.get(cache_key)
            if cached_data:
                logger.info(f"devices 缓存命中: user={user_id}")
                return json.loads(cached_data)
        except Exception:
            pass

    db = SessionLocal()
    try:
        current_device_id = get_device_id()
        regs = db.query(DeviceRegistry).filter(DeviceRegistry.user_id == user_id).all()
        alias_rows = db.query(DeviceIdAlias).filter(DeviceIdAlias.user_id == user_id).all()
        alias_map = {row.alias_device_id: row.canonical_device_id for row in alias_rows}

        if regs:
            devices = [
                {
                    "id": reg.device_id,
                    "name": reg.display_name
                    or reg.default_display_name
                    or reg.device_id,
                    "default_name": reg.default_display_name or reg.device_id,
                    "display_name": reg.display_name,
                    "fingerprint": reg.device_fingerprint,
                    "id_type": reg.id_type,
                    "canonical_id": alias_map.get(reg.device_id),
                    "is_current": reg.device_id == current_device_id,
                }
                for reg in regs
            ]
        else:
            device_ids = (
                db.query(TokenUsageRecord.device_id)
                .filter(TokenUsageRecord.user_id == user_id)
                .distinct()
                .all()
            )
            devices = [{"id": row[0], "name": row[0]} for row in device_ids]

        result = {"devices": devices}
        
        # 写入缓存（5分钟）
        if client:
            try:
                client.setex(cache_key, 300, json.dumps(result))
                logger.info(f"devices 缓存已写入: user={user_id}, TTL=300s")
            except Exception:
                pass
        
        return result
    finally:
        db.close()


