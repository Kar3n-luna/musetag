"""
标签库定义 + OpenAI Function Call Schema (Gemini 兼容版)
根据文档：AI音乐曲库分类标签详细清单
"""

# 标签库定义（严格按照文档）
TAG_LIBRARY = {
    # ==================== 一、音乐风格类 ====================
    "style": {
        "primary": ["流行", "摇滚", "电子", "嘻哈/说唱", "民谣", "国风", "爵士", "蓝调", "纯音乐", "古典", "世界音乐"],
        "secondary": {
            "流行": ["华语流行", "欧美流行", "日韩流行", "港台流行", "流行摇滚", "独立流行", "情歌", "合成器流行", "OST风", "R&B", "Funk", "K-pop", "J-pop", "City-pop"],
            "摇滚": ["经典摇滚", "朋克摇滚", "金属乐", "另类摇滚", "英式摇滚", "日式摇滚", "迷幻摇滚", "前卫摇滚", "乡村摇滚", "车库摇滚"],
            "电子": ["未来贝斯", "旋律浩室", "流行电子舞曲", "浩室音乐", "科技音乐", "回响贝斯", "Trance音乐", "鼓打贝斯", "Lo-fi", "蒸汽波", "氛围电子", "迪斯科"],
            "嘻哈/说唱": ["孟菲斯说唱", "陷阱说唱", "钻头说唱", "旋律说唱", "现代另类说唱", "Boom Bap", "情绪说唱", "中国风说唱", "爵士说唱", "方言说唱", "Afro系说唱", "Jersey Club"],
            "民谣": ["城市新民谣", "当代乡村流行", "另类乡村", "跨界融合民谣", "Afro乡村"],
            "国风": ["抒情国风", "戏腔国风", "国风电子", "民谣国风", "国风摇滚", "城市国风", "少数民族风", "Afro国风"],
            "爵士": ["摇摆乐", "冷爵士", "波萨诺瓦", "融合爵士"],
            "蓝调": ["三角洲蓝调", "芝加哥蓝调", "灵魂蓝调", "德州蓝调", "新灵魂乐"],
            "纯音乐": ["钢琴独奏", "吉他独奏", "弦乐合奏", "管乐独奏", "交响乐", "乐器独奏", "电子纯音乐"],
            "古典": ["现代主义音乐", "歌剧音乐剧", "电影配乐古典", "中世纪音乐", "文艺复兴音乐", "巴洛克音乐", "古典主义音乐", "浪漫主义音乐", "印象派音乐"],
            "世界音乐": ["雷鬼", "拉丁音乐", "非洲音乐", "中东音乐", "实验音乐"]
        }
    },

    # ==================== 二、情绪类 ====================
    "emotion": {
        "primary": ["积极情绪", "中性情绪", "消极情绪"],
        "secondary": {
            "积极情绪": ["开心", "治愈", "热血激昂", "浪漫", "轻快", "活力", "明朗", "温馨", "有希望的", "家国情怀", "坚定", "自信", "深情", "释放自我", "励志"],
            "中性情绪": ["平静", "回忆", "空灵", "神秘", "孤独", "深邃", "慵懒", "释然", "诉说", "轻松", "慢摇摆", "思乡", "思念", "无奈", "遗憾", "感慨"],
            "消极情绪": ["伤感", "忧郁", "压抑", "凄美", "静谧忧伤", "自怜", "自嘲", "恐惧"]
        }
    },

    # ==================== 三、场景类 ====================
    "scene": {
        "primary": ["学习工作", "运动健身", "休闲放松", "影音游戏", "出行生活", "社交聚会", "特殊场景"],
        "secondary": {
            "学习工作": ["深度专注", "轻度办公", "图书馆", "自习室", "创意构思", "后台背景音", "会议间隙"],
            "运动健身": ["慢跑", "力量训练", "HIIT", "有氧健身", "瑜伽普拉提", "户外骑行", "徒步登山", "健身热身", "健身放松", "流行舞蹈", "拉丁舞"],
            "休闲放松": ["沉浸", "睡前助眠", "咖啡馆", "漂亮饭", "小酒馆", "下午茶", "散步", "阅读", "洗澡泡澡", "居家小酌", "居家简餐", "发呆", "深夜emo", "茶室"],
            "影音游戏": ["游戏对战", "游戏BGM", "动漫配乐", "视频剪辑", "vlog配乐", "穿搭分享"],
            "出行生活": ["白日自驾", "日落自驾", "深夜自驾", "通勤路上", "长途旅行", "户外漫游", "城市漫步", "户外露营", "购物"],
            "社交聚会": ["西餐厅", "婚礼", "庆典背景", "小型派对", "轻音乐酒会", "蹦迪", "Livehouse酒吧"],
            "特殊场景": ["独处时光", "纪念日", "季节氛围", "书房伴读", "爱国主义", "音乐剧场", "暧昧氛围"]
        }
    },

    # ==================== 四、语种类 ====================
    "language": ["华语", "粤语", "华语（其他方言）", "英语", "韩语", "日语", "俄语", "葡萄牙语", "阿拉伯语", "法语", "西班牙语", "土耳其语", "德语", "意大利语"],

    # ==================== 五、人声特征类 ====================
    "vocal": {
        "primary": ["无人声", "男声", "女声", "童声", "群声"],
        "secondary": {
            "类型": ["男声独唱", "女声独唱", "人声和声", "对唱", "乐队合唱", "童声独唱", "童声合唱", "多人合唱", "特效人声"],
            "特征": ["治愈系", "松弛", "烟嗓", "空灵", "磁性", "颗粒感", "甜美", "厚重", "清澈", "温润", "温柔", "富有张力", "穿透力强", "气声", "嘶吼", "沙哑", "反差", "快嘴", "可爱", "性感", "气泡音", "鼻音", "软绵", "呐喊", "美声唱法", "民族唱法", "流行美声唱法", "流行民族唱法", "音乐剧唱法", "呼麦", "咬字松"]
        }
    },

    # ==================== 六、特色附加类 ====================
    "extra": {
        "intensity": ["低强度（舒缓）", "中强度（适中）", "高强度（动感）", "渐变强度"],
        "era": ["70年代", "80年代", "90年代", "00年代", "10年代", "20年代（近年创作）"],
        "feature": ["小众宝藏", "短视频风格", "经典复刻", "实验性", "主流向", "氛围感", "细腻情感", "乡土气息", "爱国主义", "艺术陶冶"]
    }
}


