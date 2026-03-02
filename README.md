# JD_COOKIE 管理系统

本项目是一个基于 Flask 的 JD_COOKIE 管理系统，支持 JD_COOKIE 的查询与更新，适合内部使用。前端页面美观，支持 Docker 部署。

![](figs/1.png)

![](figs/2.png)

## 功能简介

- 查询 JD_COOKIE 状态（按 pt_pin 查询）
- 更新并启用 JD_COOKIE
- 限制同一 IP 每日访问次数
- **邮件提醒系统**：Cookie 过期时自动发送邮件通知
- **管理后台**：查看所有 Cookie 状态、配置邮件系统、管理用户绑定邮箱
- 支持 Docker 一键部署

## 目录结构

```
.
├── app.py                        # Flask 主程序
├── requirements.txt              # Python 依赖
├── Dockerfile                    # Docker 镜像构建文件
├── config.yaml.example           # 配置文件模板（cp 后填写）
├── docker-compose.yaml.example   # Compose 示例配置
├── user_config.yaml.example      # 用户配置模板（cp 后填写）
├── static/
│   ├── jdupdate.html             # 主前端页面
│   ├── admin.html                # 管理后台页面
│   └── admin_login.html          # 管理后台登录页
├── .dockerignore
└── .gitignore
```

## 快速开始

### 1. 复制配置文件

```sh
cp config.yaml.example config.yaml
cp user_config.yaml.example user_config.yaml
```

编辑 `config.yaml`，填入青龙面板信息、管理员账号、邮件配置等。

### 2. 本地运行

#### 方法 A: 使用 pip（传统方式）

```sh
pip install -r requirements.txt
python app.py
```

#### 方法 B: 使用 uv（推荐，速度更快）

```sh
# 安装 uv（如果未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 运行
uv run app.py
```

### 3. Docker Compose 部署（推荐）

```sh
cp docker-compose.yaml.example docker-compose.yaml
# 编辑 docker-compose.yaml，填入配置

docker build -t jdupdate .
docker compose up -d

# 查看日志
docker compose logs -f
```

## 配置说明

所有配置通过 `config.yaml` 管理（参考 `config.yaml.example`）：

### 青龙面板（必填）
- `QL_HOST`：青龙面板地址（如 `http://192.168.1.1:5789`）
- `CLIENT_ID`：青龙开放 API Client ID
- `CLIENT_SECRET`：青龙开放 API Client Secret

### 管理员账号
- `ADMIN_USERNAME`：管理员用户名（默认 `admin`）
- `ADMIN_PASSWORD`：管理员密码（默认 `admin123`，**请修改！**）
- `ADMIN_EMAIL`：管理员邮箱（用于接收测试邮件）

### 可选配置
- `MAX_DAILY_ACCESS`：每个 IP 每日最大访问次数（默认 `7`）
- `BACKGROUND_IMAGE_URL`：页面背景图 URL（默认随机图片 API）

### 邮件系统
- `email.enabled`：是否启用邮件提醒（`true`/`false`）
- `email.smtpServer`：SMTP 服务器地址
- `email.smtpPort`：SMTP 端口（465 使用 SSL，587 使用 STARTTLS）
- `email.smtpUser`：发件邮箱账号
- `email.smtpPass`：邮箱授权码
- `email.checkTime`：每日检查时间（如 `08:00`）

## API 接口

- `GET /` - 主页面
- `GET /admin` - 管理后台
- `GET /api/config` - 获取前端配置
- `GET /api/envs` - 获取青龙环境变量列表
- `GET /api/jdcookie/query?ptpin=<value>` - 查询 JD_COOKIE（有频率限制）
- `POST /api/jdcookie/update` - 更新并启用 JD_COOKIE（有频率限制）
- `POST /api/jdcookie/bind-email` - 绑定邮箱提醒（有频率限制）
- `GET /api/admin/email/config` - 获取邮件配置（需登录）
- `POST /api/admin/email/config` - 保存邮件配置（需登录）
- `POST /api/admin/email/test` - 发送测试邮件（需登录）

## 注意事项

- 本项目仅供内部学习与交流使用，请勿用于非法用途
- IP 访问限制基于内存存储，应用重启后计数会重置
- 生产环境建议修改默认管理员密码，并使用 HTTPS
- `config.yaml` 和 `user_config.yaml` 包含敏感信息，已加入 `.gitignore`

## 问题反馈及功能开发

[![QQ群](https://img.shields.io/badge/QQ群-965312424-green)](https://qm.qq.com/cgi-bin/qm/qr?k=en97YqjfYaLpebd9Nn8gbSvxVrGdIXy2&jump_from=webapi&authKey=41BmkEjbGeJ81jJNdv7Bf5EDlmW8EHZeH7/nktkXYdLGpZ3ISOS7Ur4MKWXC7xIx)

## License

MIT
