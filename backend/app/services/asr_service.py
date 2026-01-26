import re
import time
import logging
import httpx
import os
from app.models.asr_models import ASRResponse
from app.config.asr_config import asr_settings

logger = logging.getLogger(__name__)

class ASRService:
    def __init__(self):
        self.api_url = asr_settings.ASR_API_URL
        # ASR 接口目前不需要显式 API Key，如果需要可以从 asr_settings.API_KEY 获取

    def _clean_text(self, text: str) -> str:
        """
        清理 ASR 输出的文本，移除特殊标签
        """
        if not text:
            return ""
        # 移除 <|...|> 格式的标签
        cleaned = re.sub(r'<\|.*?\|>', '', text)
        # 移除多余的空白字符
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def predict(self, audio_file_path: str) -> ASRResponse:
        """
        调用远程 ASR 服务进行语音识别
        :param audio_file_path: 音频文件路径
        """
        start_time = time.time()
        
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        try:
            # 构造请求
            # 根据 Umi-OCR 源码，ASR 默认路径是 /asr-http/，但也可能通过网关转发到 /recognition
            # 这里的 ASR_API_URL 是 https://ocr.peanuthzm.com.cn
            # 实际上 Nginx 配置了 /asr-http/ -> http://127.0.0.1:8000/
            # 而 FunASR 服务通常监听 /recognition 路径
            # 所以完整路径应该是 /asr-http/recognition
            
            target_url = f"{self.api_url}/asr-http/recognition"
            logger.info(f"Calling ASR API: {target_url}")
            
            with open(audio_file_path, "rb") as f:
                # Umi-OCR 的 AsrController 接收 multipart/form-data，字段名为 "audio" (在 AsrServiceImpl 中看到)
                # 但 AsrController 中使用的是 @ModelAttribute AsrRecognizeForm，其中字段名为 file
                # 再看 AsrServiceImpl.recognizeToPath 方法：
                # httpClientService.sendPostFormWithField(path, "audio", file, formParams);
                # 这里发送的字段名是 "audio"。
                # 所以我们应该使用 "audio" 字段。
                
                files = {"audio": (os.path.basename(audio_file_path), f, "audio/wav")}
                
                # 使用 httpx 发送请求
                with httpx.Client(timeout=120.0) as client:
                    response = client.post(target_url, files=files)
                    
                    if response.status_code != 200:
                        raise RuntimeError(f"ASR API error: {response.status_code} - {response.text}")
                    
                    result = response.json()
                    
                    # 解析结果 (参考 AsrServiceImpl.recognizeToPath 的解析逻辑)
                    # { "code": 0, "text": "...", "sentences": [...], "time": ... }
                    
                    code = result.get("code")
                    if code != 0:
                         message = result.get("message") or result.get("msg") or "ASR识别失败"
                         raise RuntimeError(f"ASR failed with code {code}: {message}")

                    text = result.get("text", "")
                    
                    # 格式化处理文本，移除特殊标签
                    text = self._clean_text(text)
                    
                    # 处理 sentences (如果需要更详细的结果)
                    # sentences = result.get("sentences", [])
                    
                    # 获取 duration (如果 API 返回)
                    # 这里的 time 可能是处理耗时，也可能是音频时长，需确认
                    # Umi-OCR 源码中：Double time = resp.get("time") ...
                    # 通常 FunASR 返回的是处理耗时。
                    duration = 0.0 

            processing_time = time.time() - start_time
            
            return ASRResponse(
                text=text,
                duration=duration,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"ASR prediction failed: {e}")
            raise

asr_service = ASRService()
