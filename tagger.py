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

【品质等级判断标准（2026版）- 严格评估】

⚠️ **重要：品质评估必须严格！大多数 AI 生成音乐应评为「低品质」或「中品质」，只有极少数接近商业发行水准的作品才能评为「高品质」。**

**低品质（基础合格，满足日常听歌需求）** - 适用于大多数 AI 生成音乐：
- 旋律与调性：调性明确且高度稳定，无任何音准偏差，旋律流畅自然；小节内时值总和严格符合拍号要求
- 节奏与结构：节奏精准稳定，无明显抢拍、拖拍，具备"主歌+副歌"基础结构，时长2-5分钟
- 人声与情感：人声清晰自然，无机械失真、卡顿、数字电流声；发音准确率≥90%，气息平稳均匀
- 编曲与混音：配器简洁高效（2-3种核心乐器），无频段冲突；混音基础均衡，人声占比40-60%
- 文本逻辑：文本逻辑基本连贯，无明显语法错误；押韵率≥70%，主题简单明确
- 判定要点：如果存在任何 AI 生成痕迹（如轻微机械感、模板化编曲、情感表达平淡），应评为低品质

**中品质（细节打磨，具备专业创作质感）** - 需要明显超出基础水平：
- 旋律与调性：旋律富有起伏变化，Hook记忆点突出；和声进行合理流畅，可加入自然转调
- 节奏与结构：节奏富有层次变化（切分音、弱起拍），具备完整结构（前奏+主歌+预副歌+副歌+尾奏）
- 人声与情感：发音准确率≥98%，咬字细腻自然；具备中级情感深度，可适度颤音、转音
- 编曲与混音：配器丰富多样（4-6种乐器），声部层次清晰；动态范围控制在12-15dB
- 文本逻辑：文本结构清晰（主歌叙事、副歌高潮）；押韵率≥85%，主题富有深度
- 判定要点：需要在多个维度（至少3个）明显超出基础水平，但仍可察觉一定的 AI 痕迹

**高品质（专业质感，逼近商业作品）** - 极少数作品能达到，需满足以下全部条件：
- 旋律与调性：旋律创意性强，Hook段高辨识度；和声编排复杂高级（七和弦、九和弦、借调、模进）
- 节奏与结构：节奏灵动多变，结合风格设计特色节奏型；结构灵活创新
- 人声与情感：发音准确率≥99%，咬字与情感深度高度绑定；接近真人专业演唱水准，和声立体多层
- 编曲与混音：配器精细化且富有创意；混音达到商业级标准，动态范围12-18dB，LUFS -14dB
- 文本逻辑：文本文学性强，逻辑严密富有诗意；押韵率≥95%，高度原创性和艺术张力
- ⚠️ 判定要点：必须在所有维度都达到专业水准，几乎无法分辨是 AI 生成，具备商业发行潜力。如有任何明显短板，应降级为中品质

【标签说明】
- quality: 品质等级，必填（低品质/中品质/高品质）
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

            # 规范化品质标签（确保只有三个标准值）
            if "quality" in tags:
                quality = tags["quality"]
                if isinstance(quality, str):
                    quality_lower = quality.lower()
                    if "高" in quality or "high" in quality_lower:
                        tags["quality"] = "高品质"
                    elif "中" in quality or "medium" in quality_lower or "mid" in quality_lower:
                        tags["quality"] = "中品质"
                    else:
                        tags["quality"] = "低品质"

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
