# DuckBot

基于 NoneBot2 的 QQ 机器人，自动将 Apple Music 链接转换为网易云音乐链接。

## 快速开始

```bash
cp .env.example .env          # 编辑配置
docker compose up -d           # 启动
# 浏览器访问 http://<ip>:6099/webui/ 扫码登录 QQ
```

详见 [部署指南](docs/deploy.md)。

## 项目结构

```
docker-compose.yml
Dockerfile
.env                     # 环境变量
napcat/config/           # NapCat 配置
src/duckbot/
  ├── bot.py             # 启动入口
  └── plugins/
      └── music_converter/
          ├── apple.py   # Apple Music 元数据提取
          └── netease.py # 网易云音乐搜索
```
