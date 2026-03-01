# AI 前沿资讯收集 Agent

一个高度专业化的 AI 资讯代理，负责每日自动采集、筛选、摘要并推送全球人工智能领域的前沿动态到飞书群机器人。

## 功能特点

- 🔍 **多源采集**: 支持 arXiv、GitHub Trending、官方博客、顶会、科技媒体等多种数据源
- 🎯 **智能筛选**: 基于关键词、热度指标的多重筛选机制
- 🔄 **双渠道模式**: 支持单渠道（混合）和双渠道（分类）两种筛选模式
- 🔄 **自动去重**: 基于URL和内容哈希的智能去重
- 📝 **LLM摘要**: 使用智谱 AI 生成风格统一的中文摘要
- 📤 **飞书推送**: 自动推送格式化的日报到飞书群
- ⏰ **定时执行**: 每天早上9点自动运行
- ☁️ **GitHub Actions**: 支持云端定时运行，无需本地设备开机

## 项目结构

```
AI资料收集agent/
├── .github/                # GitHub Actions 配置
│   └── workflows/
│       └── daily-news.yml  # 定时任务配置
├── config/                 # 配置文件
│   ├── sources.json        # 数据源配置
│   ├── keywords.json       # 关键词配置
│   ├── thresholds.json     # 筛选阈值配置
│   └── feishu.json         # 飞书机器人配置
├── docs/                   # 文档
│   └── GITHUB_ACTIONS_GUIDE.md  # GitHub Actions 使用指南
├── src/                    # 源代码
│   ├── collectors/         # 数据源采集器
│   ├── filters/            # 过滤器
│   ├── formatter.py        # 格式化输出
│   ├── summarizer.py       # LLM摘要生成
│   ├── sender.py           # 飞书推送
│   ├── config.py           # 配置加载
│   └── storage.py          # 数据存储
├── data/                   # 数据目录
│   ├── cache/              # 缓存目录
│   └── history.db          # 历史记录
├── logs/                   # 日志目录
├── prompts/                # LLM提示词
│   ├── summarize.txt       # 摘要生成提示词
│   └── daily_report.txt    # 日报生成提示词
├── main.py                 # 主程序入口
├── requirements.txt        # 依赖包
├── .env.example            # 环境变量示例
└── README.md               # 本文件
```

## 快速开始

### 方式一：GitHub Actions（推荐，无需本地设备开机）

详细配置步骤请参考 [GitHub Actions 使用指南](docs/GITHUB_ACTIONS_GUIDE.md)

**核心步骤：**

1. 将代码推送到 GitHub 仓库
2. 在仓库 Settings → Secrets 中配置：
   - `FEISHU_WEBHOOK_URL` - 飞书 Webhook URL
   - `OPENAI_API_KEY` - 智谱 AI API Key
   - `OPENAI_BASE_URL` - `https://open.bigmodel.cn/api/paas/v4/`
   - `OPENAI_MODEL` - 如 `glm-4-flash`
3. 每天早上 9 点自动运行

### 方式二：本地运行

#### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件，填入实际的配置值
# 至少需要配置：
# - FEISHU_WEBHOOK_URL: 飞书机器人webhook地址
# - OPENAI_API_KEY: 智谱AI API密钥（用于摘要生成）
# - OPENAI_BASE_URL: 智谱AI API地址
# - OPENAI_MODEL: 模型名称（如 glm-4-flash）
```

### 3. 配置飞书机器人

在飞书群中添加自定义机器人，获取 webhook URL，填入 `.env` 文件。

### 4. 运行

```bash
# 单次运行（测试用）
python main.py --once

# 定时运行（需要保持设备开机）
python main.py
```

### 5. 配置定时任务

**Linux/Mac (cron):**
```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天9点执行）
0 9 * * * cd /path/to/AI资料收集agent && /path/to/venv/bin/python main.py
```

**Windows (任务计划程序):**
1. 打开"任务计划程序"
2. 创建基本任务
3. 设置每天9点触发
4. 操作：启动程序 `python.exe`，参数 `main.py`

## 配置说明

### 数据源配置 (config/sources.json)

定义采集的数据源及其优先级。可以启用/禁用特定数据源。

### 关键词配置 (config/keywords.json)

定义用于筛选AI资讯的关键词，按类别分组（技术、推理、应用、安全等）。

### 筛选阈值 (config/thresholds.json)

定义"重大更新"的判断标准，如：
- arXiv论文最小引用数
- GitHub最小star数
- 每日输出最大条目数
- **双渠道模式设置**: 可以启用双渠道模式，分别筛选工具类和学术/媒体类资讯

双渠道模式参数说明：
- `dual_channel_mode`: 是否启用双渠道模式（true/false）
- `tools_channel_count`: 工具渠道输出数量
- `academic_media_channel_count`: 学术媒体渠道输出数量

启用双渠道模式后，系统将：
1. 工具渠道：专门筛选GitHub项目、工具类资讯（按评分排序）
2. 学术媒体渠道：专门筛选学术论文、科技媒体、博客类资讯

### 飞书配置 (config/feishu.json)

飞书机器人推送相关配置，包括webhook地址、重试策略等。

## 输出格式

【AI前沿日报｜2026年02月06日】

🔥 今日亮点
• OpenAI 发布了 GPT-5 大语言模型，具备高级推理能力和多模态理解
• Google DeepMind 提出了新的强化学习算法，在复杂决策任务中表现优异

🧠 技术突破
• Direct Preference Optimization（加州大学伯克利分校）
无需单独的奖励模型即可完成RLHF训练，简化了对齐流程
[链接]

🏢 行业动态
• Anthropic：发布 Claude 4 API，支持1M上下文窗口
[链接]

⚖️ 政策与伦理
• 欧盟：通过《AI法案》最终版本，对高风险AI应用实施严格监管
[链接]

✅ 数据截至 2026年02月06日 | 来源：arXiv / 官方博客 / 顶会等

## 开发计划

- [ ] 完善各采集器实现
- [ ] 添加更多数据源支持
- [ ] 实现Web管理界面
- [ ] 支持自定义输出格式
- [ ] 添加多语言支持

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
