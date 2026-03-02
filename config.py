"""
配置管理模块
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class Config:
    """应用配置"""

    # OpenRouter API 配置
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    model: str = "google/gemini-3-flash-preview"  # 使用 Gemini 3 Flash Preview

    # 数据库配置
    database_path: str = "data/musetag.db"

    # 导出配置
    export_dir: str = "exports"

    # 支持的音频格式
    supported_audio_formats: tuple = ("mp3", "wav", "flac", "m4a", "aac", "ogg", "wma")

    # API 调用配置
    max_retries: int = 3
    retry_delay: float = 1.0
    request_timeout: int = 120  # 秒

    # 音频处理配置
    max_audio_size_mb: int = 20  # 最大音频文件大小（MB）
    audio_sample_duration: int = 60  # 音频采样时长（秒），用于大文件截取

    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        api_key = os.getenv("OPENROUTER_API_KEY", "")

        # 获取项目根目录
        project_root = Path(__file__).parent

        return cls(
            openrouter_api_key=api_key,
            database_path=str(project_root / "data" / "musetag.db"),
            export_dir=str(project_root / "exports"),
            model=os.getenv("MODEL", "google/gemini-2.0-flash"),
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_delay=float(os.getenv("RETRY_DELAY", "1.0")),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "120")),
            max_audio_size_mb=int(os.getenv("MAX_AUDIO_SIZE_MB", "20")),
        )

    def validate(self) -> list[str]:
        """验证配置，返回错误列表"""
        errors = []

        if not self.openrouter_api_key:
            errors.append("OPENROUTER_API_KEY 未设置")

        return errors


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取配置实例（单例）"""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reload_config() -> Config:
    """重新加载配置"""
    global _config
    load_dotenv(override=True)
    _config = Config.from_env()
    return _config
