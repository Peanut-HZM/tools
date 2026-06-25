from pydantic_settings import BaseSettings

class OCRSettings(BaseSettings):
    # OCR 服务地址（Umi-OCR，nginx 代理路径 /umi-ocr/）
    OCR_API_URL: str = "https://ocr.peanuthzm.com.cn/umi-ocr"
    # API Key（Umi-OCR 无需认证，保留字段兼容未来扩展）
    API_KEY: str = ""
    # API Secret
    API_SECRET: str = ""

    class Config:
        env_file = ".env"
        env_prefix = "OCR_"
        extra = "ignore"

ocr_settings = OCRSettings()
