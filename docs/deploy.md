# DuckBot Docker Compose 部署

## 前置要求

- Docker + Docker Compose（Linux x86_64 或 ARM）
- 一个可用的 QQ 账号

## 1. 配置机器人

```bash
cp .env.example .env
# 编辑 .env，修改 SUPERUSERS=["你的QQ"]
```

## 2. 启动

```bash
docker compose up -d
```

## 3. 登录 QQ

打开浏览器访问 `http://<树莓派IP>:6099/webui/`：

1. 进入 **QQ 登录** 页面
2. 点击 **QRCode**，用手机 QQ 扫描二维码
3. 登录成功后自动进入 WebUI

> 首次登录会要求修改 WebUI 密码，请自行设置。

## 4. 验证连接

```bash
docker compose logs duckbot
# 看到 "Bot xxx connected" 即表示 NapCat 已连入
```

## 验证转换功能

在 QQ 中发送一条 Apple Music 链接，机器人应自动回复对应的网易云音乐链接。

## 目录说明

```
napcat/config/           # NapCat 配置（持久化，含登录态）
ntqq/                    # QQ 数据目录（持久化）
```
