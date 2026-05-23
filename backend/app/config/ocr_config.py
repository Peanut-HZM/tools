from pydantic_settings import BaseSettings

class OCRSettings(BaseSettings):
    # OCR 服务地址
    OCR_API_URL: str = "https://ocr.peanuthzm.com.cn"
    # API Key
    API_KEY: str = ""
    # API Secret
    API_SECRET: str = ""
    
    class Config:
        env_file = ".env"
        env_prefix = "OCR_"
        extra = "ignore"

ocr_settings = OCRSettings()
