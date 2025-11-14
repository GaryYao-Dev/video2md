# Docker 部署指南

本指南介绍如何使用 Docker 部署 Video2MD 项目。

## 📋 前置要求

- Docker Engine 20.10+
- Docker Compose 1.29+ (可选，用于 docker-compose 方式)
- 至少 4GB 可用磁盘空间
- 已配置的 `.env` 文件（包含必要的 API 密钥）

## 🚀 快速开始

### 方法 1: 使用 Docker Compose (推荐)

这是最简单的部署方式：

```bash
# 1. 确保 .env 文件存在并已配置
cp .env.example .env
# 编辑 .env 文件，添加您的 API 密钥

# 2. 启动容器
docker-compose up -d

# 3. 查看日志
docker-compose logs -f

# 4. 访问应用
# 打开浏览器访问 http://localhost:7860
```

**停止和清理：**

```bash
# 停止容器
docker-compose down

# 停止并删除所有数据（慎用！）
docker-compose down -v
```

### 方法 2: 使用 Docker 命令

如果您不使用 Docker Compose：

```bash
# 1. 构建镜像
docker build -t video2md .

# 2. 运行容器
docker run -d \
  --name video2md \
  -p 7860:7860 \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/.env:/app/.env:ro \
  -e TZ=Australia/Sydney \
  --restart unless-stopped \
  video2md

# 3. 查看日志
docker logs -f video2md

# 4. 停止容器
docker stop video2md
docker rm video2md
```

## 📁 数据持久化

容器使用以下卷挂载来持久化数据：

| 容器路径      | 主机路径   | 用途                             |
| ------------- | ---------- | -------------------------------- |
| `/app/input`  | `./input`  | 存放待处理的视频文件             |
| `/app/output` | `./output` | 存放处理后的 Markdown 和字幕文件 |
| `/app/models` | `./models` | 缓存 Whisper 模型文件            |
| `/app/.env`   | `./.env`   | API 密钥配置文件（只读）         |

**重要提示：** 确保在首次运行前创建这些目录：

```bash
mkdir -p input output models
```

## ⚙️ 环境配置

### 必需的环境变量

在 `.env` 文件中配置以下变量：

```bash
# OpenAI API 密钥（必需）
OPENAI_API_KEY=sk-proj-your-key-here

# Serper API 密钥（必需，用于网络搜索）
SERPER_API_KEY=your-serper-key-here
```

### 可选的环境变量

在 `docker-compose.yml` 或 Docker 命令中可配置：

```yaml
environment:
  - TZ=Australia/Sydney # 时区设置
  - GRADIO_SERVER_NAME=0.0.0.0 # Gradio 服务器地址
  - GRADIO_SERVER_PORT=7860 # Gradio 端口
  - RESEARCH_TOOL_SESSION_TIMEOUT_SECONDS=10 # 研究超时时间
```

## 🔧 自定义配置

### 修改端口

**Docker Compose 方式：**

编辑 `docker-compose.yml` 文件：

```yaml
ports:
  - '8080:7860' # 将主机端口改为 8080
```

**Docker 命令方式：**

```bash
docker run -p 8080:7860 ...  # 使用 8080 端口
```

### 修改时区

**Docker Compose 方式：**

编辑 `docker-compose.yml`：

```yaml
environment:
  - TZ=America/New_York # 更改为您的时区
```

**Docker 命令方式：**

```bash
docker run -e TZ=Australia/Sydney ...
```

## 🐛 故障排查

### 容器无法启动

```bash
# 查看容器日志
docker logs video2md

# 检查容器状态
docker ps -a | grep video2md

# 检查 .env 文件是否存在
ls -la .env
```

### API 密钥错误

确保 `.env` 文件格式正确：

```bash
# 查看 .env 内容（隐藏敏感信息）
cat .env | sed 's/=.*/=***/'
```

### 端口冲突

如果 7860 端口已被占用：

