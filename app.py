"""
MuseTAG - AI 音乐打标工具
Streamlit 主应用
"""

import os
import sys
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config, reload_config
from database import get_database, init_tag_library_to_db
from tagger import create_tagger
from tags_schema import TAG_LIBRARY
from utils import scan_audio_files, get_file_hash, get_audio_duration, ensure_dir, format_duration

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ==================== 页面配置 ====================

st.set_page_config(
    page_title="MuseTAG - AI 音乐打标工具",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================== 会话状态初始化 ====================

def init_session_state():
    """初始化会话状态"""
    if "config" not in st.session_state:
        st.session_state.config = get_config()
    if "db" not in st.session_state:
        st.session_state.db = get_database()
        # 初始化标签库数据
        init_tag_library_to_db(st.session_state.db)
    if "tagger" not in st.session_state:
        try:
            st.session_state.tagger = create_tagger(st.session_state.config, st.session_state.db)
        except Exception as e:
            st.session_state.tagger = None
            logger.error(f"初始化打标器失败: {e}")


# ==================== 侧边栏导航 ====================

def render_sidebar():
    """渲染侧边栏"""
    st.sidebar.markdown("# 🎵 MuseTAG")
    st.sidebar.markdown("*AI 音乐打标工具*")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "导航",
        ["📁 导入音频", "🎵 打标面板", "📊 打标记录", "🏷️ 标签管理", "⚙️ 设置"],
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")

    # 显示统计信息
    stats = st.session_state.db.get_statistics()
    st.sidebar.markdown("### 📈 统计")
    st.sidebar.markdown(f"- 总文件: **{stats['total_files']}**")
    st.sidebar.markdown(f"- 待打标: **{stats['pending']}**")
    st.sidebar.markdown(f"- 已完成: **{stats['tagged']}**")
    st.sidebar.markdown(f"- 失败: **{stats['failed']}**")

    return page


# ==================== 导入页面 ====================

def render_import_page():
    """渲染导入页面"""
    st.markdown("## 📁 导入音频文件")

    st.markdown("""
    将音频文件导入到 MuseTAG 进行打标。支持 MP3、WAV、FLAC、M4A 等格式。
    **注意**：文件不会被复制，仅记录原始路径。
    """)

    # 方式1：输入文件夹路径
    st.markdown("### 方式一：扫描文件夹")

    col1, col2 = st.columns([3, 1])
    with col1:
        folder_path = st.text_input(
            "音频文件夹路径",
            placeholder="/path/to/your/music/folder",
            key="folder_path_input"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        scan_button = st.button("📂 扫描", type="primary", use_container_width=True)

    if scan_button and folder_path:
        if not os.path.isdir(folder_path):
            st.error(f"文件夹不存在: {folder_path}")
        else:
            with st.spinner("正在扫描音频文件..."):
                audio_files = scan_audio_files(folder_path)

                if not audio_files:
                    st.warning("未找到音频文件")
                else:
                    st.info(f"找到 {len(audio_files)} 个音频文件")

                    imported, skipped = 0, 0
                    progress_bar = st.progress(0)

                    for i, file_path in enumerate(audio_files):
                        try:
                            file_name = os.path.basename(file_path)
                            file_hash = get_file_hash(file_path)
                            duration = get_audio_duration(file_path)

                            existing = st.session_state.db.get_audio_file_by_path(file_path)
                            if existing:
                                skipped += 1
                            else:
                                st.session_state.db.add_audio_file(
                                    file_path=file_path,
                                    file_name=file_name,
                                    file_hash=file_hash,
                                    duration_seconds=duration
                                )
                                imported += 1
                        except Exception as e:
                            logger.error(f"导入文件失败 {file_path}: {e}")

                        progress_bar.progress((i + 1) / len(audio_files))

                    st.success(f"导入完成：新增 {imported} 个，跳过 {skipped} 个已存在文件")

    st.markdown("---")

    # 方式2：拖拽上传
    st.markdown("### 方式二：上传文件")

    uploaded_files = st.file_uploader(
        "上传音频文件",
        type=["mp3", "wav", "flac", "m4a", "aac", "ogg"],
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("⬆️ 导入上传的文件", type="primary"):
            upload_dir = Path("data/uploads")
            ensure_dir(str(upload_dir))

            imported = 0
            for uploaded_file in uploaded_files:
                try:
                    file_path = upload_dir / uploaded_file.name
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    file_hash = get_file_hash(str(file_path))
                    duration = get_audio_duration(str(file_path))

                    st.session_state.db.add_audio_file(
                        file_path=str(file_path),
                        file_name=uploaded_file.name,
                        file_hash=file_hash,
                        duration_seconds=duration
                    )
                    imported += 1
                except Exception as e:
                    st.error(f"导入 {uploaded_file.name} 失败: {e}")

            st.success(f"已导入 {imported} 个文件")


# ==================== 打标面板 ====================

def render_tagging_page():
    """渲染打标面板"""
    st.markdown("## 🎵 打标面板")

    if not st.session_state.config.openrouter_api_key:
        st.error("⚠️ 未配置 API Key，请先在设置页面配置")
        return

    pending_files = st.session_state.db.get_pending_files()

    if not pending_files:
        st.info("没有待打标的文件，请先在「导入音频」页面添加文件")
        return

    st.markdown(f"**待打标文件: {len(pending_files)} 个**")

    selected_files = st.multiselect(
        "选择要打标的文件",
        options=[f["id"] for f in pending_files],
        format_func=lambda x: next(
            (f"{f['file_name']}" for f in pending_files if f["id"] == x),
            str(x)
        ),
        default=[f["id"] for f in pending_files[:10]]
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🚀 开始 AI 打标", type="primary", disabled=not selected_files):
            run_tagging(selected_files, pending_files)

    # 显示已打标的文件
    st.markdown("---")
    st.markdown("### 已打标文件")

    tagged_files = st.session_state.db.get_tagged_files(limit=20)

    if not tagged_files:
        st.info("暂无已打标的文件")
        return

    for file_info in tagged_files:
        tags = st.session_state.db.get_tags(file_info["id"])
        if not tags:
            continue

        with st.expander(f"✅ {file_info['file_name']}"):
            render_tags_detail(file_info, tags)


def run_tagging(file_ids: List[int], all_files: List[Dict]):
    """执行打标"""
    progress_bar = st.progress(0)
    status_text = st.empty()

    success_count, fail_count = 0, 0
    logger.info(f"开始批量打标，共 {len(file_ids)} 个文件")

    for i, file_id in enumerate(file_ids):
        file_info = next((f for f in all_files if f["id"] == file_id), None)
        if not file_info:
            continue

        status_text.text(f"正在分析: {file_info['file_name']}...")
        logger.info(f"开始处理: {file_info['file_name']}")

        try:
            tagger = st.session_state.tagger or create_tagger(st.session_state.config, st.session_state.db)
            tags = tagger.tag(file_info["file_path"])

            st.session_state.db.save_tags(
                audio_id=file_id,
                tags=tags,
                model=st.session_state.config.model
            )

            success_count += 1
            logger.info(f"打标成功: {file_info['file_name']}")

        except Exception as e:
            fail_count += 1
            logger.error(f"打标失败: {file_info['file_name']}, {e}")
            st.session_state.db.update_file_status(file_id, "failed")

        progress_bar.progress((i + 1) / len(file_ids))

    status_text.empty()
    st.success(f"打标完成：成功 {success_count} 个，失败 {fail_count} 个")
    st.rerun()


def render_tags_detail(file_info: Dict, tags: Dict):
    """渲染标签详情"""
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📋 一级标签")
        if tags.get("style_primary"):
            if isinstance(tags["style_primary"], list):
                st.markdown(f"**风格**: {', '.join(tags['style_primary'])}")
            else:
                st.markdown(f"**风格**: {tags['style_primary']}")
        st.markdown(f"**情绪**: {tags.get('emotion_primary', '-')}")
        if tags.get("scene_primary"):
            if isinstance(tags["scene_primary"], list):
                st.markdown(f"**场景**: {', '.join(tags['scene_primary'])}")
            else:
                st.markdown(f"**场景**: {tags['scene_primary']}")
        st.markdown(f"**语言**: {tags.get('language', '-')}")
        st.markdown(f"**人声**: {tags.get('vocal_primary', '-')}")
        st.markdown(f"**强度**: {tags.get('intensity', '-')}")

    with col2:
        st.markdown("#### 📝 二级标签")
        if tags.get("style_secondary"):
            st.markdown(f"**风格**: {', '.join(tags['style_secondary'])}")
        if tags.get("emotion_secondary"):
            st.markdown(f"**情绪**: {', '.join(tags['emotion_secondary'])}")
        if tags.get("scene_secondary"):
            st.markdown(f"**场景**: {', '.join(tags['scene_secondary'])}")
        if tags.get("vocal_type"):
            st.markdown(f"**演唱类型**: {', '.join(tags['vocal_type'])}")
        if tags.get("vocal_traits"):
            st.markdown(f"**人声特征**: {', '.join(tags['vocal_traits'])}")
        if tags.get("era"):
            st.markdown(f"**年代**: {tags['era']}")
        if tags.get("feature"):
            st.markdown(f"**特色**: {', '.join(tags['feature'])}")
        if tags.get("bpm_estimate"):
            st.markdown(f"**BPM**: {tags['bpm_estimate']}")

        if tags.get("brief_description"):
            st.markdown(f"**描述**: {tags['brief_description']}")


# ==================== 打标记录页面 ====================

def render_records_page():
    """渲染打标记录页面"""
    st.markdown("## 📊 打标记录")

    # 检查是否需要刷新（删除后）
    if st.session_state.get("refresh_records"):
        st.session_state.refresh_records = False
        st.rerun()

    all_tags = st.session_state.db.get_all_tags()

    if not all_tags:
        st.info("暂无打标记录")
        return

    col1, col2 = st.columns([1, 3])
    with col1:
        search_term = st.text_input("搜索文件名", "")
    with col2:
        if st.button("📥 导出 CSV", type="primary"):
            export_to_csv(all_tags)

    filtered_tags = all_tags
    if search_term:
        filtered_tags = [t for t in filtered_tags if search_term.lower() in t.get("file_name", "").lower()]

    st.markdown(f"**共 {len(filtered_tags)} 条记录**")

    for record in filtered_tags[:100]:
        audio_id = record.get("audio_id")
        file_name = record.get("file_name", "Unknown")

        with st.expander(f"✅ {file_name}"):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                if record.get("style_primary"):
                    if isinstance(record["style_primary"], list):
                        st.markdown(f"**风格**: {', '.join(record['style_primary'])}")
                    else:
                        st.markdown(f"**风格**: {record['style_primary']}")
                else:
                    st.markdown("**风格**: -")
                st.markdown(f"**情绪**: {record.get('emotion_primary', '-')}")
                if record.get("scene_primary"):
                    if isinstance(record["scene_primary"], list):
                        st.markdown(f"**场景**: {', '.join(record['scene_primary'])}")
                    else:
                        st.markdown(f"**场景**: {record['scene_primary']}")
                else:
                    st.markdown("**场景**: -")
                st.markdown(f"**语言**: {record.get('language', '-')}")
                st.markdown(f"**人声**: {record.get('vocal_primary', '-')}")

            with col2:
                if record.get("style_secondary"):
                    st.markdown(f"**二级风格**: {', '.join(record['style_secondary'])}")
                if record.get("emotion_secondary"):
                    st.markdown(f"**二级情绪**: {', '.join(record['emotion_secondary'])}")
                if record.get("scene_secondary"):
                    st.markdown(f"**二级场景**: {', '.join(record['scene_secondary'])}")
                if record.get("bpm_estimate"):
                    st.markdown(f"**BPM**: {record['bpm_estimate']}")
                if record.get("brief_description"):
                    st.markdown(f"**描述**: {record['brief_description']}")

            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ 删除", key=f"del_record_{audio_id}"):
                    st.session_state.db.delete_audio_file(audio_id)
                    st.session_state.refresh_records = True
                    st.success("已删除")


def export_to_csv(records: List[Dict]):
    """导出为 CSV - 4列：文件名、一级标签、二级标签、备注"""
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    headers = ["文件名", "一级标签", "二级标签", "备注"]
    writer.writerow(headers)

    for record in records:
        # 备注使用描述
        note = record.get("brief_description", "")

        # 一级标签（直接输出值，用逗号分隔）
        primary_tags = []
        if record.get("style_primary"):
            if isinstance(record["style_primary"], list):
                primary_tags.extend(record["style_primary"])
            else:
                primary_tags.append(record["style_primary"])
        if record.get("emotion_primary"):
            primary_tags.append(record["emotion_primary"])
        if record.get("scene_primary"):
            if isinstance(record["scene_primary"], list):
                primary_tags.extend(record["scene_primary"])
            else:
                primary_tags.append(record["scene_primary"])
        if record.get("language"):
            primary_tags.append(record["language"])
        if record.get("vocal_primary"):
            primary_tags.append(record["vocal_primary"])

        # 二级标签（直接输出值，用逗号分隔）
        secondary_tags = []
        if record.get("style_secondary"):
            secondary_tags.extend(record["style_secondary"])
        if record.get("emotion_secondary"):
            secondary_tags.extend(record["emotion_secondary"])
        if record.get("scene_secondary"):
            secondary_tags.extend(record["scene_secondary"])
        if record.get("vocal_type"):
            secondary_tags.extend(record["vocal_type"])
        if record.get("vocal_traits"):
            secondary_tags.extend(record["vocal_traits"])
        if record.get("era"):
            secondary_tags.append(record["era"])
        if record.get("intensity"):
            secondary_tags.append(record["intensity"])
        if record.get("feature"):
            secondary_tags.extend(record["feature"])
        if record.get("bpm_estimate"):
            secondary_tags.append(f"BPM:{record['bpm_estimate']}")

        writer.writerow([
            record.get("file_name", ""),
            ", ".join(primary_tags),
            ", ".join(secondary_tags),
            note
        ])

    csv_data = output.getvalue()
    st.download_button(
        label="📥 下载 CSV",
        data=csv_data,
        file_name=f"musetag_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


# ==================== 标签管理页面 ====================

def render_tag_management_page():
    """渲染标签管理页面"""
    st.markdown("## 🏷️ 标签管理")

    st.markdown("管理 AI 打标使用的标签库。修改后，下次 AI 调用时将使用最新的标签库。")

    db = st.session_state.db

    # 获取标签库统计
    all_tags = db.get_all_tags_for_display()

    # 按分类统计
    category_counts = {}
    for tag in all_tags:
        cat = tag["category"]
        if cat not in category_counts:
            category_counts[cat] = 0
        category_counts[cat] += 1

    # 显示统计
    st.markdown("### 📊 标签统计")
    cols = st.columns(6)
    categories = ["style", "emotion", "scene", "language", "vocal", "extra"]
    category_names = {
        "style": "风格", "emotion": "情绪", "scene": "场景",
        "language": "语言", "vocal": "人声", "extra": "特色"
    }
    for i, cat in enumerate(categories):
        with cols[i]:
            st.metric(category_names.get(cat, cat), category_counts.get(cat, 0))

    st.markdown("---")

    # 标签管理标签页
    tab1, tab2, tab3 = st.tabs(["查看标签", "添加标签", "编辑/删除标签"])

    with tab1:
        render_view_tags(db)

    with tab2:
        render_add_tag(db)

    with tab3:
        render_edit_delete_tag(db, all_tags)


def render_view_tags(db):
    """查看标签"""
    tag_library = db.get_full_tag_library()

    view_tabs = st.tabs(["风格", "情绪", "场景", "语言/人声", "特色附加"])

    with view_tabs[0]:
        st.markdown("### 一级风格")
        cols = st.columns(4)
        for i, style in enumerate(tag_library["style"]["primary"]):
            cols[i % 4].markdown(f"- {style}")

        st.markdown("### 二级风格")
        for primary, secondary_list in tag_library["style"]["secondary"].items():
            with st.expander(f"**{primary}**"):
                cols = st.columns(4)
                for i, sec in enumerate(secondary_list):
                    cols[i % 4].markdown(f"- {sec}")

    with view_tabs[1]:
        st.markdown("### 一级情绪")
        cols = st.columns(3)
        for i, emotion in enumerate(tag_library["emotion"]["primary"]):
            cols[i].markdown(f"- {emotion}")

        st.markdown("### 二级情绪")
        for primary, secondary_list in tag_library["emotion"]["secondary"].items():
            with st.expander(f"**{primary}**"):
                cols = st.columns(4)
                for i, sec in enumerate(secondary_list):
                    cols[i % 4].markdown(f"- {sec}")

    with view_tabs[2]:
        st.markdown("### 一级场景")
        cols = st.columns(4)
        for i, scene in enumerate(tag_library["scene"]["primary"]):
            cols[i % 4].markdown(f"- {scene}")

        st.markdown("### 二级场景")
        for primary, secondary_list in tag_library["scene"]["secondary"].items():
            with st.expander(f"**{primary}**"):
                cols = st.columns(4)
                for i, sec in enumerate(secondary_list):
                    cols[i % 4].markdown(f"- {sec}")

    with view_tabs[3]:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 语言")
            for lang in tag_library["language"]:
                st.markdown(f"- {lang}")

        with col2:
            st.markdown("### 人声类型（一级）")
            for vocal in tag_library["vocal"]["primary"]:
                st.markdown(f"- {vocal}")

            st.markdown("### 人声特征（二级）")
            cols = st.columns(3)
            for parent, traits in tag_library["vocal"]["secondary"].items():
                for i, trait in enumerate(traits):
                    cols[i % 3].markdown(f"- {trait}")

    with view_tabs[4]:
        col1, col2, col3 = st.columns(3)

        extra_secondary = tag_library["extra"].get("secondary", {})

        with col1:
            st.markdown("### 强度（二级标签）")
            for intensity in extra_secondary.get("强度", []):
                st.markdown(f"- {intensity}")

        with col2:
            st.markdown("### 年代（二级标签）")
            for era in extra_secondary.get("年代", []):
                st.markdown(f"- {era}")

        with col3:
            st.markdown("### 特色定位（二级标签）")
            for feature in extra_secondary.get("特色", []):
                st.markdown(f"- {feature}")

        # 编曲配器混音单独一行
        st.markdown("---")
        st.markdown("### 编曲、配器、混音特色（二级标签）")
        arrangement_tags = extra_secondary.get("编曲配器混音", [])
        cols = st.columns(4)
        for i, tag in enumerate(arrangement_tags):
            cols[i % 4].markdown(f"- {tag}")


def render_add_tag(db):
    """添加标签"""
    st.markdown("### 添加新标签")

    col1, col2, col3 = st.columns(3)

    with col1:
        category = st.selectbox(
            "分类",
            options=["style", "emotion", "scene", "language", "vocal", "extra"],
            format_func=lambda x: {
                "style": "风格", "emotion": "情绪", "scene": "场景",
                "language": "语言", "vocal": "人声", "extra": "特色附加"
            }.get(x, x)
        )

    with col2:
        level = st.selectbox(
            "级别",
            options=["primary", "secondary"],
            format_func=lambda x: "一级" if x == "primary" else "二级"
        )

    # 根据分类和级别动态获取父级选项
    parent_options = [""]
    if level == "secondary":
        tag_library = db.get_full_tag_library()
        if category in ["style", "emotion", "scene"]:
            parent_options.extend(tag_library[category]["primary"])
        elif category == "vocal":
            parent_options.extend(["类型", "特征"])

    with col3:
        if level == "secondary":
            parent = st.selectbox("父级标签", options=parent_options)
        else:
            parent = ""

    tag_name = st.text_input("标签名称", placeholder="输入标签名称")
    tag_description = st.text_area("标签描述（可选）", placeholder="输入标签的说明或描述")

    if st.button("➕ 添加标签", type="primary"):
        if not tag_name:
            st.error("请输入标签名称")
        elif level == "secondary" and not parent:
            st.error("二级标签必须选择父级标签")
        else:
            try:
                db.add_tag(
                    category=category,
                    level=level,
                    name=tag_name,
                    parent=parent if parent else None,
                    description=tag_description if tag_description else None
                )
                st.success(f"标签「{tag_name}」添加成功！")
                st.rerun()
            except Exception as e:
                st.error(f"添加失败: {e}")


def render_edit_delete_tag(db, all_tags):
    """编辑/删除标签"""
    st.markdown("### 编辑或删除标签")

    # 筛选选项
    col1, col2 = st.columns(2)
    with col1:
        filter_category = st.selectbox(
            "筛选分类",
            options=["全部", "style", "emotion", "scene", "language", "vocal", "extra"],
            format_func=lambda x: {
                "全部": "全部", "style": "风格", "emotion": "情绪", "scene": "场景",
                "language": "语言", "vocal": "人声", "extra": "特色附加"
            }.get(x, x)
        )
    with col2:
        search_term = st.text_input("搜索标签", placeholder="输入关键词")

    # 筛选标签
    filtered_tags = all_tags
    if filter_category != "全部":
        filtered_tags = [t for t in filtered_tags if t["category"] == filter_category]
    if search_term:
        filtered_tags = [t for t in filtered_tags if search_term.lower() in t["name"].lower()]

    st.markdown(f"**共 {len(filtered_tags)} 个标签**")

    # 显示标签列表
    for tag in filtered_tags[:50]:  # 限制显示数量
        with st.expander(f"{'📁' if tag['level'] == 'primary' else '📄'} {tag['name']} ({tag['category']}/{tag['level']})"):
            col1, col2, col3 = st.columns([2, 2, 1])

            with col1:
                new_name = st.text_input("名称", value=tag["name"], key=f"name_{tag['id']}")
            with col2:
                new_desc = st.text_input("描述", value=tag["description"] or "", key=f"desc_{tag['id']}")
            with col3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("💾 保存", key=f"save_{tag['id']}"):
                    try:
                        db.update_tag(tag["id"], name=new_name, description=new_desc if new_desc else None)
                        st.success("保存成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存失败: {e}")

                if st.button("🗑️ 删除", key=f"del_{tag['id']}"):
                    try:
                        db.delete_tag(tag["id"])
                        st.success("删除成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败: {e}")


# ==================== 设置页面 ====================

def render_settings_page():
    """渲染设置页面"""
    st.markdown("## ⚙️ 设置")

    st.markdown("### API 配置")

    current_key = st.session_state.config.openrouter_api_key
    masked_key = f"{current_key[:8]}...{current_key[-4:]}" if len(current_key) > 12 else "未设置"

    st.markdown(f"**当前 API Key**: `{masked_key}`")
    st.markdown(f"**当前模型**: `{st.session_state.config.model}`")

    new_key = st.text_input("更新 API Key", type="password", placeholder="输入新的 OpenRouter API Key")

    if st.button("保存 API Key", type="primary"):
        if new_key:
            env_file = Path(__file__).parent / ".env"
            with open(env_file, "w") as f:
                f.write(f"OPENROUTER_API_KEY={new_key}\n")

            st.session_state.config = reload_config()
            st.session_state.tagger = create_tagger(st.session_state.config, st.session_state.db)
            st.success("API Key 已更新")

    st.markdown("---")
    st.markdown("### 测试连接")

    if st.button("🔍 测试 API 连接"):
        with st.spinner("正在测试..."):
            tagger = st.session_state.tagger or create_tagger(st.session_state.config, st.session_state.db)
            if tagger.test_connection():
                st.success("✅ API 连接正常")
            else:
                st.error("❌ API 连接失败，请检查 API Key")

    st.markdown("---")
    st.markdown("### 数据库操作")

    stats = st.session_state.db.get_statistics()
    st.markdown(f"**总记录数**: {stats['total_files']} 条")
    st.markdown(f"**标签库数量**: {st.session_state.db.count_tags()} 个")

    st.markdown("#### 重新初始化标签库")
    st.markdown("从代码同步最新的标签库到数据库（不会影响已打标的数据）")
    if st.button("🔄 重新初始化标签库", type="secondary"):
        from database import init_tag_library_to_db
        init_tag_library_to_db(st.session_state.db, force=True)
        st.success(f"标签库已更新，共 {st.session_state.db.count_tags()} 个标签")
        st.rerun()

    st.markdown("#### 清空所有数据")
    confirm_clear = st.checkbox("确认清空所有数据（不可恢复）")
    if st.button("🗑️ 清空所有数据", type="secondary", disabled=not confirm_clear):
        db = st.session_state.db
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tags")
            cursor.execute("DELETE FROM audio_files")
            conn.commit()
        st.success("数据已清空")
        st.rerun()


# ==================== 主函数 ====================

def main():
    """主函数"""
    init_session_state()
    page = render_sidebar()

    if page == "📁 导入音频":
        render_import_page()
    elif page == "🎵 打标面板":
        render_tagging_page()
    elif page == "📊 打标记录":
        render_records_page()
    elif page == "🏷️ 标签管理":
        render_tag_management_page()
    elif page == "⚙️ 设置":
        render_settings_page()


if __name__ == "__main__":
    main()
