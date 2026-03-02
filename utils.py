"""
工具函数模块
"""

import os
import hashlib
import base64
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_file_hash(file_path: str) -> str:
    """计算文件的 MD5 哈希值"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_file_size_mb(file_path: str) -> float:
    """获取文件大小（MB）"""
    return os.path.getsize(file_path) / (1024 * 1024)


def encode_audio_to_base64(file_path: str) -> str:
    """将音频文件编码为 base64"""
    with open(file_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_audio_mime_type(file_path: str) -> str:
    """根据文件扩展名获取 MIME 类型"""
    ext = Path(file_path).suffix.lower()
    mime_map = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
        ".wma": "audio/x-ms-wma",
    }
    return mime_map.get(ext, "audio/mpeg")


def scan_audio_files(folder_path: str, extensions: tuple = None) -> list[str]:
    """
    扫描文件夹中的音频文件

    Args:
        folder_path: 文件夹路径
        extensions: 支持的扩展名元组，如 (".mp3", ".wav")

    Returns:
        音频文件路径列表
    """
    if extensions is None:
        extensions = (".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma")

    folder = Path(folder_path)
    if not folder.exists():
        logger.warning(f"文件夹不存在: {folder_path}")
        return []

    audio_files = []
    for ext in extensions:
        audio_files.extend(folder.rglob(f"*{ext}"))
        audio_files.extend(folder.rglob(f"*{ext.upper()}"))

    # 转换为字符串并去重
    return sorted(set(str(f) for f in audio_files))


def format_duration(seconds: float) -> str:
    """格式化时长为 mm:ss 格式"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def get_audio_duration(file_path: str) -> Optional[float]:
    """
    获取音频时长（秒）

    尝试使用 mutagen 库，如果不可用则返回 None
    """
    try:
        from mutagen import File
        audio = File(file_path)
        if audio is not None and hasattr(audio.info, 'length'):
            return audio.info.length
    except ImportError:
        logger.warning("mutagen 库未安装，无法获取音频时长")
    except Exception as e:
        logger.warning(f"获取音频时长失败: {e}")

    return None


def truncate_audio_for_api(
    file_path: str,
    max_size_mb: float = 20.0,
    sample_duration: int = 60
) -> tuple[bytes, bool]:
    """
    为 API 调用准备音频数据

    如果文件过大，尝试截取采样部分

    Args:
        file_path: 音频文件路径
        max_size_mb: 最大文件大小（MB）
        sample_duration: 采样时长（秒）

    Returns:
        (音频数据, 是否被截取)
    """
    file_size = get_file_size_mb(file_path)

    # 如果文件大小在限制内，直接读取
    if file_size <= max_size_mb:
        with open(file_path, "rb") as f:
            return f.read(), False

    # 文件过大，尝试截取
    logger.info(f"文件过大 ({file_size:.2f}MB)，尝试截取前 {sample_duration} 秒")

    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_file(file_path)
        sample_ms = sample_duration * 1000

        if len(audio) > sample_ms:
            audio = audio[:sample_ms]

        # 导出为 bytes
        import io
        buffer = io.BytesIO()
        format = Path(file_path).suffix.lower()[1:]  # 去掉点
        if format == "m4a":
            format = "ipod"
        audio.export(buffer, format=format)
        return buffer.getvalue(), True

    except ImportError:
        logger.warning("pydub 库未安装，无法截取音频，将使用原始文件")
        with open(file_path, "rb") as f:
            return f.read(), False
    except Exception as e:
        logger.warning(f"截取音频失败: {e}，将使用原始文件")
        with open(file_path, "rb") as f:
            return f.read(), False


def ensure_dir(path: str) -> Path:
    """确保目录存在"""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除不安全字符"""
    # 移除不安全字符
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, "_")
    return filename.strip()
