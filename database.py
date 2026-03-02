"""
SQLite 数据库操作模块
"""

import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """数据库管理类"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_tables()

    def _ensure_db_dir(self):
        """确保数据库目录存在"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    def _init_tables(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 音频文件表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audio_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    file_name TEXT NOT NULL,
                    file_hash TEXT,
                    duration_seconds REAL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 打标记录表（新结构）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    audio_id INTEGER REFERENCES audio_files(id),

                    -- 一级标签（必填）
                    style_primary TEXT,
                    emotion_primary TEXT,
                    scene_primary TEXT,
                    language TEXT,
                    vocal_primary TEXT,

                    -- 二级标签（可选）
                    style_secondary TEXT,
                    emotion_secondary TEXT,
                    scene_secondary TEXT,
                    vocal_type TEXT,
                    vocal_traits TEXT,

                    -- 特色附加
                    intensity TEXT,
                    era TEXT,
                    feature TEXT,

                    -- 其他信息
                    bpm_estimate INTEGER,
                    brief_description TEXT,

                    -- 元数据
                    model_used TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            logger.info("数据库表初始化完成")

    @contextmanager
    def _get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # ==================== 音频文件操作 ====================

    def add_audio_file(
        self,
        file_path: str,
        file_name: str,
        file_hash: Optional[str] = None,
        duration_seconds: Optional[float] = None
    ) -> int:
        """添加音频文件记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO audio_files (file_path, file_name, file_hash, duration_seconds)
                    VALUES (?, ?, ?, ?)
                """, (file_path, file_name, file_hash, duration_seconds))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                cursor.execute("""
                    UPDATE audio_files
                    SET file_hash = ?, duration_seconds = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE file_path = ?
                """, (file_hash, duration_seconds, file_path))
                conn.commit()
                cursor.execute("SELECT id FROM audio_files WHERE file_path = ?", (file_path,))
                return cursor.fetchone()["id"]

    def get_audio_file(self, file_id: int) -> Optional[Dict[str, Any]]:
        """获取音频文件信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audio_files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_audio_file_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """通过路径获取音频文件信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audio_files WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_pending_files(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取待打标的文件列表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM audio_files WHERE status = 'pending' ORDER BY created_at"
            if limit:
                query += f" LIMIT {limit}"
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def get_tagged_files(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取已打标的文件列表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM audio_files WHERE status = 'tagged' ORDER BY updated_at DESC"
            if limit:
                query += f" LIMIT {limit}"
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def get_all_files(self) -> List[Dict[str, Any]]:
        """获取所有文件列表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audio_files ORDER BY created_at")
            return [dict(row) for row in cursor.fetchall()]

    def update_file_status(self, file_id: int, status: str):
        """更新文件状态"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE audio_files
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, file_id))
            conn.commit()

    def delete_audio_file(self, file_id: int):
        """删除音频文件记录（及其标签）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tags WHERE audio_id = ?", (file_id,))
            cursor.execute("DELETE FROM audio_files WHERE id = ?", (file_id,))
            conn.commit()

    def get_file_count_by_status(self) -> Dict[str, int]:
        """获取各状态的文件数量"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM audio_files
                GROUP BY status
            """)
            return {row["status"]: row["count"] for row in cursor.fetchall()}

    # ==================== 标签操作 ====================

    def save_tags(self, audio_id: int, tags: Dict[str, Any], model: str = ""):
        """保存标签"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 先删除旧标签
            cursor.execute("DELETE FROM tags WHERE audio_id = ?", (audio_id,))

            # JSON 数组字段处理
            def to_json(value):
                if isinstance(value, list):
                    return json.dumps(value, ensure_ascii=False)
                return value

            # 处理 style_primary 和 scene_primary 为列表
            style_primary = tags.get("style_primary")
            if isinstance(style_primary, list):
                style_primary = json.dumps(style_primary, ensure_ascii=False)

            scene_primary = tags.get("scene_primary")
            if isinstance(scene_primary, list):
                scene_primary = json.dumps(scene_primary, ensure_ascii=False)

            cursor.execute("""
                INSERT INTO tags (
                    audio_id,
                    style_primary, style_secondary,
                    emotion_primary, emotion_secondary,
                    scene_primary, scene_secondary,
                    language,
                    vocal_primary, vocal_type, vocal_traits,
                    intensity, era, feature,
                    bpm_estimate, brief_description,
                    model_used
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audio_id,
                style_primary,
                to_json(tags.get("style_secondary")),
                tags.get("emotion_primary"),
                to_json(tags.get("emotion_secondary")),
                scene_primary,
                to_json(tags.get("scene_secondary")),
                tags.get("language"),
                tags.get("vocal_primary"),
                to_json(tags.get("vocal_type")),
                to_json(tags.get("vocal_traits")),
                tags.get("intensity"),
                tags.get("era"),
                to_json(tags.get("feature")),
                tags.get("bpm_estimate"),
                tags.get("brief_description"),
                model
            ))
            conn.commit()

            # 更新文件状态
            self.update_file_status(audio_id, "tagged")

    def get_tags(self, audio_id: int) -> Optional[Dict[str, Any]]:
        """获取文件的标签"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tags WHERE audio_id = ?", (audio_id,))
            row = cursor.fetchone()
            if not row:
                return None

            tags = dict(row)

            # 解析 JSON 字段
            json_fields = ["style_primary", "style_secondary", "scene_primary", "scene_secondary", "emotion_secondary", "vocal_type", "vocal_traits", "feature"]
            for field in json_fields:
                if tags.get(field):
                    try:
                        tags[field] = json.loads(tags[field])
                    except json.JSONDecodeError:
                        tags[field] = []

            return tags

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """获取所有标签记录（用于导出）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    af.file_path,
                    af.file_name,
                    af.duration_seconds,
                    t.*
                FROM audio_files af
                JOIN tags t ON af.id = t.audio_id
                ORDER BY t.created_at DESC
            """)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                item = dict(row)
                # 解析 JSON 字段
                json_fields = ["style_primary", "style_secondary", "scene_primary", "scene_secondary", "emotion_secondary", "vocal_type", "vocal_traits", "feature"]
                for field in json_fields:
                    if item.get(field):
                        try:
                            item[field] = json.loads(item[field])
                        except json.JSONDecodeError:
                            item[field] = []
                results.append(item)

            return results

    # ==================== 统计信息 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as total FROM audio_files")
            total_files = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as count FROM audio_files WHERE status = 'pending'")
            pending = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM audio_files WHERE status = 'tagged'")
            tagged = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM audio_files WHERE status = 'failed'")
            failed = cursor.fetchone()["count"]

            return {
                "total_files": total_files,
                "pending": pending,
                "tagged": tagged,
                "failed": failed
            }


# 全局数据库实例
_db: Optional[Database] = None


def get_database(db_path: str = None) -> Database:
    """获取数据库实例"""
    global _db
    if _db is None:
        if db_path is None:
            from config import get_config
            db_path = get_config().database_path
        _db = Database(db_path)
    return _db


def init_db(db_path: str = None) -> Database:
    """初始化数据库"""
    return get_database(db_path)
