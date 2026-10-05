"""狼人杀 API 请求模型"""

from pydantic import BaseModel, Field


class CreateRoomRequest(BaseModel):
    board_id: str | None = Field(None, description="预置板子 id")
    custom_roles: dict[str, int] | None = Field(None, description="自定义角色数量")
    board_name: str = Field("自定义局", max_length=32)
    speech_seconds: int = Field(60, ge=30, le=120)
    witch_self_rescue: str = Field("never", pattern="^(never|first_night|always)$")
    witch_guard_conflict: bool = True


class UpdateConfigRequest(BaseModel):
    board_id: str | None = None
    custom_roles: dict[str, int] | None = None
    board_name: str | None = None
    speech_seconds: int | None = Field(None, ge=30, le=120)
    witch_self_rescue: str | None = Field(None,
                                             pattern="^(never|first_night|always)$")
    witch_guard_conflict: bool | None = None


class KickRequest(BaseModel):
    user_id: str
