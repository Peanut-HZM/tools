from pydantic_settings import BaseSettings

class ASRSettings(BaseSettings):
    # ASR 服务地址 (与 OCR 共用同一个网关)
    ASR_API_URL: str = ""
    # API Key (通常共用)
    API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        env_prefix = "ASR_"
        extra = "ignore"

asr_settings = ASRSettings()
