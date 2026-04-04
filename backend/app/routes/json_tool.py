from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Dict, Any
import json

from app.models.json_tool_models import (
    JSONFormatRequest, JSONFormatResponse,
    JSONMinifyRequest, JSONMinifyResponse,
    JSONValidateRequest, JSONValidateResponse,
    JSONCompareRequest, JSONCompareResponse,
    JSONConvertRequest, JSONConvertResponse, JSONConvertFormat,
    JSONHistoryListResponse, JSONHistoryRecord,
    JSONQuotaInfo
)
from app.services.json_tool_service import json_tool_service
from app.middleware.auth_middleware import get_current_user_id

router = APIRouter(prefix="/json-tool", tags=["JSON 工具"])


@router.post("/format", response_model=JSONFormatResponse)
async def format_json(
    request: JSONFormatRequest,
    user_id: str = Depends(get_current_user_id)
):
    """格式化 JSON"""
    try:
        return json_tool_service.format_json(
            user_id=user_id,
            content=request.content,
            indent=request.indent,
            sort_keys=request.sort_keys
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/minify", response_model=JSONMinifyResponse)
async def minify_json(
    request: JSONMinifyRequest,
    user_id: str = Depends(get_current_user_id)
):
    """压缩 JSON"""
    try:
        return json_tool_service.minify_json(
            user_id=user_id,
            content=request.content
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", response_model=JSONValidateResponse)
async def validate_json(
    request: JSONValidateRequest,
    user_id: str = Depends(get_current_user_id)
):
    """校验 JSON"""
    try:
        return json_tool_service.validate_json(
            user_id=user_id,
            content=request.content
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=JSONCompareResponse)
async def compare_json(
    request: JSONCompareRequest,
    user_id: str = Depends(get_current_user_id)
):
    """比较两个 JSON"""
    try:
        return json_tool_service.compare_json(
            user_id=user_id,
            json1=request.json1,
            json2=request.json2
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/convert", response_model=JSONConvertResponse)
async def convert_json(
    request: JSONConvertRequest,
    user_id: str = Depends(get_current_user_id)
):
    """转换 JSON 为其他格式"""
    try:
        return json_tool_service.convert_json(
            user_id=user_id,
            content=request.content,
            target_format=request.target_format
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=JSONHistoryListResponse)
async def get_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user_id: str = Depends(get_current_user_id)
):
    """获取用户 JSON 操作历史记录"""
    try:
        records, total = json_tool_service.get_history(user_id, page, page_size)
        return JSONHistoryListResponse(
            records=records,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quota", response_model=JSONQuotaInfo)
async def get_quota(user_id: str = Depends(get_current_user_id)):
    """获取用户配额信息"""
    try:
        return json_tool_service._check_quota(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def query_json(
    content: str = Body(..., embed=True, description="JSON 内容"),
    path: str = Body(..., embed=True, description="JSONPath 表达式"),
    user_id: str = Depends(get_current_user_id)
):
    """使用 JSONPath 查询 JSON 数据"""
    try:
        # 简单的 JSONPath 实现
        import jsonpath_ng
        import jsonpath_ng.ext

        parsed = json.loads(content)
        jsonpath_expr = jsonpath_ng.ext.parse(path)
        matches = [match.value for match in jsonpath_expr.find(parsed)]

        return {
            "result": matches[0] if len(matches) == 1 else matches,
            "result_type": type(matches[0]).__name__ if matches else "null"
        }
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"无效的 JSON 格式：{str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
