---
name: tugou-monitor
description: Read public Web2 trending news and hot-search feeds from 土狗气象台. Supports status checks, latest messages, group filtering, hot-search inspection, and “recent top 10 priority items” workflows for OpenClaw agents.
user-invocable: true
metadata:
  openclaw:
    requires:
      bins:
        - curl
    emoji: "\U0001F43E"
    install:
      - id: curl
        kind: brew
        formula: curl
        label: curl (HTTP client)
    os:
      - darwin
      - linux
      - win32
  version: 1.3.0
---

# 土狗气象台 Open Skill

读取土狗气象台公开热点 API，供 OpenClaw 进行新闻监控、热搜巡检、摘要、告警和日报整理。

## 快速开始

```bash
curl -s "https://tugoumeme.fun/api/status"
```

当前公开入口固定为：`https://tugoumeme.fun`

## API 约定

- 分组统计：`GET https://tugoumeme.fun/api/channels/groups`
- 消息列表：`GET https://tugoumeme.fun/api/messages`
- 系统状态：`GET https://tugoumeme.fun/api/status`
- 全部热搜：`GET https://tugoumeme.fun/api/hot-search/`
- 单平台热搜：`GET https://tugoumeme.fun/api/hot-search/{source}`，其中 `source` 为 `weibo` 或 `douyin`

## 常用操作

### 1) 查看系统状态

```bash
curl -s "https://tugoumeme.fun/api/status"
```

### 2) 获取全部最新 20 条消息

```bash
curl -s "https://tugoumeme.fun/api/messages?page=1&page_size=20"
```

### 3) 按分组过滤（示例：微博监控）

```bash
curl -s --get "https://tugoumeme.fun/api/messages" \
  --data-urlencode "group_name=微博监控" \
  --data-urlencode "page=1" \
  --data-urlencode "page_size=20"
```

### 4) 最近重点 10 条

```bash
curl -s --get "https://tugoumeme.fun/api/messages" \
  --data-urlencode "is_meme=true" \
  --data-urlencode "page=1" \
  --data-urlencode "page_size=10"
```

### 5) 只看 AI 识别重点（更多结果）

```bash
curl -s --get "https://tugoumeme.fun/api/messages" \
  --data-urlencode "is_meme=true" \
  --data-urlencode "page=1" \
  --data-urlencode "page_size=20"
```

### 6) 获取分组未读统计

```bash
curl -s "https://tugoumeme.fun/api/channels/groups"
```

### 7) 获取全平台热搜

```bash
curl -s "https://tugoumeme.fun/api/hot-search/"
```

### 8) 获取微博热搜

```bash
curl -s "https://tugoumeme.fun/api/hot-search/weibo"
```

### 9) 获取抖音热搜

```bash
curl -s "https://tugoumeme.fun/api/hot-search/douyin"
```

## 返回字段（核心）

消息对象常见字段：
- `id`
- `channel_name`
- `group_name`
- `content`
- `media_url`
- `link_url`
- `is_meme`
- `ai_summary`
- `ai_tags`
- `ai_confidence`
- `is_new`
- `created_at`

热搜对象常见字段：
- `id`
- `title`
- `url`
- `rank`
- `tag`

## 推荐工作流

### 工作流 A：每次抓取后输出“今日最值得发群的 5 条”
1. 拉取 `page=1&page_size=50`
2. 优先选 `is_meme=true` 或 `ai_confidence>=70`
3. 同类话题去重后输出 5 条

### 工作流 B：按分组巡检
1. 获取 `/api/channels/groups`
2. 对每个 `group_name` 拉取前 20 条
3. 生成“微博/抖音/公众号/币安广场”分组简报

### 工作流 C：热搜板块巡检
1. 获取 `/api/hot-search/`
2. 分别检查 `weibo` 与 `douyin` 的 `items`
3. 按 `rank`、`tag` 和标题关键词输出“当前最值得关注的热搜变化”

### 工作流 D：最近重点 10 条快报
1. 拉取 `/api/messages?is_meme=true&page=1&page_size=10`
2. 按 `created_at` 倒序读取最近重点
3. 提炼为“可发群标题 + 一句话摘要 + 原文链接”

## 推荐提示词

### 1) 最近重点 10 条简报

让土狗气象台 Skill 拉取最近重点 10 条，按时间倒序输出。每条包含：
- 标题
- 一句话摘要
- 来源分组
- 原文链接

### 2) 微博与抖音热搜巡检

调用土狗气象台 Skill 同时检查微博热搜和抖音热搜。输出：
- 各平台前 10 热搜
- 共同主题
- 最值得进群讨论的 5 个话题

### 3) 今日可发群选题

使用土狗气象台 Skill 拉取最近 50 条消息，优先筛选 `is_meme=true` 或 `ai_confidence>=70` 的内容。去重后输出 5 条最适合发群的话题，每条包含：
- 建议标题
- 推荐理由
- 风险提示
- 原文链接

### 4) 按分组生成日报

使用土狗气象台 Skill 获取各分组最新消息，为 `微博监控`、`抖音视频监控`、`公众号监控`、`币安广场监控` 分别生成一段简报，并补一段“全局趋势总结”。

## 故障排查

- 如果返回空或 5xx，先检查：
  - `https://tugoumeme.fun` 是否在线
  - 后端服务是否在线
  - Nginx 是否正确转发 `/api/*`
- 如果字段中文乱码，检查后端与数据库编码为 UTF-8，并确保响应头含 `charset=utf-8`。
