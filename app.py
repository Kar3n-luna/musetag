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
from database import get_database
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
    if "tagger" not in st.session_state:
        try:
            st.session_state.tagger = create_tagger(st.session_state.config)
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
        ["📁 导入音频", "🎵 打标面板", "📊 打标记录", "🏷️ 标签库", "⚙️ 设置"],
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
            tagger = st.session_state.tagger or create_tagger(st.session_state.config)
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
        with st.expander(f"✅ {record.get('file_name', 'Unknown')}"):
            col1, col2 = st.columns(2)

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


def export_to_csv(records: List[Dict]):
    """导出为 CSV - 4列：文件名、一级标签、二级标签、备注"""
    import io

    output = io.StringIO()
    writer = csv.writer(output)

    headers = ["文件名", "一级标签", "二级标签", "备注"]
    writer.writerow(headers)

    for record in records:
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
        if record.get("intensity"):
            primary_tags.append(record["intensity"])

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
        if record.get("feature"):
            secondary_tags.extend(record["feature"])
        if record.get("bpm_estimate"):
            secondary_tags.append(f"BPM:{record['bpm_estimate']}")

        writer.writerow([
            record.get("file_name", ""),
            ", ".join(primary_tags),
            ", ".join(secondary_tags),
            record.get("brief_description", "")
        ])

    csv_data = output.getvalue()
    st.download_button(
        label="📥 下载 CSV",
        data=csv_data,
        file_name=f"musetag_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


# ==================== 标签库页面 ====================

def render_tags_library_page():
    """渲染标签库页面"""
    st.markdown("## 🏷️ 标签库")

    st.markdown("AI 打标时必须从以下标签库中选择。")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["风格", "情绪", "场景", "语言/人声", "特色附加"])

    with tab1:
        st.markdown("### 一级风格")
        cols = st.columns(4)
        for i, style in enumerate(TAG_LIBRARY["style"]["primary"]):
            cols[i % 4].markdown(f"- {style}")

        st.markdown("### 二级风格")
        for primary, secondary_list in TAG_LIBRARY["style"]["secondary"].items():
            with st.expander(f"**{primary}**"):
                cols = st.columns(4)
                for i, sec in enumerate(secondary_list):
                    cols[i % 4].markdown(f"- {sec}")

    with tab2:
        st.markdown("### 一级情绪")
        cols = st.columns(3)
        for i, emotion in enumerate(TAG_LIBRARY["emotion"]["primary"]):
            cols[i].markdown(f"- {emotion}")

        st.markdown("### 二级情绪")
        for primary, secondary_list in TAG_LIBRARY["emotion"]["secondary"].items():
            with st.expander(f"**{primary}**"):
                cols = st.columns(4)
                for i, sec in enumerate(secondary_list):
                    cols[i % 4].markdown(f"- {sec}")

    with tab3:
        st.markdown("### 一级场景")
        cols = st.columns(4)
        for i, scene in enumerate(TAG_LIBRARY["scene"]["primary"]):
            cols[i % 4].markdown(f"- {scene}")

        st.markdown("### 二级场景")
        for primary, secondary_list in TAG_LIBRARY["scene"]["secondary"].items():
            with st.expander(f"**{primary}**"):
                cols = st.columns(4)
                for i, sec in enumerate(secondary_list):
                    cols[i % 4].markdown(f"- {sec}")

    with tab4:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 语言")
            for lang in TAG_LIBRARY["language"]:
                st.markdown(f"- {lang}")

        with col2:
            st.markdown("### 人声类型（一级）")
            for vocal in TAG_LIBRARY["vocal"]["primary"]:
                st.markdown(f"- {vocal}")

            st.markdown("### 人声特征（二级）")
            cols = st.columns(3)
            for i, trait in enumerate(TAG_LIBRARY["vocal"]["secondary"]["特征"]):
                cols[i % 3].markdown(f"- {trait}")

    with tab5:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("### 强度")
            for intensity in TAG_LIBRARY["extra"]["intensity"]:
                st.markdown(f"- {intensity}")

        with col2:
            st.markdown("### 年代")
            for era in TAG_LIBRARY["extra"]["era"]:
                st.markdown(f"- {era}")

        with col3:
            st.markdown("### 特色")
            for feature in TAG_LIBRARY["extra"]["feature"]:
                st.markdown(f"- {feature}")


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
            st.session_state.tagger = create_tagger(st.session_state.config)
            st.success("API Key 已更新")

    st.markdown("---")
    st.markdown("### 测试连接")

    if st.button("🔍 测试 API 连接"):
        with st.spinner("正在测试..."):
            tagger = st.session_state.tagger or create_tagger(st.session_state.config)
            if tagger.test_connection():
                st.success("✅ API 连接正常")
            else:
                st.error("❌ API 连接失败，请检查 API Key")

    st.markdown("---")
    st.markdown("### 数据库操作")

    stats = st.session_state.db.get_statistics()
    st.markdown(f"**总记录数**: {stats['total_files']} 条")

    if st.button("🗑️ 清空所有数据", type="secondary"):
        if st.checkbox("确认清空所有数据（不可恢复）"):
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
    elif page == "🏷️ 标签库":
        render_tags_library_page()
    elif page == "⚙️ 设置":
        render_settings_page()


if __name__ == "__main__":
    main()
