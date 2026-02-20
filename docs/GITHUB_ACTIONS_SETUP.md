# GitHub Actions 部署指南

本指南说明如何将 AI 资讯采集器部署到 GitHub Actions，实现每天自动采集。

## 为什么使用 GitHub Actions？

- ✅ **免费**：GitHub Actions 公开仓库免费使用
- ✅ **24/7 运行**：不依赖本地电脑
- ✅ **无需代理**：GitHub 服务器在国外，直接访问国外网站
- ✅ **自动定时**：每天早上9点自动运行

## 部署步骤

### 1. 推送代码到 GitHub

```bash
cd E:\作品集\AI项目\AI资料收集agent
git add .
git commit -m "feat: add GitHub Actions workflow"
git push
```

### 2. 配置 GitHub Secrets

在 GitHub 仓库中配置敏感信息：

1. 打开仓库页面
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret** 添加以下密钥：

| Secret 名称 | 值 | 说明 |
|------------|-----|------|
| `FEISHU_WEBHOOK_URL` | 你的飞书 Webhook URL | 必填 |
| `FEISHU_WEBHOOK_SECRET` | 飞书 Webhook 密钥（可选） | 可选 |
| `ZHIPUAI_API_KEY` | 智谱 AI API Key | 必填 |

**获取飞书 Webhook URL：**
1. 在飞书群中添加自定义机器人
2. 复制 Webhook URL

**获取智谱 AI API Key：**
1. 访问 https://open.bigmodel.cn/
2. 注册并获取 API Key

### 3. 启用 GitHub Actions

1. 打开仓库的 **Actions** 标签页
2. 如果是第一次使用，点击 **I understand my workflows, go ahead and enable them**
3. 选择 **AI Daily News Collector** 工作流
4. 点击 **Run workflow** 手动测试

### 4. 查看运行日志

1. 在 **Actions** 标签页
2. 点击最新的运行记录
3. 展开步骤查看详细日志

## 工作流说明

### 定时任务

每天 **北京时间早上 9:00** 自动运行（UTC 1:00）

### 手动触发

在 Actions 页面点击 **Run workflow** 可以立即运行

## 配置文件

工作流配置位于 `.github/workflows/daily.yml`：

```yaml
schedule:
  - cron: '0 1 * * *'  # UTC 1:00 = 北京 9:00
```

如需修改运行时间，调整 cron 表达式：
- `0 1 * * *` = 每天 1:00 UTC = 北京 9:00
- `0 2 * * *` = 每天 2:00 UTC = 北京 10:00
- `*/30 * * * *` = 每30分钟运行一次

## 与本地运行的区别

| 特性 | 本地运行 | GitHub Actions |
|------|----------|----------------|
| 需要代理 | ✅ 需要 | ❌ 不需要 |
| 依赖本地电脑 | ✅ 是 | ❌ 否 |
| 24/7 运行 | ❌ 否 | ✅ 是 |
| 查看日志 | 本地文件 | GitHub 网页 |
| 成本 | 免费 | 免费（公开仓库） |

## 注意事项

1. **不要在仓库中提交敏感信息**：使用 `.gitignore` 忽略 `.env` 文件
2. **飞书 Webhook 限制**：飞书机器人每分钟最多发送 20 条消息
3. **运行时间限制**：GitHub Actions 每次任务最多运行 6 小时（本任务只需几分钟）

## 故障排查

### 任务失败

1. 查看 Actions 日志中的错误信息
2. 常见问题：
   - Secrets 未配置或配置错误
   - 依赖安装失败
   - 飞书 Webhook URL 无效

### 定时任务未运行

1. 检查 cron 表达式是否正确
2. GitHub Actions 有轻微延迟（通常几分钟内）
3. 确保工作流文件在默认分支（main/master）

### 联系方式

如有问题，请提 Issue 到仓库。
