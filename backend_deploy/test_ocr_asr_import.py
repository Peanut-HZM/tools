import sys
import logging
import os
from pathlib import Path

# Mock HOME before any imports to trick libraries hardcoding ~/.xxx
PROJECT_ROOT = Path(__file__).parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ["HOME"] = str(CACHE_DIR)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set cache directories
os.environ["PADDLE_HOME"] = str(CACHE_DIR / "paddle")
os.environ["HF_HOME"] = str(CACHE_DIR / "huggingface")
os.environ["MODELSCOPE_CACHE"] = str(CACHE_DIR / "modelscope")
os.environ["XDG_CACHE_HOME"] = str(CACHE_DIR / "xdg")

logger.info(f"Set HOME to {os.environ['HOME']}")

def test_imports():
    logger.info("Testing imports...")
    
    try:
        import paddleocr
        from paddleocr import PaddleOCR
        logger.info(f"PaddleOCR version: {paddleocr.__version__}")
        # 尝试初始化 (使用 CPU)
        ocr = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=False, show_log=False)
        logger.info("PaddleOCR initialized successfully.")
    except Exception as e:
        logger.error(f"PaddleOCR failed: {e}")
        
    try:
        import funasr
        from funasr import AutoModel
        logger.info(f"FunASR version: {funasr.__version__}")
        # 暂时不下载模型，只检查导入
        logger.info("FunASR imported successfully.")
    except Exception as e:
        logger.error(f"FunASR failed: {e}")

if __name__ == "__main__":
    test_imports()