```bash
# 检查端口占用
lsof -i :7860

# 使用其他端口（如 8080）
docker run -p 8080:7860 ...
```

### 访问权限问题

确保挂载的目录有正确的权限：

```bash
# 给予读写权限
chmod -R 755 input output models
```

### 内存不足

如果处理大文件时内存不足，可以限制容器内存：

```bash
docker run --memory=4g --memory-swap=4g ...
```

## 🔄 更新应用

### 使用 Docker Compose

```bash
# 1. 停止当前容器
docker-compose down

# 2. 拉取最新代码
git pull

# 3. 重新构建并启动
docker-compose up -d --build
```

### 使用 Docker 命令

```bash
# 1. 停止并删除旧容器
docker stop video2md
docker rm video2md

# 2. 删除旧镜像
docker rmi video2md

# 3. 重新构建
docker build -t video2md .

# 4. 启动新容器
docker run -d ...
```

## 📊 监控和维护

### 查看容器状态

```bash
# 查看运行状态
docker ps | grep video2md

# 查看资源使用
docker stats video2md

# 查看容器详情
docker inspect video2md
```

### 清理旧数据

```bash
# 清理未使用的 Docker 资源
docker system prune

# 清理未使用的镜像
docker image prune

# 清理旧的输出文件（小心！）
rm -rf output/*
```

## 🚢 生产环境部署建议

### 1. 使用反向代理

使用 Nginx 或 Traefik 作为反向代理：

**Nginx 配置示例：**

```nginx
server {
    listen 80;
    server_name video2md.example.com;

    location / {
        proxy_pass http://localhost:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. 启用 HTTPS

使用 Let's Encrypt 配置 SSL：

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d video2md.example.com
```

### 3. 配置自动备份

创建定时任务备份重要数据：

```bash
# 添加到 crontab
0 2 * * * tar -czf /backup/video2md-$(date +\%Y\%m\%d).tar.gz /path/to/video2md/output
```

### 4. 监控和日志

使用日志管理工具：

```bash
# 使用 journalctl 查看日志（如果使用 systemd）
journalctl -u docker -f | grep video2md

# 或配置 Docker 日志驱动
docker run --log-driver=syslog ...
```

## 🔐 安全建议

1. **不要将 `.env` 文件提交到版本控制**
2. **定期更新 Docker 镜像和基础镜像**
3. **使用最小权限原则配置文件权限**
4. **在生产环境中使用 HTTPS**
5. **定期备份重要数据**

## 📝 CI/CD 集成

本项目包含 Jenkins 配置文件 `ci/Jenkinsfile`，支持自动化构建和部署。

参考 Jenkins 配置：

```groovy
// 见 ci/Jenkinsfile 文件
```

## ❓ 常见问题

**Q: 为什么容器启动后无法访问？**

A: 检查防火墙设置，确保 7860 端口已开放。

**Q: 如何在容器内使用 GPU？**

A: 需要安装 NVIDIA Container Toolkit，并在运行时添加 `--gpus all` 参数。详见 GPU 支持文档。

**Q: 容器重启后数据丢失了？**

A: 确保正确配置了卷挂载，数据应存储在挂载的目录中。

**Q: 如何查看详细的处理日志？**

A: 使用 `docker logs -f video2md` 实时查看日志输出。

## 📚 相关文档

- [README.md](README.md) - 项目总览
- [SETUP.md](SETUP.md) - 本地开发设置
- [docs/GPU_SUPPORT.md](docs/GPU_SUPPORT.md) - GPU 加速配置
- [docs/ENVIRONMENT_CONFIG.md](docs/ENVIRONMENT_CONFIG.md) - 环境变量详解

## 💬 获取帮助

如遇到问题，请：

1. 查看容器日志
2. 检查 [GitHub Issues](https://github.com/your-username/video2md/issues)
3. 提交新的 Issue 并附上详细的错误信息
