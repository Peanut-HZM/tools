from pydantic import BaseModel, Field
from typing import Optional

class ASRRequest(BaseModel):
    # 通常通过 Multipart/form-data 上传文件，这里定义辅助参数
    language: str = Field("zh", description="音频语言")

class ASRResponse(BaseModel):
    text: str = Field(..., description="识别出的文本")
    duration: float = Field(..., description="音频时长")
    processing_time: float = Field(..., description="处理耗时")
