@router.get("/summary", response_model=SummaryResponse)
async def get_token_usage_summary(
    source: str = "all",
    type: str = "daily",
    days: int = 30,
    group_by: str = "none",
    device_id: Optional[str] = None,
    tool_id: Optional[str] = None,
    model: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    # 尝试从 Redis 缓存读取（优先返回缓存）
    from app.services.token_usage_cache import get_query_cached_payload, set_query_cached_data
    
    cache_payload = get_query_cached_payload(
        source=source,
        report_type=type,
        days=days,
        group_by=group_by,
        user_id=user_id,
        device_id=device_id or "",
        tool_id=tool_id or "",
        model=model or "",
        sort_by="date",
        sort_order="desc",
    )
    
    if cache_payload:
        logger.info(f"summary 缓存命中: user={user_id}, source={source}, days={days}")
        cached_response = dict(cache_payload)
        cached_response.pop("_cache_ttl_seconds", None)
        return SummaryResponse(**cached_response, cached=True)

    db = SessionLocal()
    try:
        from app.utils.device_name_resolver import load_alias_map

        alias_map = load_alias_map(db, user_id)

        req = SimpleNamespace(
            source=source,
            type=type,
            days=days,
            group_by=group_by,
            device_id=device_id,
            tool_id=tool_id,
            model=model,
            sort_by="date",
            sort_order="desc",
        )

        has_data = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.user_id == user_id)
            .first()
            is not None
        )
        if not has_data:
            return SummaryResponse(
                summary=SummaryUsageSummary(
                    total_input_tokens=0,
                    total_output_tokens=0,
                    total_cache_creation_tokens=0,
                    total_cache_read_tokens=0,
                    total_tokens=0,
                    total_cost=0.0,
                    days_count=0,
                    avg_daily_cost=0.0,
                )
            )

        since_date = datetime.now() - timedelta(days=days)
        
        # 优化：使用数据库聚合替代 Python 内存聚合
        agg_result = (
            db.query(
                func.sum(TokenUsageRecord.input_tokens).label("total_input"),
                func.sum(TokenUsageRecord.output_tokens).label("total_output"),
                func.sum(TokenUsageRecord.cache_creation_tokens).label("total_cc"),
                func.sum(TokenUsageRecord.cache_read_tokens).label("total_cr"),
                func.sum(TokenUsageRecord.total_cost).label("total_cost"),
                func.count(func.distinct(TokenUsageRecord.record_date)).label("days_count"),
            )
            .filter(*_build_record_filters(user_id, req, since_date, alias_map, db=db))
            .first()
        )
        
        total_input = int(agg_result.total_input or 0)
        total_output = int(agg_result.total_output or 0)
        total_cc = int(agg_result.total_cc or 0)
        total_cr = int(agg_result.total_cr or 0)
        total_tokens = total_input + total_output + total_cc + total_cr
        total_cost = float(agg_result.total_cost or 0)
        days_count = int(agg_result.days_count or 0)

        summary = SummaryUsageSummary(
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cache_creation_tokens=total_cc,
            total_cache_read_tokens=total_cr,
            total_tokens=total_tokens,
            total_cost=round(total_cost, 4),
            days_count=days_count,
            avg_daily_cost=round(total_cost / max(days_count, 1), 4),
        )

        dimension_rows, filter_options = _query_dimension_data(
            db, user_id, req, since_date, alias_map
        )

        model_rows = _execute_model_summary_query(db, user_id, req, since_date, alias_map)
        model_summary = _rows_to_model_summary(model_rows)

        device_names = _load_device_names(db, user_id)
        devices = [{"id": did, "name": name} for did, name in device_names.items()]

        # 优化：单独查询用于图表的数据（只取必要字段）
        chart_records = (
            db.query(
                TokenUsageRecord.record_date,
                TokenUsageRecord.input_tokens,
                TokenUsageRecord.output_tokens,
                TokenUsageRecord.cache_creation_tokens,
                TokenUsageRecord.cache_read_tokens,
                TokenUsageRecord.total_tokens,
                TokenUsageRecord.total_cost,
            )
            .filter(*_build_record_filters(user_id, req, since_date, alias_map, db=db))
            .all()
        )
        chart_series = build_chart_series(chart_records, group_by)

        sync_meta = _get_sync_meta(db, user_id, req, None)

        payload = SummaryResponse(
            summary=summary,
            dimension_summaries=_to_dimension_summaries(dimension_rows),
            model_summary=model_summary,
            filter_options=_to_filter_options(filter_options),
            sync_meta=_to_sync_meta(sync_meta),
            chart_series=[ChartSeriesItem(**s) for s in chart_series],
            devices=devices,
        ).model_dump(exclude={"cached"})

        # 写入 Redis 缓存
        set_query_cached_data(
            source=source,
            report_type=type,
            days=days,
            group_by=group_by,
            user_id=user_id,
            device_id=device_id or "",
            tool_id=tool_id or "",
            model=model or "",
            sort_by="date",
            sort_order="desc",
            data=payload,
        )

        return SummaryResponse(**payload, cached=False)
    finally:
        db.close()


