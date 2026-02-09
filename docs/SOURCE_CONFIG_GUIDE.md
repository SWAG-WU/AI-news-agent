# 信息源配置指南

本文档说明如何使用统一的信息源配置格式来添加和管理AI资讯信息源。

## 目录

- [配置格式概览](#配置格式概览)
- [配置结构](#配置结构)
- [采集器类型](#采集器类型)
- [完整示例](#完整示例)
- [最佳实践](#最佳实践)

---

## 配置格式概览

统一配置格式支持以下特性：

- ✅ **多采集方式**：RSS、API、爬虫、Newsletter
- ✅ **灵活认证**：API Key、Bearer Token、OAuth2
- ✅ **智能过滤**：关键词、评分、时间范围
- ✅ **限流控制**：请求频率、突发大小
- ✅ **缓存配置**：内存、Redis、文件缓存
- ✅ **监控告警**：日志级别、错误告警
- ✅ **JSON Schema**：可验证的配置格式

---

## 配置结构

每个信息源配置包含以下主要部分：

### 1. metadata（元数据）

```json
{
  "metadata": {
    "id": "openai_blog",           // 唯一标识符（必需）
    "name": "OpenAI Blog",          // 显示名称（必需）
    "description": "OpenAI官方博客", // 描述
    "homepage": "https://openai.com", // 官网
    "icon": "🏢",                    // 图标
    "tags": ["official", "ai"],     // 标签
    "version": "1.0.0"              // 配置版本
  }
}
```

### 2. categorization（分类信息）

```json
{
  "categorization": {
    "category": "lab_blog",         // 6大分类之一（必需）
    "type": "rss",                   // 采集方式（必需）
    "priority": 1,                   // 优先级 1-10
    "language": "en"                 // 内容语言
  }
}
```

**6大分类**：
- `academic` - 🎓 学术研究
- `lab_blog` - 🏢 实验室博客
- `media` - 📰 专业媒体
- `tools` - 🛠️ 工具产品
- `community` - 💬 社区讨论
- `newsletter` - 📧 Newsletter

### 3. collector（采集器配置）

根据 `type` 不同，采集器配置也不同。见下文详细说明。

### 4. authentication（认证配置）

```json
{
  "authentication": {
    "type": "api_key",              // none | api_key | bearer | oauth2 | basic
    "api_key": "${API_KEY}",        // 支持环境变量
    "api_key_header": "X-API-Key"   // 自定义请求头
  }
}
```

### 5. rate_limit（限流配置）

```json
{
  "rate_limit": {
    "requests_per_minute": 10,      // 每分钟请求数
    "requests_per_hour": 500,       // 每小时请求数
    "burst_size": 5,                // 突发大小
    "retry_after": 60               // 重试等待时间（秒）
  }
}
```

### 6. filters（过滤规则）

```json
{
  "filters": {
    "include_keywords": ["AI", "ML"],    // 包含关键词
    "exclude_keywords": ["广告", "推广"], // 排除关键词
    "min_score": 0.6,                     // 最低评分
    "time_range": {
      "max_age_hours": 168               // 最大时间范围
    }
  }
}
```

### 7. status（状态管理）

```json
{
  "status": {
    "enabled": true,                 // 是否启用
    "stable": true,                  // 是否稳定
    "notes": "运行正常"              // 备注
  }
}
```

---

## 采集器类型

### RSS 采集器

最常用的采集方式，适用于有RSS feed的网站。

```json
{
  "collector": {
    "type": "rss",
    "rss_url": "https://example.com/rss.xml",
    "base_url": "https://example.com",
    "update_frequency": "daily",     // realtime | hourly | daily | weekly
    "item_limit": 50                 // 单次采集最大条数
  }
}
```

### API 采集器

适用于提供API接口的服务。

```json
{
  "collector": {
    "type": "api",
    "base_url": "https://api.example.com",
    "endpoint": "/v1/items",
    "method": "GET",                  // GET | POST
    "headers": {
      "Accept": "application/json"
    },
    "params": {
      "limit": 50,
      "sort": "newest"
    },
    "response_format": "json",       // json | xml | html | text
    "data_path": "data.items",       // JSON数据路径
    "pagination": {
      "type": "offset",              // offset | cursor | page
      "limit": 50,
      "max_pages": 5
    }
  }
}
```

### 爬虫采集器

适用于需要网页抓取的场景。

```json
{
  "collector": {
    "type": "scraper",
    "url": "https://example.com/latest",
    "base_url": "https://example.com",
    "selectors": {
      "container": ".article-item",   // 条目容器
      "title": ".title",              // 标题选择器
      "url": "a.permalink",           // 链接选择器
      "description": ".excerpt",      // 描述选择器
      "author": ".author-name",       // 作者选择器
      "published_at": "time[datetime]", // 时间选择器
      "score": ".points"              // 评分选择器
    },
    "render_js": false,               // 是否需要渲染JS
    "wait_for_selector": ".article-item" // 等待选择器
  }
}
```

### Newsletter 采集器

适用于Newsletter内容提取。

```json
{
  "collector": {
    "type": "newsletter",
    "url": "https://example.com/newsletter/archive",
    "archive_url": "https://example.com/newsletter/archive",
    "extractor": "html",             // rss | html | custom
    "rss_url": "https://example.com/rss.xml" // 如果有RSS
  }
}
```

---

## 完整示例

### 示例1：OpenAI Blog（RSS）

```json
{
  "metadata": {
    "id": "openai_blog",
    "name": "OpenAI Blog",
    "description": "OpenAI官方博客，发布GPT、Agent、安全研究等最新进展",
    "homepage": "https://openai.com/blog",
    "icon": "🏢",
    "tags": ["official", "high-priority"]
  },
  "categorization": {
    "category": "lab_blog",
    "type": "rss",
    "priority": 1,
    "language": "en"
  },
  "collector": {
    "type": "rss",
    "rss_url": "https://openai.com/blog/rss.xml",
    "base_url": "https://openai.com",
    "update_frequency": "daily",
    "item_limit": 20
  },
  "authentication": {
    "type": "none"
  },
  "rate_limit": {
    "requests_per_minute": 10
  },
  "filters": {
    "time_range": {
      "max_age_hours": 168
    }
  },
  "cache": {
    "enabled": true,
    "ttl_minutes": 60
  },
  "status": {
    "enabled": true,
    "stable": true
  },
  "monitoring": {
    "log_level": "INFO"
  }
}
```

### 示例2：Hacker News（API）

```json
{
  "metadata": {
    "id": "hacker_news",
    "name": "Hacker News",
    "description": "Hacker News首页，获取AI相关热门讨论",
    "homepage": "https://news.ycombinator.com",
    "icon": "💬",
    "tags": ["community", "discussion"]
  },
  "categorization": {
    "category": "community",
    "type": "api",
    "priority": 2,
    "language": "en"
  },
  "collector": {
    "type": "api",
    "base_url": "https://hacker-news.firebaseio.com/v0",
    "endpoint": "/newstories",
    "method": "GET",
    "response_format": "json",
    "data_path": null,
    "params": {
      "limit": 30
    }
  },
  "authentication": {
    "type": "none"
  },
  "filters": {
    "include_keywords": ["AI", "machine learning", "LLM", "GPT"],
    "min_score": 50
  },
  "status": {
    "enabled": true,
    "stable": true
  }
}
```

### 示例3：Product Hunt（爬虫）

```json
{
  "metadata": {
    "id": "product_hunt_ai",
    "name": "Product Hunt - AI",
    "description": "Product Hunt上的AI新产品",
    "homepage": "https://www.producthunt.com",
    "icon": "🛠️",
    "tags": ["tools", "products"]
  },
  "categorization": {
    "category": "tools",
    "type": "scraper",
    "priority": 3,
    "language": "en"
  },
  "collector": {
    "type": "scraper",
    "url": "https://www.producthunt.com/topics/artificial-intelligence",
    "base_url": "https://www.producthunt.com",
    "selectors": {
      "container": "li[data-test=post-item]",
      "title": "[data-test=post-name]",
      "url": "a[data-test=post-url]",
      "description": "[data-test=post-description]",
      "score": "[data-test=vote-button]"
    },
    "render_js": true,
    "wait_for_selector": "li[data-test=post-item]"
  },
  "rate_limit": {
    "requests_per_minute": 5
  },
  "filters": {
    "time_range": {
      "max_age_hours": 24
    }
  },
  "status": {
    "enabled": false,
    "notes": "需要渲染JavaScript，依赖页面结构"
  }
}
```

---

## 最佳实践

### 1. ID命名规范

- 使用小写字母和下划线：`openai_blog`
- 按类型添加前缀：`rss_openai`, `api_hacker_news`
- 保持简洁和描述性

### 2. 优先级设置

| 优先级 | 用途 |
|--------|------|
| 1 | 核心信息源，优先采集 |
| 2-3 | 重要信息源 |
| 4-6 | 常规信息源 |
| 7-8 | 备用信息源 |
| 9-10 | 实验性/不稳定源 |

### 3. 限流配置

- RSS源：10-20 请求/分钟
- API源：遵循API文档限制
- 爬虫源：5-10 请求/分钟
- Newsletter源：1-5 请求/小时

### 4. 过滤规则

- 使用 `include_keywords` 精准定位内容
- 使用 `exclude_keywords` 过滤垃圾内容
- 设置合理的 `max_age_hours` 避免过期内容
- 设置 `min_score` 提升内容质量

### 5. 测试新信息源

1. 先设置 `enabled: false`
2. 测试采集是否正常
3. 验证内容质量
4. 确认无误后设置 `enabled: true` 和 `stable: true`

### 6. 环境变量使用

对于敏感信息，使用环境变量：

```json
{
  "authentication": {
    "api_key": "${API_KEY}",           // 从环境变量读取
    "bearer_token": "${BEARER_TOKEN}"
  }
}
```

### 7. 监控配置

对于关键信息源，启用监控：

```json
{
  "monitoring": {
    "log_level": "INFO",
    "alert_on_failure": true,
    "metrics": {
      "collect_count": true,
      "collect_duration": true,
      "error_rate": true
    }
  }
}
```

---

## 配置验证

使用JSON Schema验证配置：

```bash
# 安装ajv CLI
npm install -g ajv-cli

# 验证配置文件
ajv validate -s config/schemas/source.schema.json -d config/sources.json
```

---

## 故障排查

### 问题：RSS解析失败

**可能原因**：
- RSS URL错误
- RSS格式不规范
- 网络问题

**解决方案**：
1. 在浏览器中测试RSS URL是否可访问
2. 使用RSS验证工具检查格式
3. 检查网络连接

### 问题：API返回401/403

**可能原因**：
- 认证配置错误
- API密钥过期
- 请求频率过高

**解决方案**：
1. 验证API密钥是否正确
2. 检查认证类型配置
3. 降低请求频率

### 问题：爬虫无法提取内容

**可能原因**：
- 页面结构变化
- 需要渲染JavaScript
- 触发反爬机制

**解决方案**：
1. 更新CSS选择器
2. 启用 `render_js`
3. 添加请求头模拟浏览器

---

## 更新日志

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2026-02-09 | 初始版本，定义统一配置格式 |
