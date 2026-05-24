# DuckBot — QQ 机器人规划

## 架构概览

```
┌─────────────┐    OneBot v11    ┌──────────────┐    消息事件    ┌──────────────┐
│ go-cqhttp    │ ◄─────────────► │ NoneBot2      │ ──────────► │ music_conv  │
│ (协议实现)   │    WebSocket     │ (机器人框架)   │             │ (转换插件)  │
└─────────────┘                  └──────────────┘             └──────────────┘
```

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 协议层 | go-cqhttp / Lagrange.OneBot | 模拟 QQ 客户端，提供 OneBot v11 API |
| 框架层 | NoneBot2 (Python) | 异步事件驱动，插件化架构 |
| 转换逻辑 | 自实现 (httpx) | iTunes Search API 获取元数据 → 搜索网易云 |
| 运行环境 | Docker Compose | 树莓派 (ARM64) / x86_64 |

## 功能模块

### 1. 音乐链接转换 (plugins/music_converter)
- **触发方式**: 群聊/私聊中检测到 `music.apple.com` 链接
- **流程**: Apple Music URL → 提取曲目元数据 → 搜索网易云音乐 → 返回网易云链接
- **应对策略**: 若搜索不到精确匹配，返回最相似结果 + 置信度提示

### 2. 可扩展架构
- NoneBot2 插件热加载
- 新增插件只需在 `src/duckbot/plugins/` 下创建目录

## 目录结构

```
duckbot/
├── docker-compose.yml       # 容器编排
├── Dockerfile               # 构建镜像
├── PLAN.md                  # 本规划文档
├── README.md                # 使用说明
├── pyproject.toml           # 项目元数据 + 依赖
├── .env.example             # 环境变量模板
├── go-cqhttp/
│   └── config.yml           # go-cqhttp 配置（用户创建）
├── src/duckbot/
│   ├── bot.py               # 启动入口
│   ├── config.py            # 配置读取
│   └── plugins/
│       └── music_converter/
│           ├── __init__.py  # 插件定义 + 事件响应
│           ├── apple.py     # Apple Music 元数据提取
│           └── netease.py   # 网易云音乐搜索
└── docs/
    └── deploy.md            # 部署指南
```

## 风险与应对

- **QQ 账号风控**: go-cqhttp 存在封号风险，建议使用小号
- **Apple Music 反爬**: 使用 User-Agent 轮换 + 请求限流
- **网易云 API 不稳定**: 增加重试与降级策略
