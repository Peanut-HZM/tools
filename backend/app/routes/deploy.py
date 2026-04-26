"""
部署信息 API - 提供部署时间戳等部署相关信息
"""

import logging
import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

DEPLOY_TIMESTAMP_FILE = Path(__file__).parent.parent.parent / ".deploy_timestamp"


@router.get("/deploy/timestamp")
async def get_deploy_timestamp():
    """获取上次部署时间"""
    try:
        if not DEPLOY_TIMESTAMP_FILE.exists():
            raise HTTPException(status_code=404, detail="部署时间戳不存在，可能尚未部署")
        
        with open(DEPLOY_TIMESTAMP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return {"timestamp": data["timestamp"], "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取部署时间戳失败: {e}")
        raise HTTPException(status_code=500, detail=f"读取部署时间戳失败: {str(e)}")
