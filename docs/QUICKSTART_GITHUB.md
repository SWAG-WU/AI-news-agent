# GitHub Actions 快速部署指南

## 三步完成部署

### 第 1 步：推送代码到 GitHub

```bash
git add .
git commit -m "feat: add GitHub Actions workflow for daily collection"
git push
```

### 第 2 步：配置 Secrets

打开你的 GitHub 仓库：

1. **Settings** → **Secrets and variables** → **Actions**
2. 点击 **New repository secret**，添加：

| 名称 | 值 |
|------|-----|
| `FEISHU_WEBHOOK_URL` | `https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx` |
| `ZHIPUAI_API_KEY` | 你的智谱AI API Key |

> 你的飞书 Webhook URL 在 `.env` 文件中

### 第 3 步：手动测试

1. 打开仓库的 **Actions** 标签页
2. 选择 **AI Daily News Collector**
3. 点击 **Run workflow** → **Run workflow**
4. 等待几分钟，查看运行结果

---

## 配置完成！

现在系统会：
- ✅ 每天 **北京时间早上 9:00** 自动采集
- ✅ 发送到你的飞书群
- ✅ 无需本地电脑开机
- ✅ 无需代理

## 常用命令

```bash
# 查看工作流状态
gh run list

# 手动触发工作流
gh workflow run daily.yml

# 查看最新运行日志
gh run view --log
```

## 修改运行时间

编辑 `.github/workflows/daily.yml`：

```yaml
schedule:
  - cron: '0 1 * * *'  # 北京 9:00
```

改为其他时间：
- `0 2 * * *` = 北京 10:00
- `30 1 * * *` = 北京 9:30
- `0 */6 * * *` = 每6小时一次
