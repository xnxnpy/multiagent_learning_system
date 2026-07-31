from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置管理"""

    # FastAPI 配置
    APP_NAME: str = "智学优培"
    DEBUG: bool = True
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_EXPIRE_MINUTES: int = 1440  # 24小时

    # MySQL 8.0 数据库配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "your-mysql-password"
    MYSQL_DATABASE: str = "ai_learning"

    # Redis 5 配置
    REDIS_URL: str = "redis://localhost:6379/0"

    # ChromaDB 配置
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma"
    CHROMA_COLLECTION: str = "learning_resources"
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000

    # Neo4j 知识图谱配置
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "your-neo4j-password"

    # JWT 配置
    JWT_SECRET_KEY: str = "your-jwt-secret-key-here"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # 讯飞星火 API 配置
    # WebSocket 使用 APP_ID + API_KEY + API_SECRET
    XUNFEI_APP_ID: str = "your-xunfei-app-id"
    XUNFEI_API_KEY: str = "your-xunfei-api-key"
    XUNFEI_API_SECRET: str = "your-xunfei-api-secret"
    
    # HTTP API 使用 APIPassword（每个模型独立）
    XUNFEI_API_PASSWORD_LITE: str = "your-api-password-lite"
    XUNFEI_API_PASSWORD_PRO: str = "your-api-password-pro"
    XUNFEI_API_PASSWORD_PRO_128K: str = "your-api-password-pro-128k"
    XUNFEI_API_PASSWORD_ULTRA: str = "your-api-password-ultra"
    XUNFEI_API_PASSWORD_X1: str = "your-api-password-x1"
    XUNFEI_API_PASSWORD_X2: str = "your-api-password-x2"
    XUNFEI_API_PASSWORD_X2_FLASH: str = "your-api-password-x2-flash"
    
    # 模型选择
    XUNFEI_MODEL: str = "lite"
    XUNFEI_REASONING_MODEL: str = "x2-flash"

    # Celery 配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # 讯飞图片生成服务配置（使用 XUNFEI_API_KEY/XUNFEI_API_SECRET 鉴权）
    QWEN_IMAGE_APP_ID: str = "your-xunfei-app-id"
    QWEN_IMAGE_MODEL_ID: str = "xopqwentti20b"
    QWEN_IMAGE_API_URL: str = "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/tti"

    # StableDiffusion XL 图片生成（同样使用 XUNFEI 凭证）
    SDXL_APP_ID: str = "your-xunfei-app-id"
    SDXL_MODEL_ID: str = "xssdxl"
    SDXL_API_URL: str = "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/tti"

    # Z-Image-Turbo 图片生成（同样使用 XUNFEI 凭证）
    ZIMAGE_TURBO_APP_ID: str = "your-xunfei-app-id"
    ZIMAGE_TURBO_MODEL_ID: str = "xopzimageturbo"
    ZIMAGE_TURBO_API_URL: str = "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/tti"

    # 多模态模型（图片理解 + 文本生成）
    QWEN36_MULTIMODAL_APP_ID: str = "your-xunfei-app-id"
    QWEN36_MULTIMODAL_MODEL_ID: str = "xopqwen36v35b"
    QWEN36_MULTIMODAL_API_URL: str = "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/chat"

    QWEN35_MULTIMODAL_APP_ID: str = "your-xunfei-app-id"
    QWEN35_MULTIMODAL_MODEL_ID: str = "xopqwen35v35b"
    QWEN35_MULTIMODAL_API_URL: str = "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/chat"

    # 文本推理模型
    QWEN3_17B_APP_ID: str = "your-xunfei-app-id"
    QWEN3_17B_MODEL_ID: str = "xop3qwen1b7"
    QWEN3_17B_API_URL: str = "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/chat"

    QWEN35_2B_APP_ID: str = "your-xunfei-app-id"
    QWEN35_2B_MODEL_ID: str = "xop35qwen2b"
    QWEN35_2B_API_URL: str = "https://maas-api.cn-huabei-1.xf-yun.com/v2.1/chat"

    # 多模态资源生成配置（可选）
    SD_API_URL: str = "http://localhost:7860/sdapi/v1/txt2img"
    SD_API_KEY: str = ""

    # 讯飞 TTS 配置
    XUNFEI_TTS_APP_ID: str = "your-xunfei-app-id"
    XUNFEI_TTS_WS_URL: str = "wss://tts-api.xfyun.cn/v2/tts"

    # 讯飞 ASR 配置
    XUNFEI_ASR_WS_URL: str = "wss://iat-api.xfyun.cn/v2/iat"

    # 讯飞 OCR 配置（通用文字识别 intsig，支持52种语言，用于辅导场景图片题目识别）
    XUNFEI_OCR_URL: str = "https://api.xf-yun.com/v1/private/hh_ocr_recognize_doc"

    # 阿里云 OSS 配置
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET_NAME: str = ""
    OSS_ENDPOINT: str = "oss-cn-hangzhou.aliyuncs.com"
    OSS_BASE_URL: str = ""  # 自定义域名（可选），为空则用 bucket.endpoint 格式

    # PPT 视频临时文件目录
    PPT_VIDEO_TEMP_DIR: str = "./data/tmp/ppt_video"

    DALLE_API_KEY: str = ""

    # 后端配置
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
