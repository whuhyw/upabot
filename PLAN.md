# DuckBot — QQ 机器人规划

## 架构概览

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| 协议层 | [NapCatQQ](https://github.com/NapNeko/NapCatQQ) (Docker) | QQ 协议实现，WebUI 扫码登录，ARM64 原生支持 |
| 框架层 | NoneBot2 + OneBot V11 适配器 | 异步事件驱动，插件化架构，反向 WebSocket |
| 转换逻辑 | 自实现 (httpx) | iTunes Search API 获取元数据 → 搜索网易云 |
| 运行环境 | Docker Compose | 树莓派 (ARM64) / 开发机 (x86_64) |

## 功能模块

### 1. 音乐链接转换 (plugins/music_converter)
- **触发方式**: 群聊/私聊中检测到 `music.apple.com` 链接
- **流程**: Apple Music URL → 提取曲目元数据 → 搜索网易云音乐 → 返回网易云链接
- **应对策略**: 若搜索不到精确匹配，返回最相似结果 + 置信度提示

### 2. 可扩展架构
- NoneBot2 插件化架构，新插件在 `src/duckbot/plugins/` 下创建目录
- 注册方式（二选一）：
  - 在 `bot.py` 中添加 `nonebot.load_plugin("duckbot.plugins.xxx")`
  - 或在 `pyproject.toml` 的 `[tool.nonebot] plugins` 中添加

## 目录结构

```
duckbot/
├── docker-compose.yml       # 容器编排（含日志轮转）
├── Dockerfile               # 构建镜像（双层缓存: 依赖→源码）
├── PLAN.md                  # 本规划文档
├── README.md                # 使用说明
├── pyproject.toml           # 项目元数据 + Python 依赖
├── .env                     # 环境变量（不提交）
├── .env.example             # 环境变量模板
├── .dockerignore            # Docker 构建上下文过滤
├── scripts/
│   └── build.sh             # PC 端交叉编译 → 部署到树莓派
├── napcat/
│   └── config/
│       └── onebot11.json    # NapCat 反向 WS 配置（预置）
├── ntqq/                    # QQ 登录态 + 聊天数据（Docker 挂载卷）
├── src/duckbot/
│   ├── bot.py               # 启动入口
│   └── plugins/
│       └── music_converter/
│           ├── __init__.py  # 插件定义 + Apple Music 链接匹配
│           ├── apple.py     # iTunes Search API 元数据提取
│           └── netease.py   # 网易云音乐搜索 API
└── docs/
    └── deploy.md            # 部署指南（NapCat 扫码流程）
```

## 添加依赖 / 新插件

每次添加 Python 包或新插件时，需同步修改以下文件：

### 添加 Python 包
| 文件 | 修改内容 |
|------|---------|
| `pyproject.toml` | 在 `[project] dependencies` 中添加包名 + 版本约束 |
| `Dockerfile` | 无需修改（自动读取 `pyproject.toml` 安装依赖） |

> 注意：Dockerfile 的分层缓存依赖 `pyproject.toml`，新增依赖后首次构建会较慢（重新下载所有包），后续不改依赖则秒级完成。

### 添加新插件
| 文件 | 修改内容 |
|------|---------|
| `src/duckbot/plugins/xxx/__init__.py` | 创建插件文件，定义事件响应器 |
| `pyproject.toml` | 在 `[tool.nonebot] plugins` 中添加模块路径 |
| `bot.py` | 或在此文件中添加 `nonebot.load_plugin("...")` |

## 持久化与存储风险

| 风险点 | 位置 | 应对措施 |
|--------|------|---------|
| Docker 日志 | 每个容器的 `json-file` 驱动 | ✅ 已配置 `max-size: 10m`, `max-file: 3` |
| QQ 聊天记录 DB | `ntqq/.../nt_db/nt_msg.db` | 随使用增长，月级尺度可控 |
| QQ 媒体缓存 | `ntqq/.../nt_data/` (头像/图片/文件) | 定期清理：`rm -rf ntqq/*/nt_temp/* ntqq/*/nt_data/avatar/*` |
| 容器崩溃 | 进程异常退出 | ✅ `restart: unless-stopped` 自动恢复 |

## 风险与应对

- **QQ 账号风控**: NapCatQQ 使用官方 QQ 协议，风险低于第三方协议实现，但仍建议使用小号
- **Apple Music 反爬**: 使用 User-Agent 轮换 + 请求限流
- **网易云 API 不稳定**: 增加重试与降级策略
