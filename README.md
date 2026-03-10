# MuseTAG - AI 音乐自动打标工具

基于 AI 的音乐文件自动打标工具，支持批量处理音频文件并生成结构化标签。

## 功能特点

- 🎵 **智能打标**：自动分析音乐风格、情绪、场景、语言、人声特征等
- 📊 **品质评估**：按 2026 版标准评估音乐品质（低/中/高）
- 🏷️ **标签管理**：可视化标签库管理，支持增删改查
- 📁 **批量处理**：支持批量上传和打标
- 📤 **CSV 导出**：一键导出打标结果

## 安装

### 1. 安装系统依赖

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

### 2. 克隆项目

```bash
git clone https://github.com/Kar3n-luna/musetag.git
cd musetag
```

### 3. 创建虚拟环境（推荐）

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows
```

### 4. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 5. 配置 API Key

创建 `.env` 文件：

```bash
echo "OPENROUTER_API_KEY=你的OpenRouter API密钥" > .env
```

> 获取 API Key: https://openrouter.ai/

## 使用

### 启动应用

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`

### 首次运行

1. 进入 **⚙️ 设置** → 点击 **🔄 重新初始化标签库**
2. 配置你的 OpenRouter API Key
3. 测试 API 连接是否正常

### 打标流程

1. **📁 导入音频**：上传 MP3/WAV/M4A 等格式音频
2. **🎵 打标面板**：选择文件进行 AI 打标
3. **📊 打标记录**：查看、编辑、导出打标结果

## 标签体系（2026 版）

| 分类 | 说明 |
|------|------|
| 风格 | 流行、摇滚、电子、嘻哈等 11 个一级分类 |
| 情绪 | 积极、中性、消极情绪及细分 |
| 场景 | 学习工作、运动健身、休闲放松等 7 大场景 |
| 语言 | 华语、英语、日语等 14 种语言 |
| 人声 | 无人声、男声、女声及音色特征 |
| 特色附加 | 强度、年代、特色定位、编曲配器混音 |
| 品质 | 低品质、中品质、高品质 |

## 技术栈

- **前端**：Streamlit
- **后端**：Python 3.9+
- **数据库**：SQLite
- **AI**：OpenRouter API (支持多种 LLM)

## License

MIT
