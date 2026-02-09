# 信息源配置快速参考

## 配置模板速查

### RSS 类型

```json
{
  "metadata": {
    "id": "唯一标识符",
    "name": "显示名称",
    "icon": "📰"
  },
  "categorization": {
    "category": "academic|lab_blog|media|tools|community|newsletter",
    "type": "rss",
    "priority": 1-10
  },
  "collector": {
    "type": "rss",
    "rss_url": "RSS地址"
  }
}
```

### API 类型

```json
{
  "collector": {
    "type": "api",
    "base_url": "API基础URL",
    "endpoint": "/v1/端点",
    "method": "GET|POST",
    "response_format": "json",
    "data_path": "data.items"
  },
  "authentication": {
    "type": "api_key|bearer",
    "api_key": "${ENV_VAR}"
  }
}
```

### 爬虫类型

```json
{
  "collector": {
    "type": "scraper",
    "url": "抓取URL",
    "selectors": {
      "container": "CSS选择器",
      "title": ".title",
      "url": "a.link"
    }
  }
}
```

## 6大分类

| 分类 | 图标 | 说明 |
|------|------|------|
| `academic` | 🎓 | 学术研究、论文 |
| `lab_blog` | 🏢 | 实验室官方博客 |
| `media` | 📰 | 专业媒体 |
| `tools` | 🛠️ | 工具产品 |
| `community` | 💬 | 社区讨论 |
| `newsletter` | 📧 | Newsletter |

## 优先级

| 优先级 | 用途 |
|--------|------|
| 1-2 | 核心源 |
| 3-5 | 重要源 |
| 6-8 | 常规源 |
| 9-10 | 实验源 |

## 认证类型

| 类型 | 说明 |
|------|------|
| `none` | 无需认证 |
| `api_key` | API密钥 |
| `bearer` | Bearer Token |
| `oauth2` | OAuth2 |
| `basic` | 基本认证 |

## 常用配置字段

| 字段 | 说明 |
|------|------|
| `enabled` | 是否启用 |
| `stable` | 是否稳定 |
| `requests_per_minute` | 请求频率 |
| `max_age_hours` | 最大内容时间 |
| `include_keywords` | 包含关键词 |
| `exclude_keywords` | 排除关键词 |

## 环境变量

```json
{
  "api_key": "${API_KEY}",
  "bearer_token": "${BEARER_TOKEN}"
}
```
