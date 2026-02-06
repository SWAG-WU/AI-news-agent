# GitHub Actions 使用指南

本项目使用 GitHub Actions 实现每天早上 9 点自动采集 AI 资讯并推送到飞书。

---

## 一、配置 Secrets

### 1. 进入 Secrets 配置页面

仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

### 2. 必需配置项

| Secret 名称 | 说明 | 获取方式 |
|------------|------|---------|
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook URL | 飞书群 → 群设置 → 群机器人 → 添加机器人 → 自定义机器人 |
| `OPENAI_API_KEY` | 智谱 AI API Key | [智谱 AI 开放平台](https://open.bigmodel.cn/) |
| `OPENAI_BASE_URL` | 智谱 AI API 地址 | `https://open.bigmodel.cn/api/paas/v4/` |
| `OPENAI_MODEL` | 模型名称 | 如 `glm-4-flash` |

### 3. 可选配置项

| Secret 名称 | 说明 | 默认值 |
|------------|------|-------|
| `FEISHU_WEBHOOK_SECRET` | 飞书签名验证密钥（增强安全性） | 空 |
| `GITHUB_TOKEN` | GitHub Token（提高 GitHub API 请求限额） | 空 |

---

## 二、获取配置信息

### 飞书 Webhook URL

1. 打开飞书群
2. 点击右上角 **...** → **群设置** → **群机器人**
3. 点击 **添加机器人** → **自定义机器人**
4. 设置机器人名称和头像
5. 复制 **Webhook URL**（格式：`https://open.feishu.cn/open-apis/bot/v2/hook/...`）

### 智谱 AI API Key

1. 访问 [智谱 AI 开放平台](https://open.bigmodel.cn/)
2. 注册/登录账号
3. 进入 **API Key** 页面
4. 创建新的 API Key 并复制

---

## 三、运行方式

### 1. 定时运行（自动）

GitHub Actions 每天北京时间 **9:00** 自动运行，无需手动操作。

### 2. 手动触发（测试）

1. 进入仓库 **Actions** 页面
2. 选择 **AI Daily News Collector** workflow
3. 点击右侧 **Run workflow** 按钮
4. 选择分支，点击 **Run workflow**

---

## 四、查看运行日志

### 1. 查看 workflow 运行日志

1. 进入仓库 **Actions** 页面
2. 点击具体的运行记录
3. 展开 **运行 AI 资讯收集** 步骤查看详细日志

### 2. 下载日志文件

每次运行后，日志文件会上传为 **Artifact**：

1. 进入具体的 workflow 运行记录
2. 滚动到底部 **Artifacts** 区域
3. 下载 `logs-{序号}` 文件

### 3. 日志保留时间

| 文件类型 | 保留时间 |
|---------|---------|
| 日志文件 | 7 天 |
| 数据库文件 | 30 天 |

---

## 五、常见问题

### Q1: workflow 运行失败怎么办？

1. 查看 **Actions** 页面的错误日志
2. 检查 Secrets 是否配置正确
3. 尝试手动触发 workflow 进行调试

### Q2: 如何修改运行时间？

编辑 `.github/workflows/daily-news.yml`，修改 cron 表达式：

```yaml
schedule:
  - cron: '0 1 * * *'  # UTC 时间，需换算成北京时间
```

| 北京时间 | UTC 时间 | Cron 表达式 |
|---------|---------|------------|
| 8:00 | 0:00 | `0 0 * * *` |
| 9:00 | 1:00 | `0 1 * * *` |
| 10:00 | 2:00 | `0 2 * * *` |

### Q3: 飞书收不到消息？

1. 检查 `FEISHU_WEBHOOK_URL` 是否正确
2. 查看日志确认推送是否成功
3. 确认飞书机器人是否被禁用

### Q4: API 调用失败？

1. 检查 `OPENAI_API_KEY` 和 `OPENAI_BASE_URL` 是否正确
2. 确认智谱 AI 账户余额是否充足
3. 查看日志中的具体错误信息

---

## 六、本地测试

在推送到 GitHub 之前，可以本地测试：

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 .env 文件（复制 .env.example）
cp .env.example .env
# 编辑 .env，填入真实的配置

# 单次运行测试
python main.py --once
```

---

## 七、配置示例

### .env 文件示例

```env
# 飞书配置
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
FEISHU_WEBHOOK_SECRET=

# 智谱 AI 配置
OPENAI_API_KEY=your_zhipu_api_key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
OPENAI_MODEL=glm-4-flash

# GitHub 配置（可选）
GITHUB_TOKEN=ghp_xxx

# 其他配置
TZ=Asia/Shanghai
LOG_LEVEL=INFO
```