def get_all_secondary_styles() -> list:
    """获取所有二级风格标签"""
    all_tags = []
    for tags in TAG_LIBRARY["style"]["secondary"].values():
        all_tags.extend(tags)
    return all_tags


def get_all_secondary_emotions() -> list:
    """获取所有二级情绪标签"""
    all_tags = []
    for tags in TAG_LIBRARY["emotion"]["secondary"].values():
        all_tags.extend(tags)
    return all_tags


def get_all_secondary_scenes() -> list:
    """获取所有二级场景标签"""
    all_tags = []
    for tags in TAG_LIBRARY["scene"]["secondary"].values():
        all_tags.extend(tags)
    return all_tags


def build_tag_music_tool():
    """
    构建 Function Call Schema (Gemini 兼容版)
    强制使用库内标签，不允许库外标签
    """
    return {
        "type": "function",
        "function": {
            "name": "tag_music",
            "description": "为音乐文件打上分类标签。必须从预设标签库中选择，不允许使用库外标签。",
            "parameters": {
                "type": "object",
                "properties": {
                    # ===== 一级标签（必填，部分可多选）=====
                    "style_primary": {
                        "type": "string",
                        "description": "【必填，可多选】主要音乐风格，从以下选项中选择1-3个，用逗号分隔: " + ", ".join(TAG_LIBRARY["style"]["primary"])
                    },
                    "emotion_primary": {
                        "type": "string",
                        "description": "【必填】主要情绪，必须从以下选项中选择一个: " + ", ".join(TAG_LIBRARY["emotion"]["primary"])
                    },
                    "scene_primary": {
                        "type": "string",
                        "description": "【必填，可多选】主要场景，从以下选项中选择1-3个，用逗号分隔: " + ", ".join(TAG_LIBRARY["scene"]["primary"])
                    },
                    "language": {
                        "type": "string",
                        "description": "【必填】歌曲语言，必须从以下选项中选择一个: " + ", ".join(TAG_LIBRARY["language"])
                    },
                    "vocal_primary": {
                        "type": "string",
                        "description": "【必填】人声类型，必须从以下选项中选择一个: " + ", ".join(TAG_LIBRARY["vocal"]["primary"])
                    },

                    # ===== 二级标签（可选，多选用逗号分隔）=====
                    "style_secondary": {
                        "type": "string",
                        "description": "【可选】二级风格，根据一级风格选择1-3个，用逗号分隔。可选: " + ", ".join(get_all_secondary_styles())
                    },
                    "emotion_secondary": {
                        "type": "string",
                        "description": "【可选】二级情绪，根据一级情绪选择1-3个，用逗号分隔。可选: " + ", ".join(get_all_secondary_emotions())
                    },
                    "scene_secondary": {
                        "type": "string",
                        "description": "【可选】二级场景，根据一级场景选择1-3个，用逗号分隔。可选: " + ", ".join(get_all_secondary_scenes())
                    },
                    "vocal_type": {
                        "type": "string",
                        "description": "【可选】人声演唱类型，用逗号分隔。可选: " + ", ".join(TAG_LIBRARY["vocal"]["secondary"]["类型"])
                    },
                    "vocal_traits": {
                        "type": "string",
                        "description": "【可选】人声特征，用逗号分隔。可选: " + ", ".join(TAG_LIBRARY["vocal"]["secondary"]["特征"])
                    },

                    # ===== 特色附加类 =====
                    "intensity": {
                        "type": "string",
                        "description": "【可选】音乐强度，从以下选项中选择: " + ", ".join(TAG_LIBRARY["extra"]["intensity"])
                    },
                    "era": {
                        "type": "string",
                        "description": "【可选】年代属性，从以下选项中选择: " + ", ".join(TAG_LIBRARY["extra"]["era"])
                    },
                    "feature": {
                        "type": "string",
                        "description": "【可选】特色定位，从以下选项中选择1-2个，用逗号分隔: " + ", ".join(TAG_LIBRARY["extra"]["feature"])
                    },

                    # ===== 其他信息 =====
                    "bpm_estimate": {
                        "type": "integer",
                        "description": "【可选】估计的BPM（每分钟节拍数），范围40-200"
                    },
                    "brief_description": {
                        "type": "string",
                        "description": "【可选】对音乐的简要描述（20-50字）"
                    }
                },
                "required": [
                    "style_primary",
                    "emotion_primary",
                    "scene_primary",
                    "language",
                    "vocal_primary"
                ]
            }
        }
    }


def parse_string_to_list(value: str) -> list:
    """将逗号分隔的字符串转为列表"""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def validate_tag(category: str, subcategory: str, tag: str) -> bool:
    """验证标签是否在库内"""
    if category not in TAG_LIBRARY:
        return False

    cat_data = TAG_LIBRARY[category]

    # 语言类是简单列表
    if isinstance(cat_data, list):
        return tag in cat_data

    # 其他类有 primary 和 secondary
    if subcategory == "primary":
        return tag in cat_data.get("primary", [])
    elif subcategory == "secondary":
        # 检查所有二级标签
        for tags in cat_data.get("secondary", {}).values():
            if tag in tags:
                return True
        return False

    return False
