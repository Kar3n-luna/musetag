"""
核心打标逻辑模块
"""

import json
import logging
import time
from typing import Dict, Any
import requests

from config import Config
from tags_schema import build_tag_music_tool, TAG_LIBRARY, parse_string_to_list
from utils import get_file_size_mb, truncate_audio_for_api

logger = logging.getLogger(__name__)


class AudioTagger:
    """音频打标器"""

    def __init__(self, config: Config, db=None):
        self.config = config
        self.api_key = config.openrouter_api_key
        self.base_url = config.openrouter_base_url
        self.model = config.model
        self.db = db
        self.tool = build_tag_music_tool(db)

    def tag(self, audio_path: str) -> Dict[str, Any]:
        """
        分析音频并返回标签

        Args:
            audio_path: 音频文件路径

        Returns:
            标签字典
        """
        logger.info(f"开始分析音频: {audio_path}")

        # 1. 准备音频数据
        audio_data, was_truncated = self._prepare_audio(audio_path)
        audio_base64 = self._encode_base64(audio_data)
        mime_type = self._get_mime_type(audio_path)

        # 2. 调用 API
        response = self._call_api(audio_base64, mime_type)

        # 3. 解析结果
        tags = self._parse_response(response)
        tags["was_truncated"] = was_truncated

        logger.info(f"分析完成: {audio_path}")
        logger.info(f"标签结果: style={tags.get('style_primary')}, emotion={tags.get('emotion_primary')}, scene={tags.get('scene_primary')}")

        return tags

    def _prepare_audio(self, audio_path: str) -> tuple[bytes, bool]:
        """准备音频数据（可能截取）"""
        file_size = get_file_size_mb(audio_path)

        if file_size > self.config.max_audio_size_mb:
            logger.warning(f"文件过大 ({file_size:.2f}MB)，将进行截取")
            return truncate_audio_for_api(
                audio_path,
                self.config.max_audio_size_mb,
                self.config.audio_sample_duration
            )
        else:
            with open(audio_path, "rb") as f:
                return f.read(), False

    def _encode_base64(self, data: bytes) -> str:
        """编码为 base64"""
        import base64
        return base64.standard_b64encode(data).decode("utf-8")

    def _get_mime_type(self, file_path: str) -> str:
        """根据文件扩展名获取 MIME 类型"""
        from pathlib import Path
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

    def _call_api(self, audio_base64: str, mime_type: str) -> Dict[str, Any]:
        """调用 OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://musetag.local",
            "X-Title": "MuseTAG"
        }

        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": self._build_prompt()
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{audio_base64}"
                        }
                    }
                ]
            }
        ]

        payload = {
            "model": self.model,
            "messages": messages,
            "tools": [self.tool],
            "tool_choice": {"type": "function", "function": {"name": "tag_music"}},
            "max_tokens": 1024
        }

        # 带重试的请求
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.config.request_timeout
                )

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"API 速率限制，等待 {retry_after} 秒后重试")
                    time.sleep(retry_after)
                    continue

                last_error = f"API 错误 ({response.status_code}): {response.text}"
                logger.error(last_error)

            except requests.exceptions.Timeout:
                last_error = "API 请求超时"
                logger.warning(f"{last_error}，尝试 {attempt + 1}/{self.config.max_retries}")
            except requests.exceptions.RequestException as e:
                last_error = f"API 请求失败: {str(e)}"
                logger.error(last_error)

            if attempt < self.config.max_retries - 1:
                time.sleep(self.config.retry_delay * (attempt + 1))

        raise Exception(f"API 调用失败: {last_error}")

    def _build_prompt(self) -> str:
        """构建提示词 - 强调必须使用库内标签，包含品质判断标准"""
        return """请仔细分析这段音频，为其打上分类标签。

【重要规则】
1. 所有标签必须从预设标签库中选择，不允许使用库外标签
2. 一级标签为必填项，其中 style_primary 和 scene_primary 可多选（用逗号分隔）
3. 二级标签为可选项，可多选
4. 品质等级为必填项，需要综合评估后选择

【品质等级判断标准】

**低等级（基础合格）**：
- 旋律与调性：调性明确，无明显跑调、音准偏移，旋律流畅不违和
- 节奏与结构：节奏稳定，无明显抢拍、拖拍，具备"主歌+副歌"基础结构
- 人声与情感：人声清晰可辨，无严重机械音、卡顿，歌词发音准确率≥85%
- 编曲与混音：配器简洁（2-3种核心乐器），混音基础均衡，无明显失真

**中等级（细节打磨）**：
- 旋律与调性：旋律有起伏变化，副歌与主歌音域形成对比，和声进行合理
- 节奏与结构：节奏富有层次，具备完整结构（前奏+主歌+副歌+尾奏）
- 人声与情感：发音准确率≥95%，咬字细腻，有基础情感表达
- 编曲与混音：配器丰富（4-6种乐器），声部层次清晰，混音细节优化

**高等级（专业质感）**：
- 旋律与调性：旋律创意性强，Hook段具备高辨识度，和声编排复杂高级
- 节奏与结构：节奏变化灵动，结构可灵活创新，整体时长适配风格
- 人声与情感：发音准确率100%，情感表达丰富，接近专业演唱水准
- 编曲与混音：配器精细化，混音达到商业级标准，动态范围合理

【标签说明】
- quality: 品质等级，必填（低等级/中等级/高等级）
- quality_reason: 品质评价理由，必填，简要说明给出该品质等级的具体依据（30-80字）
- style_primary: 音乐风格，可选1-3个（流行/摇滚/电子/嘻哈说唱/民谣/国风/爵士/蓝调/纯音乐/古典/世界音乐）
- emotion_primary: 主要情绪，选1个（积极情绪/中性情绪/消极情绪）
- scene_primary: 适用场景，可选1-3个（学习工作/运动健身/休闲放松/影音游戏/出行生活/社交聚会/特殊场景）
- language: 歌曲语言，选1个
- vocal_primary: 人声类型，选1个（无人声/男声/女声/童声/群声）

请调用 tag_music 函数返回结果。"""

    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """解析 API 响应，提取标签"""
        try:
            choices = response.get("choices", [])
            if not choices:
                raise ValueError("API 响应中没有 choices")

            message = choices[0].get("message", {})
            tool_calls = message.get("tool_calls", [])

            if not tool_calls:
                content = message.get("content", "")
                if content:
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        pass
                raise ValueError("API 响应中没有 tool_calls")

            # 解析 tool call
            tool_call = tool_calls[0]
            function = tool_call.get("function", {})
            arguments = function.get("arguments", "{}")

            if isinstance(arguments, str):
                tags = json.loads(arguments)
            else:
                tags = arguments

            # 将逗号分隔的字符串转为列表
            list_fields = [
                "style_primary", "style_secondary",
                "scene_primary", "scene_secondary",
                "emotion_secondary",
                "vocal_type", "vocal_traits",
                "feature"
            ]
            for field in list_fields:
                if field in tags and isinstance(tags[field], str):
                    tags[field] = parse_string_to_list(tags[field])

            return tags

        except json.JSONDecodeError as e:
            logger.error(f"解析 API 响应失败: {e}")
            raise ValueError(f"解析 API 响应失败: {e}")


def create_tagger(config: Config = None, db=None) -> AudioTagger:
    """创建打标器实例"""
    if config is None:
        from config import get_config
        config = get_config()
    if db is None:
        from database import get_database
        db = get_database()
    return AudioTagger(config, db)
